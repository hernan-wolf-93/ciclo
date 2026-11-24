from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import exigir_administrador, obtener_db, obtener_operador_actual
from app.core.roles import ROLES_ADMINISTRADORES
from app.models import Operador
from app.schemas.catalogo import (
    EquipoOut,
    MaterialAdminOut,
    MaterialAltaIn,
    MaterialModificarIn,
    MaterialOut,
    ProgramaOut,
    ProximoNumeroOut,
    ServicioAdminOut,
    ServicioAltaIn,
    ServicioModificarIn,
    ServicioOut,
)
from app.services import abm_catalogos, catalogo
from app.services.abm_catalogos import Duplicado, ErrorDeCatalogo, Inexistente
from app.services.numeracion_lote import EquipoInexistente, proponer_numero

# Todo con sesión iniciada, igual que lotes y recepciones. La consulta es para
# cualquier usuario; alta, modificación y baja de servicios y materiales, solo
# para administradores (mismo criterio que operadores.py).
router = APIRouter(tags=["catalogos"], dependencies=[Depends(obtener_operador_actual)])


def _a_http(error: ErrorDeCatalogo) -> HTTPException:
    """Traduce una regla de negocio incumplida al código HTTP que corresponde."""
    if isinstance(error, Duplicado):
        codigo = status.HTTP_409_CONFLICT
    elif isinstance(error, Inexistente):
        codigo = status.HTTP_404_NOT_FOUND
    else:
        codigo = 422
    return HTTPException(status_code=codigo, detail=str(error))


def _exigir_admin_si(incluir_inactivos: bool, operador: Operador) -> None:
    """La lista completa (con inactivos) es solo para el ABM: solo administradores."""
    if incluir_inactivos and operador.rol.nombre not in ROLES_ADMINISTRADORES:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="No tiene permiso para realizar esta acción")


_INCLUIR_INACTIVOS = Query(
    description="Solo administradores: todos los registros, con externo (servicios) y el estado."
)


# La respuesta tiene dos formas según incluir_inactivos: sin el parámetro, ServicioOut /
# MaterialOut (igual que antes del ABM); con él, la forma completa del ABM. La forma
# completa va primero en la unión: si fuera segunda, una lista del ABM también valida
# como la reducida y FastAPI le quitaría externo y activo.
@router.get("/servicios", response_model=list[ServicioAdminOut] | list[ServicioOut])
def servicios(
    db: Annotated[Session, Depends(obtener_db)],
    operador: Annotated[Operador, Depends(obtener_operador_actual)],
    incluir_inactivos: Annotated[bool, _INCLUIR_INACTIVOS] = False,
):
    """Servicios activos, con los días de aireación de óxido de etileno.

    Con ?incluir_inactivos=true (solo administradores), todos, con externo y activo.
    """
    _exigir_admin_si(incluir_inactivos, operador)
    if incluir_inactivos:
        return [ServicioAdminOut.model_validate(s) for s in abm_catalogos.listar_servicios_admin(db)]
    return [ServicioOut(**fila) for fila in catalogo.listar_servicios(db)]


@router.post("/servicios", response_model=ServicioAdminOut, status_code=status.HTTP_201_CREATED)
def crear_servicio(
    datos: ServicioAltaIn,
    _: Annotated[Operador, Depends(exigir_administrador)],
    db: Annotated[Session, Depends(obtener_db)],
):
    """Alta de un servicio. Solo administradores."""
    try:
        return abm_catalogos.crear_servicio(db, datos)
    except ErrorDeCatalogo as error:
        raise _a_http(error) from error


@router.patch("/servicios/{servicio_id}", response_model=ServicioAdminOut)
def modificar_servicio(
    servicio_id: int,
    datos: ServicioModificarIn,
    _: Annotated[Operador, Depends(exigir_administrador)],
    db: Annotated[Session, Depends(obtener_db)],
):
    """Modifica un servicio. La baja es lógica (activo: false) y se revierte con activo: true."""
    try:
        return abm_catalogos.modificar_servicio(db, servicio_id, datos)
    except ErrorDeCatalogo as error:
        raise _a_http(error) from error


@router.get("/materiales", response_model=list[MaterialAdminOut] | list[MaterialOut])
def materiales(
    db: Annotated[Session, Depends(obtener_db)],
    operador: Annotated[Operador, Depends(obtener_operador_actual)],
    incluir_inactivos: Annotated[bool, _INCLUIR_INACTIVOS] = False,
):
    """Materiales activos, con código y nombre alternativo (técnico o de cirugía).

    Con ?incluir_inactivos=true (solo administradores), todos, con activo.
    """
    _exigir_admin_si(incluir_inactivos, operador)
    if incluir_inactivos:
        return [MaterialAdminOut.model_validate(m) for m in abm_catalogos.listar_materiales_admin(db)]
    return [MaterialOut(**fila) for fila in catalogo.listar_materiales(db)]


@router.post("/materiales", response_model=MaterialAdminOut, status_code=status.HTTP_201_CREATED)
def crear_material(
    datos: MaterialAltaIn,
    _: Annotated[Operador, Depends(exigir_administrador)],
    db: Annotated[Session, Depends(obtener_db)],
):
    """Alta de un material. El código se guarda en mayúsculas y sin espacios. Solo administradores."""
    try:
        return abm_catalogos.crear_material(db, datos)
    except ErrorDeCatalogo as error:
        raise _a_http(error) from error


@router.patch("/materiales/{material_id}", response_model=MaterialAdminOut)
def modificar_material(
    material_id: int,
    datos: MaterialModificarIn,
    _: Annotated[Operador, Depends(exigir_administrador)],
    db: Annotated[Session, Depends(obtener_db)],
):
    """Modifica un material. La baja es lógica (activo: false) y se revierte con activo: true."""
    try:
        return abm_catalogos.modificar_material(db, material_id, datos)
    except ErrorDeCatalogo as error:
        raise _a_http(error) from error


@router.get("/equipos", response_model=list[EquipoOut])
def equipos(db: Annotated[Session, Depends(obtener_db)]):
    """Equipos de esterilización activos, con su método."""
    return catalogo.listar_equipos(db)


@router.get("/programas", response_model=list[ProgramaOut])
def programas(
    db: Annotated[Session, Depends(obtener_db)],
    equipo_id: Annotated[
        int | None, Query(gt=0, description="Si se indica, solo los programas del método del equipo.")
    ] = None,
):
    try:
        return catalogo.listar_programas(db, equipo_id)
    except EquipoInexistente as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.get("/equipos/{equipo_id}/proximo-numero", response_model=ProximoNumeroOut)
def proximo_numero(equipo_id: int, db: Annotated[Session, Depends(obtener_db)]):
    """Número que se propone para el próximo lote del equipo. Es una propuesta, no una reserva."""
    try:
        numero = proponer_numero(db, equipo_id)
    except EquipoInexistente as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    return ProximoNumeroOut(equipo_id=equipo_id, numero=numero)
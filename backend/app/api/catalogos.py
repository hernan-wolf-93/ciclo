from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import obtener_db, obtener_operador_actual
from app.schemas.catalogo import (
    EquipoOut,
    MaterialOut,
    ProgramaOut,
    ProximoNumeroOut,
    ServicioOut,
)
from app.services import catalogo
from app.services.numeracion_lote import EquipoInexistente, proponer_numero

# Solo lectura, pero con sesión iniciada, igual que lotes y recepciones.
router = APIRouter(tags=["catalogos"], dependencies=[Depends(obtener_operador_actual)])


@router.get("/servicios", response_model=list[ServicioOut])
def servicios(db: Annotated[Session, Depends(obtener_db)]):
    """Servicios activos, con los días de aireación de óxido de etileno."""
    return catalogo.listar_servicios(db)


@router.get("/materiales", response_model=list[MaterialOut])
def materiales(db: Annotated[Session, Depends(obtener_db)]):
    """Materiales activos, con código y nombre alternativo (técnico o de cirugía)."""
    return catalogo.listar_materiales(db)


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
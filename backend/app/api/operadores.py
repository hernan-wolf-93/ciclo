from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import exigir_administrador, obtener_db
from app.models import Operador
from app.schemas.operador import OperadorAdminOut, OperadorAltaIn, OperadorModificarIn
from app.services.operadores import (
    ErrorDeOperadores,
    NumeroDuplicado,
    OperadorInexistente,
    SinPermiso,
    dar_de_alta_operador,
    listar_operadores,
    modificar_operador,
)

router = APIRouter(prefix="/operadores", tags=["operadores"])


def _salida(operador: Operador) -> OperadorAdminOut:
    return OperadorAdminOut(
        id=operador.id,
        numero_operador=operador.numero_operador,
        rol=operador.rol.nombre,
        activo=operador.activo,
    )


def _a_http(error: ErrorDeOperadores) -> HTTPException:
    """Traduce una regla de negocio incumplida al código HTTP que corresponde."""
    if isinstance(error, SinPermiso):
        codigo = status.HTTP_403_FORBIDDEN
    elif isinstance(error, NumeroDuplicado):
        codigo = status.HTTP_409_CONFLICT
    elif isinstance(error, OperadorInexistente):
        codigo = status.HTTP_404_NOT_FOUND
    else:
        codigo = 422
    return HTTPException(status_code=codigo, detail=str(error))


@router.get("", response_model=list[OperadorAdminOut])
def listar(
    _: Annotated[Operador, Depends(exigir_administrador)],
    db: Annotated[Session, Depends(obtener_db)],
    activo: bool | None = None,
):
    """Lista de operadores. Con ?activo=true o ?activo=false se filtra por estado."""
    return [_salida(operador) for operador in listar_operadores(db, activo)]


@router.post("", response_model=OperadorAdminOut, status_code=status.HTTP_201_CREATED)
def crear(
    datos: OperadorAltaIn,
    actor: Annotated[Operador, Depends(exigir_administrador)],
    db: Annotated[Session, Depends(obtener_db)],
):
    """Alta de un operador. El rol que puede asignar depende del rol de quien lo crea."""
    try:
        nuevo = dar_de_alta_operador(db, actor, datos)
    except ErrorDeOperadores as error:
        raise _a_http(error) from error
    return _salida(nuevo)


@router.patch("/{operador_id}", response_model=OperadorAdminOut)
def modificar(
    operador_id: int,
    datos: OperadorModificarIn,
    actor: Annotated[Operador, Depends(exigir_administrador)],
    db: Annotated[Session, Depends(obtener_db)],
):
    """Cambia el rol o el estado de un operador. La baja es lógica: activo = false."""
    try:
        operador = modificar_operador(db, actor, operador_id, datos)
    except ErrorDeOperadores as error:
        raise _a_http(error) from error
    return _salida(operador)
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import exigir_administrador, obtener_db
from app.models import Operador
from app.schemas.operador import OperadorAdminOut, OperadorAltaIn
from app.services.operadores import (
    ErrorDeOperadores,
    NumeroDuplicado,
    SinPermiso,
    dar_de_alta_operador,
    listar_operadores,
)

router = APIRouter(prefix="/operadores", tags=["operadores"])


def _salida(operador: Operador) -> OperadorAdminOut:
    return OperadorAdminOut(
        id=operador.id,
        numero_operador=operador.numero_operador,
        rol=operador.rol.nombre,
        activo=operador.activo,
    )


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
    except SinPermiso as error:  # las subclases van antes que ErrorDeOperadores
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error)) from error
    except NumeroDuplicado as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except ErrorDeOperadores as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return _salida(nuevo)
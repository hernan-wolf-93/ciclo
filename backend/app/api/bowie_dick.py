from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import obtener_db, obtener_operador_actual
from app.models import Equipo, Operador
from app.schemas.bowie_dick import BowieDickEstadoOut, BowieDickIn, BowieDickOut
from app.services.bowie_dick import (
    ErrorDeBowieDick,
    hay_bowie_dick_aprobado_hoy,
    registrar_bowie_dick,
)
from app.services.numeracion_lote import EquipoInexistente

router = APIRouter(tags=["bowie-dick"])


@router.post(
    "/equipos/{equipo_id}/bowie-dick",
    response_model=BowieDickOut,
    status_code=status.HTTP_201_CREATED,
)
def registrar(
    equipo_id: int,
    datos: BowieDickIn,
    operador: Annotated[Operador, Depends(obtener_operador_actual)],
    db: Annotated[Session, Depends(obtener_db)],
):
    """Registra el control Bowie-Dick del autoclave. El operador sale del token."""
    try:
        return registrar_bowie_dick(db, operador, equipo_id, datos)
    except EquipoInexistente as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except ErrorDeBowieDick as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error


@router.get(
    "/equipos/{equipo_id}/bowie-dick/hoy",
    response_model=BowieDickEstadoOut,
    dependencies=[Depends(obtener_operador_actual)],
)
def estado_de_hoy(equipo_id: int, db: Annotated[Session, Depends(obtener_db)]):
    """Dice si el equipo tiene hoy un Bowie-Dick aprobado (el último de hoy cuenta)."""
    if db.get(Equipo, equipo_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"No existe el equipo {equipo_id}")
    aprobado = hay_bowie_dick_aprobado_hoy(db, equipo_id, datetime.now(timezone.utc))
    return BowieDickEstadoOut(equipo_id=equipo_id, aprobado_hoy=aprobado)
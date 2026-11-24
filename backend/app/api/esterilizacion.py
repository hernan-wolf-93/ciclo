from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import obtener_db, obtener_operador_actual
from app.schemas.avance import PendienteOut
from app.services.esterilizacion import listar_pendientes_equipo
from app.services.numeracion_lote import EquipoInexistente

router = APIRouter(tags=["esterilizacion"], dependencies=[Depends(obtener_operador_actual)])


@router.get("/equipos/{equipo_id}/pendientes", response_model=list[PendienteOut])
def pendientes_del_equipo(equipo_id: int, db: Annotated[Session, Depends(obtener_db)]):
    """Material que puede cargar el equipo (su método), por servicio de origen y material."""
    try:
        return listar_pendientes_equipo(db, equipo_id)
    except EquipoInexistente as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(error)) from error
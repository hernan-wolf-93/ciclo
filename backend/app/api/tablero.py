from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import obtener_db, obtener_operador_actual
from app.schemas.tablero import FilaTableroOut
from app.services.tablero import listar_tablero

# Solo lectura, pero con sesión iniciada, igual que lotes y recepciones.
router = APIRouter(
    prefix="/tablero",
    tags=["tablero"],
    dependencies=[Depends(obtener_operador_actual)],
)


@router.get("", response_model=list[FilaTableroOut])
def tablero(
    db: Annotated[Session, Depends(obtener_db)],
    urgente: Annotated[bool | None, Query(description="true: solo urgentes; false: solo no urgentes.")] = None,
    servicio_id: Annotated[int | None, Query(gt=0, description="Servicio de origen.")] = None,
    material_id: Annotated[int | None, Query(gt=0, description="Recepciones que tienen este material.")] = None,
    lote_id: Annotated[
        list[int] | None,
        Query(description="Recepciones con ítems que pasaron por alguno de estos lotes (se repite el parámetro)."),
    ] = None,
):
    """Material en curso por recepción: urgentes primero y, dentro de cada grupo, la más antigua primero."""
    return listar_tablero(db, urgente, servicio_id, material_id, lote_id)

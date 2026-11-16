from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import obtener_db, obtener_operador_actual
from app.schemas.lote import LoteDetalleOut, LoteResumenOut
from app.services.lote import listar_lotes, obtener_lote

# Solo lectura, pero con sesión iniciada, igual que recepciones.
router = APIRouter(
    prefix="/lotes",
    tags=["lotes"],
    dependencies=[Depends(obtener_operador_actual)],
)


@router.get("", response_model=list[LoteResumenOut])
def listar(
    db: Annotated[Session, Depends(obtener_db)],
    numero: Annotated[
        int | None,
        Query(ge=1, le=999, description="Número de lote. Se repite: puede devolver varios."),
    ] = None,
):
    """Lista de lotes, del más nuevo al más viejo."""
    return listar_lotes(db, numero)


@router.get("/{lote_id}", response_model=LoteDetalleOut)
def detalle(lote_id: int, db: Annotated[Session, Depends(obtener_db)]):
    """Detalle del lote con sus ítems y el historial de cada uno."""
    lote = obtener_lote(db, lote_id)
    if lote is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="El lote no existe")
    return lote

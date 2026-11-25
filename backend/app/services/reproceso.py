"""Reproceso de material (migración 0010): número de intento del historial.

Si falla el indicador interno, el material se vuelve a empacar antes de esterilizar.
Ese segundo paso por Empaque necesita un intento nuevo, porque la unicidad de
evento_item es (item, etapa, lote, intento). La reesterilización por falla de la
máquina sigue con el mismo intento: la distingue el lote.

PENDIENTE: la transición Esterilización (lote fallido) -> Empaque todavía no está
permitida en services/flujo.py. Queda para la API de reproceso, que usará
siguiente_intento al registrar el nuevo recorrido.
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import EventoItem


def siguiente_intento(db: Session, item_id: int) -> int:
    """Intento que corresponde a un nuevo recorrido del ítem (1 si no tiene historial)."""
    actual = db.scalar(select(func.max(EventoItem.intento)).where(EventoItem.item_id == item_id))
    return (actual or 0) + 1

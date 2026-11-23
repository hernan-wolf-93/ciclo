"""Servicios que no pueden compartir lote, según el método (migración 0010).

Neonatología y UTI no se mezclan solo en óxido de etileno; en autoclave y estufa sí
pueden ir juntos. La regla la va a usar la API de esterilización al armar un lote
(todavía no existe). Está en un módulo propio para no modificar services/flujo.py.
"""

from itertools import combinations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Servicio, ServicioIncompatible
from app.services.flujo import ErrorDeFlujo


def pares_incompatibles(db: Session, servicio_ids: set[int], metodo_id: int) -> list[tuple[int, int]]:
    """Pares (a, b) de esos servicios que no pueden ir juntos con ese método."""
    pares = {(a, b) for a, b in combinations(sorted(servicio_ids), 2)}
    if not pares:
        return []
    filas = db.execute(
        select(ServicioIncompatible.servicio_a_id, ServicioIncompatible.servicio_b_id).where(
            ServicioIncompatible.metodo_id == metodo_id,
            ServicioIncompatible.servicio_a_id.in_(servicio_ids),
            ServicioIncompatible.servicio_b_id.in_(servicio_ids),
        )
    )
    return sorted((a, b) for a, b in filas if (a, b) in pares)


def validar_servicios_compatibles(db: Session, servicio_ids: set[int], metodo_id: int) -> None:
    """Lanza ErrorDeFlujo si el lote mezclaría servicios incompatibles con ese método."""
    pares = pares_incompatibles(db, servicio_ids, metodo_id)
    if not pares:
        return
    a, b = pares[0]
    nombres = {s.id: s.nombre for s in db.scalars(select(Servicio).where(Servicio.id.in_([a, b])))}
    raise ErrorDeFlujo(f"{nombres[a]} y {nombres[b]} no pueden ir en el mismo lote con este método")

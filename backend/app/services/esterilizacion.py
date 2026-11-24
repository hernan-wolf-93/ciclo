"""Esterilización: qué material puede cargar un equipo.

Un equipo carga material de su método: ítems cuyo último evento es Empaque y que
tienen asignado ese método, más los ítems de un lote fallido de ese método que
esperan reesterilizarse. La misma consulta alimenta la lista de pendientes y la
elección de ítems al crear el lote, para que lo que se ve sea lo que se puede cargar.
"""

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.models import Equipo, Etapa, EventoItem, Item, Lote, Material, Recepcion, Servicio
from app.services.avance import ultimo_evento_por_item
from app.services.flujo import ORDEN_ESTERILIZACION, RESULTADO_FALLIDO
from app.services.numeracion_lote import EquipoInexistente

ORDEN_EMPAQUE = 3


def _disponibles(equipo: Equipo):
    """Consulta (ítem, servicio de origen, material) de lo que el equipo puede cargar."""
    ultimos = ultimo_evento_por_item()
    return (
        select(
            Item.id.label("item_id"),
            Recepcion.servicio_id.label("servicio_id"),
            Item.material_id.label("material_id"),
        )
        .select_from(EventoItem)
        .join(ultimos, ultimos.c.id == EventoItem.id)
        .join(Etapa, Etapa.id == EventoItem.etapa_id)
        .join(Item, Item.id == EventoItem.item_id)
        .join(Recepcion, Recepcion.id == Item.recepcion_id)
        .outerjoin(Lote, Lote.id == EventoItem.lote_id)
        .where(Item.metodo_id == equipo.metodo_id)
        .where(
            or_(
                Etapa.orden == ORDEN_EMPAQUE,
                and_(Etapa.orden == ORDEN_ESTERILIZACION, Lote.resultado == RESULTADO_FALLIDO),
            )
        )
    )


def elegir_items(
    db: Session,
    equipo: Equipo,
    servicio_id: int,
    material_id: int,
    cantidad: int,
    excluir=(),
) -> list[int]:
    """Ids de los ítems más antiguos que el equipo puede cargar, de un servicio y un material.

    Devuelve menos de los pedidos si no alcanzan: quien llama decide el error.
    Con excluir se saltean los que otra línea del mismo pedido ya eligió.
    """
    disponibles = _disponibles(equipo).subquery()
    consulta = select(disponibles.c.item_id).where(
        disponibles.c.servicio_id == servicio_id, disponibles.c.material_id == material_id
    )
    if excluir:
        consulta = consulta.where(disponibles.c.item_id.not_in(list(excluir)))
    return list(db.scalars(consulta.order_by(disponibles.c.item_id).limit(cantidad)))


def listar_pendientes_equipo(db: Session, equipo_id: int) -> list[dict]:
    """Material que puede cargar el equipo, por servicio de origen y material."""
    equipo = db.get(Equipo, equipo_id)
    if equipo is None:
        raise EquipoInexistente(f"No existe el equipo {equipo_id}")
    disponibles = _disponibles(equipo).subquery()
    filas = db.execute(
        select(
            Servicio.id.label("servicio_id"),
            Servicio.nombre.label("servicio"),
            Material.id.label("material_id"),
            Material.nombre.label("material"),
            func.count(disponibles.c.item_id).label("cantidad"),
        )
        .select_from(disponibles)
        .join(Servicio, Servicio.id == disponibles.c.servicio_id)
        .join(Material, Material.id == disponibles.c.material_id)
        .group_by(Servicio.id, Servicio.nombre, Material.id, Material.nombre)
        .order_by(Servicio.nombre, Material.nombre)
    ).mappings()
    return [dict(fila) for fila in filas]
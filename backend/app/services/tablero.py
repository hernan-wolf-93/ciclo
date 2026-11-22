"""Tablero de material en curso (RF7 y RF6): consultas de solo lectura.

Una fila por recepción con al menos un ítem que todavía no llegó a Entrega. La
etapa de cada ítem se deduce de su último evento con situaciones_de_items
(services/flujo.py). Desde Esterilización, la fila muestra el último lote de
esos ítems.
"""

from collections import Counter, defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Equipo, EventoItem, Item, Lote, Material, Recepcion, Servicio
from app.schemas.tablero import (
    FilaTableroOut,
    LoteDeFilaOut,
    MaterialEnCursoOut,
    ServicioRef,
)
from app.services.flujo import situaciones_de_items

ORDEN_ENTREGA = 6
ORDENES = range(1, ORDEN_ENTREGA + 1)


def ultimo_lote_por_item(db: Session, item_ids: list[int]) -> dict[int, int]:
    """Para cada ítem, el lote de su último evento con lote (el de mayor id).

    Solo los eventos de Esterilización llevan lote_id: si el ítem se reesterilizó,
    gana el lote del último intento.
    """
    filas = db.execute(
        select(EventoItem.item_id, EventoItem.lote_id)
        .where(EventoItem.item_id.in_(item_ids), EventoItem.lote_id.is_not(None))
        .order_by(EventoItem.id)
    )
    return {item_id: lote_id for item_id, lote_id in filas}  # el último pisa a los anteriores


def listar_tablero(
    db: Session,
    urgente: bool | None = None,
    servicio_id: int | None = None,
    material_id: int | None = None,
    lote_ids: list[int] | None = None,
) -> list[FilaTableroOut]:
    """Recepciones en curso: urgentes primero y, dentro de cada grupo, la más antigua primero.

    Filtros: urgente, servicio de origen, material (recepciones que lo tienen) y
    lotes (recepciones con algún ítem que pasó por alguno de esos lotes).
    """
    # TODO: hoy se leen todas las recepciones que cumplen los filtros y después se
    # descartan las ya entregadas. Si el volumen crece, filtrar en SQL o paginar.
    consulta = (
        select(Recepcion)
        .order_by(Recepcion.urgente.desc(), Recepcion.fecha_hora, Recepcion.id)
    )
    if urgente is not None:
        consulta = consulta.where(Recepcion.urgente.is_(urgente))
    if servicio_id is not None:
        consulta = consulta.where(Recepcion.servicio_id == servicio_id)
    if material_id is not None:
        consulta = consulta.where(
            Recepcion.id.in_(select(Item.recepcion_id).where(Item.material_id == material_id))
        )
    if lote_ids:
        consulta = consulta.where(
            Recepcion.id.in_(
                select(Item.recepcion_id)
                .join(EventoItem, EventoItem.item_id == Item.id)
                .where(EventoItem.lote_id.in_(lote_ids))
            )
        )
    recepciones = list(db.scalars(consulta))
    if not recepciones:
        return []

    items = list(
        db.scalars(select(Item).where(Item.recepcion_id.in_([r.id for r in recepciones])).order_by(Item.id))
    )
    if not items:
        return []

    item_ids = [item.id for item in items]
    situaciones = situaciones_de_items(db, item_ids)
    lote_por_item = ultimo_lote_por_item(db, item_ids)

    # Catálogos que hacen falta, con una consulta por tabla
    servicios = {
        s.id: s for s in db.scalars(select(Servicio).where(Servicio.id.in_({r.servicio_id for r in recepciones})))
    }
    materiales = {
        m.id: m for m in db.scalars(select(Material).where(Material.id.in_({i.material_id for i in items})))
    }
    lotes = {
        lote.id: (lote, nombre_equipo)
        for lote, nombre_equipo in db.execute(
            select(Lote, Equipo.nombre)
            .join(Equipo, Equipo.id == Lote.equipo_id)
            .where(Lote.id.in_(set(lote_por_item.values())))
        )
    }

    items_por_recepcion: dict[int, list[Item]] = defaultdict(list)
    for item in items:
        items_por_recepcion[item.recepcion_id].append(item)

    filas: list[FilaTableroOut] = []
    for recepcion in recepciones:
        propios = items_por_recepcion.get(recepcion.id, [])
        etapas = {item.id: situaciones[item.id].orden_etapa for item in propios}

        # En curso: algún ítem todavía no llegó a Entrega
        if not propios or all(orden == ORDEN_ENTREGA for orden in etapas.values()):
            continue

        conteo = Counter(etapas.values())
        por_material = Counter((item.material_id, etapas[item.id]) for item in propios)
        lotes_de_fila = sorted({lote_por_item[i.id] for i in propios if i.id in lote_por_item})

        filas.append(
            FilaTableroOut(
                recepcion_id=recepcion.id,
                fecha_hora=recepcion.fecha_hora,
                urgente=recepcion.urgente,
                servicio=ServicioRef(id=recepcion.servicio_id, nombre=servicios[recepcion.servicio_id].nombre),
                total_items=len(propios),
                por_etapa={orden: conteo.get(orden, 0) for orden in ORDENES},
                materiales=[
                    MaterialEnCursoOut(
                        material_id=material_id_,
                        nombre=materiales[material_id_].nombre,
                        codigo=materiales[material_id_].codigo,
                        etapa_orden=orden,
                        cantidad=cantidad,
                    )
                    for (material_id_, orden), cantidad in sorted(
                        por_material.items(), key=lambda par: (par[0][1], materiales[par[0][0]].nombre)
                    )
                ],
                lotes=[
                    LoteDeFilaOut(
                        id=lote_id,
                        numero=lotes[lote_id][0].numero,
                        equipo=lotes[lote_id][1],
                        resultado=lotes[lote_id][0].resultado,
                    )
                    for lote_id in lotes_de_fila
                ],
            )
        )
    return filas

"""Historial de lotes (RF3): consultas de solo lectura.

Un lote es la carga de un equipo de esterilización. Sus ítems salen de
evento_item.lote_id (no de item.lote_id), para que un lote fallido siga
mostrando el material que pasó por él aunque después se haya reesterilizado.
"""

from collections import defaultdict
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models import Equipo, Etapa, EventoItem, Item, Lote, Material, Operador, Programa, Recepcion, Servicio
from app.schemas.lote import (
    EquipoOut,
    EtapaOut,
    EventoItemOut,
    ItemDelLoteOut,
    LoteDetalleOut,
    LoteRef,
    LoteResumenOut,
    MaterialOut,
    OperadorOut,
    ProgramaOut,
    ServicioOut,
)

ORDEN_ESTERILIZACION = 4

# Mismo criterio que frontend/src/utils/aireacion.ts: el modelo no marca qué
# método lleva aireación, así que se reconoce por el nombre de la migración 0002.
METODO_CON_AIREACION = "Óxido de etileno"


def fin_aireacion(nombre_metodo: str, fin: datetime | None, dias_max: int | None) -> datetime | None:
    """Fin de la aireación de un lote: lote.fin + el mayor dias_aireacion de sus ítems.

    Devuelve None si el método no lleva aireación, si el lote no terminó o si no
    tiene ítems. Es la misma regla que el frontend aplica ítem por ítem.
    """
    if nombre_metodo != METODO_CON_AIREACION or fin is None or dias_max is None:
        return None
    return fin + timedelta(days=dias_max)


def _equipos(db: Session, ids: set[int]) -> dict[int, Equipo]:
    consulta = select(Equipo).options(selectinload(Equipo.metodo)).where(Equipo.id.in_(ids))
    return {equipo.id: equipo for equipo in db.scalars(consulta)}


def _dias_aireacion_por_lote(db: Session, lote_ids: list[int]) -> dict[int, int]:
    """Para cada lote, el mayor dias_aireacion entre los servicios de origen de sus ítems."""
    filas = db.execute(
        select(EventoItem.lote_id, func.max(Servicio.dias_aireacion))
        .join(Item, Item.id == EventoItem.item_id)
        .join(Recepcion, Recepcion.id == Item.recepcion_id)
        .join(Servicio, Servicio.id == Recepcion.servicio_id)
        .where(EventoItem.lote_id.in_(lote_ids))
        .group_by(EventoItem.lote_id)
    )
    return {lote_id: dias for lote_id, dias in filas}


def listar_lotes(db: Session, numero: int | None = None) -> list[LoteResumenOut]:
    """Lotes del más nuevo al más viejo. Con numero puede haber varios: se repite."""
    consulta = select(Lote).order_by(Lote.inicio.desc(), Lote.id.desc())
    if numero is not None:
        consulta = consulta.where(Lote.numero == numero)
    lotes = list(db.scalars(consulta))
    if not lotes:
        return []

    equipos = _equipos(db, {lote.equipo_id for lote in lotes})
    dias = _dias_aireacion_por_lote(db, [lote.id for lote in lotes])

    return [
        LoteResumenOut(
            id=lote.id,
            numero=lote.numero,
            inicio=lote.inicio,
            fin=lote.fin,
            equipo=EquipoOut.model_validate(equipos[lote.equipo_id]),
            resultado=lote.resultado,
            aireacion_fin_max=fin_aireacion(
                equipos[lote.equipo_id].metodo.nombre, lote.fin, dias.get(lote.id)
            ),
        )
        for lote in lotes
    ]


def _lotes_vecinos(
    eventos_por_item: dict[int, list[EventoItem]],
    etapa_esterilizacion_id: int | None,
    lote_id: int,
) -> tuple[set[int], set[int]]:
    """Lotes anteriores y siguientes a este en las esterilizaciones de sus ítems.

    Un ítem reesterilizado tiene dos eventos de Esterilización, cada uno con su
    lote: el anterior es el lote fallido y el siguiente, el de reemplazo.
    """
    anteriores: set[int] = set()
    siguientes: set[int] = set()
    for eventos in eventos_por_item.values():
        secuencia = [
            e.lote_id
            for e in eventos
            if e.etapa_id == etapa_esterilizacion_id and e.lote_id is not None
        ]
        if lote_id not in secuencia:
            continue
        posicion = secuencia.index(lote_id)
        if posicion > 0:
            anteriores.add(secuencia[posicion - 1])
        if posicion < len(secuencia) - 1:
            siguientes.add(secuencia[posicion + 1])
    return anteriores, siguientes


def _primer_lote(db: Session, ids: set[int]) -> LoteRef | None:
    # TODO: si los ítems de un lote fallido se reesterilizaron en lotes distintos,
    # se devuelve el primero por fecha de inicio. Pendiente con el servicio:
    # "¿un lote falla siempre completo?" (docs/DER.md).
    if not ids:
        return None
    lote = db.scalar(select(Lote).where(Lote.id.in_(ids)).order_by(Lote.inicio, Lote.id).limit(1))
    return LoteRef(id=lote.id, numero=lote.numero)


def obtener_lote(db: Session, lote_id: int) -> LoteDetalleOut | None:
    """Detalle del lote con sus ítems y el historial de cada uno. None si no existe."""
    lote = db.get(Lote, lote_id)
    if lote is None:
        return None

    equipo = _equipos(db, {lote.equipo_id})[lote.equipo_id]
    programa = db.get(Programa, lote.programa_id)

    # Ítems que pasaron por el lote: los que tienen un evento con este lote_id.
    items = list(
        db.scalars(
            select(Item)
            .where(Item.id.in_(select(EventoItem.item_id).where(EventoItem.lote_id == lote.id)))
            .order_by(Item.id)
        )
    )
    item_ids = [item.id for item in items]

    # Todo el historial de esos ítems. A igual hora (misma transacción) desempata el id.
    eventos = list(
        db.scalars(
            select(EventoItem)
            .where(EventoItem.item_id.in_(item_ids))
            .order_by(EventoItem.fecha_hora, EventoItem.id)
        )
    )
    eventos_por_item: dict[int, list[EventoItem]] = defaultdict(list)
    for evento in eventos:
        eventos_por_item[evento.item_id].append(evento)

    # El modelo no tiene relaciones desde evento_item ni item hacia estos
    # catálogos: se traen aparte, con una consulta por tabla.
    etapas = {etapa.id: etapa for etapa in db.scalars(select(Etapa))}
    operadores = {
        o.id: o
        for o in db.scalars(
            select(Operador).where(Operador.id.in_({e.operador_id for e in eventos} | {lote.operador_id}))
        )
    }
    materiales = {
        m.id: m for m in db.scalars(select(Material).where(Material.id.in_({i.material_id for i in items})))
    }
    servicios_por_recepcion = {
        recepcion_id: servicio
        for recepcion_id, servicio in db.execute(
            select(Recepcion.id, Servicio)
            .join(Servicio, Servicio.id == Recepcion.servicio_id)
            .where(Recepcion.id.in_({i.recepcion_id for i in items}))
        )
    }

    etapa_esterilizacion_id = next(
        (etapa.id for etapa in etapas.values() if etapa.orden == ORDEN_ESTERILIZACION), None
    )
    anteriores, siguientes = _lotes_vecinos(eventos_por_item, etapa_esterilizacion_id, lote.id)

    return LoteDetalleOut(
        id=lote.id,
        numero=lote.numero,
        equipo_id=lote.equipo_id,
        programa_id=lote.programa_id,
        operador_id=lote.operador_id,
        inicio=lote.inicio,
        fin=lote.fin,
        resultado=lote.resultado,
        observacion=lote.observacion,
        equipo=EquipoOut.model_validate(equipo),
        programa=ProgramaOut.model_validate(programa),
        operador=OperadorOut.model_validate(operadores[lote.operador_id]),
        reemplazado_por=_primer_lote(db, siguientes),
        reemplaza_a=_primer_lote(db, anteriores),
        items=[
            ItemDelLoteOut(
                id=item.id,
                recepcion_id=item.recepcion_id,
                material_id=item.material_id,
                metodo_id=item.metodo_id,
                lote_id=item.lote_id,
                entrega_id=item.entrega_id,
                material=MaterialOut.model_validate(materiales[item.material_id]),
                servicio=ServicioOut.model_validate(servicios_por_recepcion[item.recepcion_id]),
                eventos=[
                    EventoItemOut(
                        id=e.id,
                        item_id=e.item_id,
                        etapa_id=e.etapa_id,
                        operador_id=e.operador_id,
                        lote_id=e.lote_id,
                        fecha_hora=e.fecha_hora,
                        etapa=EtapaOut.model_validate(etapas[e.etapa_id]),
                        operador=OperadorOut.model_validate(operadores[e.operador_id]),
                    )
                    for e in eventos_por_item[item.id]
                ],
            )
            for item in items
        ],
    )

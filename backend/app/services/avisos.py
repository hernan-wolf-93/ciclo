"""Avisos de material detenido y listo para retirar (RF4 y RF7): solo lectura.

La etapa de cada ítem sale de su último evento (situaciones_de_items, en
services/flujo.py). Los umbrales están en services/reglas_avisos.py. "ahora" se
recibe como parámetro: el router lo toma del reloj y las pruebas usan una fecha fija.
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Equipo, EventoItem, Item, Lote, Material, MetodoEsterilizacion, Programa, Recepcion, Servicio
from app.schemas.aviso import AvisoOut, LoteAvisoRef, MaterialRef
from app.schemas.tablero import ServicioRef
from app.services import reglas_avisos as reglas
from app.services.flujo import situaciones_de_items
from app.services.tablero import ultimo_lote_por_item

ORDEN_ESTERILIZACION = 4
ORDEN_ALMACEN = 5

# Texto de cada motivo; {dur} es el tiempo transcurrido y {lote} el N.º y equipo
MOTIVOS = {
    1: "Lleva {dur} sin pasar a Lavado.",
    2: "Lleva {dur} sin pasar a Empaque.",
    3: "Lleva {dur} esperando esterilización.",
    "lote_sin_cerrar": "El lote {lote} lleva {dur} sin cerrarse.",
    "lote_fallido": "El lote {lote} falló hace {dur}: falta reesterilizar.",
    "falta_almacen": "El lote {lote} se cerró hace {dur}: falta pasar a Almacén.",
    "sin_resultado": "El lote {lote} se cerró hace {dur} sin resultado cargado.",
    "aireacion_cumplida": "Aireación cumplida hace {dur}: el servicio puede retirar.",
}


@dataclass(frozen=True)
class _Clave:
    """Lo que agrupa a los ítems en un mismo aviso."""

    tipo: str
    motivo: str | int
    recepcion_id: int
    material_id: int
    etapa_orden: int
    lote_id: int | None
    umbral: int | None


def _fecha_ultimo_evento(db: Session, item_ids: list[int]) -> dict[int, datetime]:
    """Fecha del último evento de cada ítem (el de mayor id, mismo criterio que flujo.py)."""
    ultimos = (
        select(func.max(EventoItem.id).label("id"))
        .where(EventoItem.item_id.in_(item_ids))
        .group_by(EventoItem.item_id)
        .subquery()
    )
    filas = db.execute(select(EventoItem.item_id, EventoItem.fecha_hora).join(ultimos, ultimos.c.id == EventoItem.id))
    return {item_id: fecha for item_id, fecha in filas}


@dataclass(frozen=True)
class _InfoLote:
    """Lo que hace falta de un lote para aplicar las reglas."""

    lote: Lote
    equipo: str
    metodo: str
    requiere_aireacion: bool  # metodo_esterilizacion.requiere_aireacion (migración 0010)
    duracion_programa: int | None  # minutos según el panel del equipo; None si no tiene tiempos


def _regla_del_item(etapa: int, desde_evento: datetime, info: _InfoLote | None,
                    dias_aireacion: int, ahora: datetime) -> tuple[str, str | int, datetime, int | None] | None:
    """Devuelve (tipo, motivo, desde, umbral) si el ítem genera un aviso, o None."""
    if etapa in reglas.UMBRAL_POR_ETAPA_MIN:
        umbral = reglas.UMBRAL_POR_ETAPA_MIN[etapa]
        return ("detenido", etapa, desde_evento, umbral) if reglas.supera(desde_evento, ahora, umbral) else None

    if etapa not in (ORDEN_ESTERILIZACION, ORDEN_ALMACEN) or info is None:
        return None
    lote = info.lote

    # Método con aireación y lote aprobado: aviso cuando se cumple (en Esterilización o en Almacén)
    if info.requiere_aireacion and lote.resultado == "aprobado" and lote.fin is not None:
        fin_aireacion = lote.fin + timedelta(days=dias_aireacion)
        return ("listo_para_retirar", "aireacion_cumplida", fin_aireacion, None) if ahora >= fin_aireacion else None

    if etapa == ORDEN_ALMACEN:
        return None  # almacenamiento normal: sin umbral

    # En Esterilización
    if lote.fin is None:
        umbral = reglas.umbral_esterilizacion_programa(info.metodo, info.duracion_programa)
        return ("detenido", "lote_sin_cerrar", lote.inicio, umbral) if reglas.supera(lote.inicio, ahora, umbral) else None

    umbral = reglas.UMBRAL_TRAS_CIERRE_MIN
    if not reglas.supera(lote.fin, ahora, umbral):
        return None
    if lote.resultado == "fallido":
        return ("detenido", "lote_fallido", lote.fin, umbral)
    if lote.resultado is None:
        return ("detenido", "sin_resultado", lote.fin, umbral)
    if reglas.AVISAR_FALTA_ALMACEN:
        return ("detenido", "falta_almacen", lote.fin, umbral)
    return None


def listar_avisos(db: Session, ahora: datetime) -> list[AvisoOut]:
    """Avisos agrupados por recepción, material, etapa y motivo.

    Primero los detenidos, del que más se pasó de su umbral al que menos; después
    los listos para retirar, del más viejo al más nuevo.
    """
    # TODO: hoy se revisan todos los ítems; si el volumen crece, filtrar los entregados en SQL.
    items = list(db.scalars(select(Item).order_by(Item.id)))
    if not items:
        return []
    item_ids = [item.id for item in items]

    situaciones = situaciones_de_items(db, item_ids)
    fechas = _fecha_ultimo_evento(db, item_ids)
    lote_por_item = ultimo_lote_por_item(db, item_ids)

    # Catálogos, con una consulta por tabla
    lotes = {
        lote.id: _InfoLote(
            lote=lote,
            equipo=equipo,
            metodo=metodo.nombre,
            requiere_aireacion=metodo.requiere_aireacion,
            duracion_programa=reglas.duracion_programa(
                programa.tiempo_esterilizacion_min, programa.tiempo_secado_min, programa.tiempo_desgasificacion_min
            ),
        )
        for lote, equipo, metodo, programa in db.execute(
            select(Lote, Equipo.nombre, MetodoEsterilizacion, Programa)
            .join(Equipo, Equipo.id == Lote.equipo_id)
            .join(MetodoEsterilizacion, MetodoEsterilizacion.id == Equipo.metodo_id)
            .join(Programa, Programa.id == Lote.programa_id)
            .where(Lote.id.in_(set(lote_por_item.values())))
        )
    }
    servicio_por_recepcion = {
        recepcion_id: servicio
        for recepcion_id, servicio in db.execute(
            select(Recepcion.id, Servicio)
            .join(Servicio, Servicio.id == Recepcion.servicio_id)
            .where(Recepcion.id.in_({i.recepcion_id for i in items}))
        )
    }
    materiales = {m.id: m for m in db.scalars(select(Material).where(Material.id.in_({i.material_id for i in items})))}

    grupos: dict[_Clave, list[datetime]] = defaultdict(list)
    for item in items:
        etapa = situaciones[item.id].orden_etapa
        lote_id = lote_por_item.get(item.id) if etapa >= ORDEN_ESTERILIZACION else None
        servicio = servicio_por_recepcion[item.recepcion_id]

        regla = _regla_del_item(etapa, fechas[item.id], lotes.get(lote_id), servicio.dias_aireacion, ahora)
        if regla is None:
            continue
        tipo, motivo, desde, umbral = regla
        clave = _Clave(tipo, motivo, item.recepcion_id, item.material_id, etapa, lote_id, umbral)
        grupos[clave].append(desde)

    avisos: list[AvisoOut] = []
    for clave, fechas_grupo in grupos.items():
        desde = min(fechas_grupo)
        minutos = reglas.minutos_entre(desde, ahora)
        lote_ref = None
        texto_lote = ""
        if clave.lote_id is not None:
            info = lotes[clave.lote_id]
            lote_ref = LoteAvisoRef(id=info.lote.id, numero=info.lote.numero, equipo=info.equipo)
            texto_lote = f"N.º {info.lote.numero:02d} de {info.equipo}"
        servicio = servicio_por_recepcion[clave.recepcion_id]
        material = materiales[clave.material_id]
        avisos.append(
            AvisoOut(
                tipo=clave.tipo,
                recepcion_id=clave.recepcion_id,
                servicio=ServicioRef(id=servicio.id, nombre=servicio.nombre),
                material=MaterialRef(id=material.id, nombre=material.nombre, codigo=material.codigo),
                cantidad=len(fechas_grupo),
                etapa_orden=clave.etapa_orden,
                lote=lote_ref,
                desde=desde,
                minutos_transcurridos=minutos,
                umbral_minutos=clave.umbral,
                motivo=MOTIVOS[clave.motivo].format(dur=reglas.duracion(minutos), lote=texto_lote),
            )
        )

    detenidos = sorted(
        (a for a in avisos if a.tipo == "detenido"),
        key=lambda a: (-(a.minutos_transcurridos - (a.umbral_minutos or 0)), a.recepcion_id, a.material.nombre),
    )
    listos = sorted((a for a in avisos if a.tipo == "listo_para_retirar"), key=lambda a: (a.desde, a.recepcion_id))
    return detenidos + listos

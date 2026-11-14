"""Reglas de flujo por etapas (RF4).

Decide si un ítem puede pasar de una etapa a otra. Las etapas se identifican
por su orden (1 a 6, ver migración 0002). validar_transicion es una función pura;
situacion_del_item y validar_avance consultan el historial del ítem.
"""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Etapa, EventoItem, Lote

ORDEN_PRIMERA_ETAPA = 1
ORDEN_ESTERILIZACION = 4
ORDEN_ALMACEN = 5
ORDEN_ULTIMA_ETAPA = 6

RESULTADO_APROBADO = "aprobado"
RESULTADO_FALLIDO = "fallido"


class ErrorDeFlujo(Exception):
    """Una transición de etapa no está permitida."""


def validar_transicion(
    orden_actual: int,
    orden_destino: int,
    resultado_ultimo_lote: str | None = None,
) -> None:
    """Lanza ErrorDeFlujo si el ítem no puede pasar de una etapa a otra.

    resultado_ultimo_lote solo importa cuando el ítem está en Esterilización:
    es el resultado del lote de su último evento (None si el lote sigue en curso).
    """
    if not ORDEN_PRIMERA_ETAPA <= orden_destino <= ORDEN_ULTIMA_ETAPA:
        raise ErrorDeFlujo("La etapa de destino no existe")

    if orden_actual == ORDEN_ESTERILIZACION:
        _validar_salida_de_esterilizacion(orden_destino, resultado_ultimo_lote)
        return

    if orden_destino != orden_actual + 1:
        raise ErrorDeFlujo(
            f"No se puede pasar de la etapa {orden_actual} a la {orden_destino}: "
            "solo se avanza a la etapa siguiente"
        )


def _validar_salida_de_esterilizacion(orden_destino: int, resultado: str | None) -> None:
    if resultado is None:
        raise ErrorDeFlujo(
            "El lote de esterilización sigue en curso: hay que cerrarlo antes de avanzar"
        )
    if orden_destino == ORDEN_ESTERILIZACION:
        if resultado != RESULTADO_FALLIDO:
            raise ErrorDeFlujo("Solo se puede reesterilizar un ítem cuyo lote quedó fallido")
        return
    if orden_destino == ORDEN_ALMACEN:
        if resultado != RESULTADO_APROBADO:
            raise ErrorDeFlujo(
                "Un ítem de un lote fallido no avanza a Almacén: debe reesterilizarse"
            )
        return
    raise ErrorDeFlujo(
        "Desde Esterilización solo se avanza a Almacén (lote aprobado) "
        "o se reesterilizan (lote fallido)"
    )
    
@dataclass(frozen=True)
class SituacionItem:
    """Dónde está un ítem: etapa actual y resultado del lote de su último evento."""

    orden_etapa: int
    resultado_ultimo_lote: str | None


def situacion_del_item(db: Session, item_id: int) -> SituacionItem:
    """Deduce la situación del ítem a partir de su último evento (el de mayor id)."""
    fila = db.execute(
        select(Etapa.orden, Lote.resultado)
        .select_from(EventoItem)
        .join(Etapa, Etapa.id == EventoItem.etapa_id)
        .outerjoin(Lote, Lote.id == EventoItem.lote_id)
        .where(EventoItem.item_id == item_id)
        .order_by(EventoItem.id.desc())
        .limit(1)
    ).first()
    if fila is None:
        raise ErrorDeFlujo("El ítem no existe o no tiene historial")
    return SituacionItem(orden_etapa=fila.orden, resultado_ultimo_lote=fila.resultado)


def validar_avance(db: Session, item_id: int, orden_destino: int) -> None:
    """Lanza ErrorDeFlujo si el ítem no puede pasar a la etapa de destino."""
    situacion = situacion_del_item(db, item_id)
    validar_transicion(situacion.orden_etapa, orden_destino, situacion.resultado_ultimo_lote)
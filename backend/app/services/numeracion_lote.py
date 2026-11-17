"""Numeración de lotes (RF3): propuesta del número siguiente para un método.

El servicio numera del 1 al 999 y reinicia al llegar a 999. El número lo
confirma el operador, que lo escribe en el equipo: acá solo se propone.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Equipo, Lote

NUMERO_MAXIMO = 999


def siguiente_numero(ultimo: int | None) -> int:
    """Número que se propone después del último lote del método.

    ultimo es None si el método todavía no tiene lotes.
    """
    if ultimo is None:
        return 1
    if not 1 <= ultimo <= NUMERO_MAXIMO:
        raise ValueError(f"Número de lote fuera de rango: {ultimo}")
    return 1 if ultimo == NUMERO_MAXIMO else ultimo + 1

class EquipoInexistente(Exception):
    """El equipo para el que se pide el número no existe."""


def proponer_numero(db: Session, equipo_id: int) -> int:
    """Número que se propone para el próximo lote de un equipo.

    La numeración es por método: se toma el último lote creado en cualquier
    equipo del mismo método. "Último" es el de mayor id y no el de mayor
    número, porque tras un reinicio el número más alto no es el más reciente.
    """
    equipo = db.get(Equipo, equipo_id)
    if equipo is None:
        raise EquipoInexistente(f"No existe el equipo {equipo_id}")

    ultimo = db.scalar(
        select(Lote.numero)
        .join(Equipo, Equipo.id == Lote.equipo_id)
        .where(Equipo.metodo_id == equipo.metodo_id)
        .order_by(Lote.id.desc())
        .limit(1)
    )
    return siguiente_numero(ultimo)
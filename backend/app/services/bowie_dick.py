"""Prueba Bowie-Dick (regla principal del servicio): obligatoria todos los días antes
de usar el autoclave.

Esta es solo la consulta. La validación "no se puede esterilizar en el autoclave sin
un Bowie-Dick aprobado hoy" va en la API de esterilización, que todavía no existe:
ese endpoint tiene que llamar a hay_bowie_dick_aprobado_hoy antes de crear el lote.
"""

from datetime import datetime, time
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ControlBowieDick

# El "día" del servicio es el de Tucumán, no el de UTC
ZONA_SERVICIO = ZoneInfo("America/Argentina/Tucuman")


def inicio_del_dia(ahora: datetime) -> datetime:
    """Medianoche local del día de "ahora" (con zona)."""
    local = ahora.astimezone(ZONA_SERVICIO)
    return datetime.combine(local.date(), time.min, tzinfo=ZONA_SERVICIO)


def hay_bowie_dick_aprobado_hoy(db: Session, equipo_id: int, ahora: datetime) -> bool:
    """True si el último control Bowie-Dick de hoy de ese equipo está aprobado.

    Cuenta el último: un control aprobado seguido de uno fallido el mismo día da False.
    """
    ultimo = db.scalar(
        select(ControlBowieDick.resultado)
        .where(
            ControlBowieDick.equipo_id == equipo_id,
            ControlBowieDick.fecha_hora >= inicio_del_dia(ahora),
            ControlBowieDick.fecha_hora <= ahora,
        )
        .order_by(ControlBowieDick.fecha_hora.desc(), ControlBowieDick.id.desc())
        .limit(1)
    )
    return ultimo == "aprobado"

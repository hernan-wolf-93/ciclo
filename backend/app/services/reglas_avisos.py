"""Umbrales de los avisos de material detenido (RF4 y RF7).

Todos los tiempos son PROVISORIOS: los tipos de alerta y sus tiempos todavía no
están definidos con la jefa del servicio. Este es el único lugar donde se cambian.
No hay una regla fija de 2 horas: la jefa pidió respetar el tiempo de cada método
y la aireación del óxido de etileno, y no avisar mientras el material está dentro
de su tiempo normal.

TODO: confirmar todos los valores con el servicio.
"""

from datetime import datetime, timedelta

from app.services.lote import METODO_CON_AIREACION  # noqa: F401  (misma regla que el historial)

# Etapas 1 a 3: minutos desde el último evento del ítem
UMBRAL_POR_ETAPA_MIN: dict[int, int] = {
    1: 120,  # Recepción: esperando lavado
    2: 180,  # Lavado y secado: lavado más secado
    3: 240,  # Empaque y rotulación: esperando que se arme un lote
}

# Esterilización con el lote sin cerrar (sin fin): minutos desde lote.inicio, por método.
# programa no tiene tiempos en la base: se usan los de los paneles de los equipos.
UMBRAL_ESTERILIZACION_POR_METODO_MIN: dict[str, int] = {
    "Calor húmedo": 90,  # autoclave: el ciclo más largo es Priones, 60 + 20 min, más los pulsos
    "Calor seco": 150,  # estufa: 180 °C durante 1 h, más el enfriado
    "Óxido de etileno": 900,  # 180 min de esterilización + 720 min de desgasificación
}
UMBRAL_ESTERILIZACION_POR_DEFECTO_MIN = 150  # método sin umbral cargado

# Lote ya cerrado (con fin): minutos desde lote.fin hasta que el material siga su camino
UMBRAL_TRAS_CIERRE_MIN = 60

# Aviso "Lote cerrado: falta pasar a Almacén".
# TODO: la jefa dijo que la etapa de almacén se podría omitir; está pendiente de
# decidir. Si se omite, poner False y el aviso deja de aparecer.
AVISAR_FALTA_ALMACEN = True


def minutos_entre(desde: datetime, ahora: datetime) -> int:
    """Minutos enteros transcurridos. Las dos fechas tienen que tener zona horaria."""
    return int((ahora - desde).total_seconds() // 60)


def supera(desde: datetime, ahora: datetime, umbral_min: int) -> bool:
    """True si pasó el umbral (o justo se cumplió)."""
    return ahora - desde >= timedelta(minutes=umbral_min)


def umbral_esterilizacion(nombre_metodo: str) -> int:
    return UMBRAL_ESTERILIZACION_POR_METODO_MIN.get(nombre_metodo, UMBRAL_ESTERILIZACION_POR_DEFECTO_MIN)


def duracion(minutos: int) -> str:
    """'45 min', '3 h 20 min', '2 d 3 h'."""
    if minutos < 60:
        return f"{minutos} min"
    horas, resto = divmod(minutos, 60)
    if horas < 24:
        return f"{horas} h {resto} min" if resto else f"{horas} h"
    dias, horas = divmod(horas, 24)
    return f"{dias} d {horas} h" if horas else f"{dias} d"

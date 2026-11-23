"""Umbrales de los avisos de material detenido (RF4 y RF7).

Los tiempos de las etapas 1 a 3 y los márgenes son PROVISORIOS: los tipos de alerta
y sus tiempos todavía no están definidos con la jefa del servicio. Este es el único
lugar donde se cambian. No hay una regla fija de 2 horas: la jefa pidió respetar el
tiempo de cada método y la aireación del óxido de etileno, y no avisar mientras el
material está dentro de su tiempo normal.

TODO: confirmar los valores provisorios con el servicio.
"""

from datetime import datetime, timedelta

# Etapas 1 a 3: minutos desde el último evento del ítem
UMBRAL_POR_ETAPA_MIN: dict[int, int] = {
    1: 120,  # Recepción: esperando lavado
    2: 180,  # Lavado y secado: lavado más secado
    3: 240,  # Empaque y rotulación: esperando que se arme un lote
}

# Esterilización con el lote sin cerrar: el umbral sale de los tiempos del programa
# (esterilización + secado + desgasificación, migración 0010) más este margen.
# TODO: margen provisorio; el panel no informa el tiempo de los pulsos de vacío ni
# el de calentamiento.
MARGEN_ESTERILIZACION_MIN = 30

# Piso por método: el umbral del programa nunca queda por debajo de estos valores,
# y son el umbral cuando el programa no tiene tiempos (por ejemplo, P de la estufa).
UMBRAL_ESTERILIZACION_POR_METODO_MIN: dict[str, int] = {
    "Calor húmedo": 90,  # autoclave: el ciclo más largo es Priones, 60 + 20 min, más los pulsos
    "Calor seco": 150,  # estufa: hasta 120 min (programa A) más el enfriado
    "Óxido de etileno": 900,  # 180 min de esterilización + 720 min de desgasificación
}
UMBRAL_ESTERILIZACION_POR_DEFECTO_MIN = 150  # método sin umbral cargado

# Lote ya cerrado (con fin): minutos desde lote.fin hasta que el material siga su camino
UMBRAL_TRAS_CIERRE_MIN = 60

# Aviso "Lote cerrado: falta pasar a Almacén". El servicio confirmó que la etapa de
# almacén no se omite (docs/RESPUESTAS-SERVICIO.md).
AVISAR_FALTA_ALMACEN = True


def minutos_entre(desde: datetime, ahora: datetime) -> int:
    """Minutos enteros transcurridos. Las dos fechas tienen que tener zona horaria."""
    return int((ahora - desde).total_seconds() // 60)


def supera(desde: datetime, ahora: datetime, umbral_min: int) -> bool:
    """True si pasó el umbral (o justo se cumplió)."""
    return ahora - desde >= timedelta(minutes=umbral_min)


def umbral_esterilizacion(nombre_metodo: str) -> int:
    """Piso del método (o el umbral si el programa no tiene tiempos)."""
    return UMBRAL_ESTERILIZACION_POR_METODO_MIN.get(nombre_metodo, UMBRAL_ESTERILIZACION_POR_DEFECTO_MIN)


def duracion_programa(
    tiempo_esterilizacion_min: int | None,
    tiempo_secado_min: int | None,
    tiempo_desgasificacion_min: int | None,
) -> int | None:
    """Minutos que dura el programa según su panel. None si no tiene tiempos."""
    tiempos = [tiempo_esterilizacion_min, tiempo_secado_min, tiempo_desgasificacion_min]
    if all(t is None for t in tiempos):
        return None
    return sum(t or 0 for t in tiempos)


def umbral_esterilizacion_programa(nombre_metodo: str, duracion_min: int | None) -> int:
    """Umbral de un lote sin cerrar: duración del programa + margen, nunca menos que
    el piso del método. Sin tiempos en el programa, el piso del método."""
    piso = umbral_esterilizacion(nombre_metodo)
    if duracion_min is None:
        return piso
    return max(duracion_min + MARGEN_ESTERILIZACION_MIN, piso)


def duracion(minutos: int) -> str:
    """'45 min', '3 h 20 min', '2 d 3 h'."""
    if minutos < 60:
        return f"{minutos} min"
    horas, resto = divmod(minutos, 60)
    if horas < 24:
        return f"{horas} h {resto} min" if resto else f"{horas} h"
    dias, horas = divmod(horas, 24)
    return f"{dias} d {horas} h" if horas else f"{dias} d"

"""Reglas de flujo por etapas (RF4).

Decide si un ítem puede pasar de una etapa a otra. Las etapas se identifican
por su orden (1 a 6, ver migración 0002). Este módulo no consulta la base.
"""

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
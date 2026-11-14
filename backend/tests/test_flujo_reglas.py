import pytest

from app.services.flujo import ErrorDeFlujo, validar_transicion


@pytest.mark.parametrize(
    "actual, destino, resultado",
    [
        (1, 2, None),
        (2, 3, None),
        (3, 4, None),
        (4, 5, "aprobado"),
        (5, 6, None),
        (4, 4, "fallido"),
    ],
    ids=[
        "recepción a lavado",
        "lavado a empaque",
        "empaque a esterilización",
        "esterilización aprobada a almacén",
        "almacén a entrega",
        "reesterilización tras lote fallido",
    ],
)
def test_transiciones_validas(actual, destino, resultado):
    validar_transicion(actual, destino, resultado)  # no debe lanzar nada


@pytest.mark.parametrize(
    "actual, destino, resultado, fragmento",
    [
        (1, 3, None, "etapa siguiente"),
        (1, 1, None, "etapa siguiente"),
        (2, 1, None, "etapa siguiente"),
        (3, 5, None, "etapa siguiente"),
        (5, 5, None, "etapa siguiente"),
        (6, 7, None, "no existe"),
        (4, 5, None, "en curso"),
        (4, 4, None, "en curso"),
        (4, 5, "fallido", "fallido"),
        (4, 4, "aprobado", "fallido"),
        (4, 6, "aprobado", "Desde Esterilización"),
        (4, 3, "fallido", "Desde Esterilización"),
    ],
    ids=[
        "salta lavado",
        "repite recepción",
        "retrocede",
        "salta esterilización",
        "repite almacén",
        "después de entrega",
        "a almacén con lote en curso",
        "reesterilizar con lote en curso",
        "a almacén con lote fallido",
        "reesterilizar con lote aprobado",
        "salta almacén",
        "vuelve a empaque tras fallo",
    ],
)
def test_transiciones_invalidas(actual, destino, resultado, fragmento):
    with pytest.raises(ErrorDeFlujo, match=fragmento):
        validar_transicion(actual, destino, resultado)
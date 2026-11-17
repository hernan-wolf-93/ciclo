import pytest

from app.services.numeracion_lote import siguiente_numero


@pytest.mark.parametrize(
    "ultimo, esperado",
    [(None, 1), (1, 2), (500, 501), (998, 999), (999, 1)],
)
def test_siguiente_numero(ultimo, esperado):
    assert siguiente_numero(ultimo) == esperado


@pytest.mark.parametrize("ultimo", [0, -1, 1000])
def test_numero_fuera_de_rango_se_rechaza(ultimo):
    """La base ya lo impide (CHECK 1..999): acá se falla fuerte y no se corrige en silencio."""
    with pytest.raises(ValueError):
        siguiente_numero(ultimo)
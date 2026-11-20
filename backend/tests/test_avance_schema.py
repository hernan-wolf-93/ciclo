"""Validación del pedido de avance (sin base de datos)."""

import pytest
from pydantic import ValidationError

from app.schemas.avance import AvanceIn

LINEA = {"material_id": 1, "cantidad": 1}


def _datos(**cambios):
    base = {"etapa_orden": 2, "items": [LINEA]}
    base.update(cambios)
    return base


def test_pedido_valido():
    assert AvanceIn(**_datos()).solo_desinfeccion is False


@pytest.mark.parametrize("etapa", [1, 4])
def test_solo_se_admiten_lavado_y_empaque(etapa):
    with pytest.raises(ValidationError):
        AvanceIn(**_datos(etapa_orden=etapa))


def test_items_vacios_se_rechazan():
    with pytest.raises(ValidationError):
        AvanceIn(**_datos(items=[]))


def test_cantidad_cero_se_rechaza():
    with pytest.raises(ValidationError):
        AvanceIn(**_datos(items=[{"material_id": 1, "cantidad": 0}]))


def test_material_repetido_se_rechaza():
    with pytest.raises(ValidationError, match="repetirse"):
        AvanceIn(**_datos(items=[LINEA, LINEA]))


@pytest.mark.parametrize("observacion", [None, "   "])
def test_excepcion_sin_observacion_se_rechaza(observacion):
    with pytest.raises(ValidationError, match="obligatoria"):
        AvanceIn(**_datos(solo_desinfeccion=True, observacion=observacion))


def test_excepcion_solo_en_lavado():
    with pytest.raises(ValidationError, match="Solo el lavado"):
        AvanceIn(**_datos(etapa_orden=3, solo_desinfeccion=True, observacion="prueba"))


def test_observacion_en_blanco_se_guarda_como_nula():
    assert AvanceIn(**_datos(observacion="   ")).observacion is None
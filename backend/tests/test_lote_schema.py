"""Validación del pedido de crear un lote (sin base de datos)."""

import pytest
from pydantic import ValidationError

from app.schemas.esterilizacion import LoteIn

LINEA = {"servicio_id": 1, "material_id": 1, "cantidad": 1}


def _datos(**cambios):
    base = {"equipo_id": 1, "programa_id": 1, "numero": 1, "lineas": [LINEA]}
    base.update(cambios)
    return base


def test_pedido_valido():
    assert LoteIn(**_datos()).numero == 1


@pytest.mark.parametrize("numero", [0, 1000])
def test_numero_fuera_de_rango_se_rechaza(numero):
    with pytest.raises(ValidationError):
        LoteIn(**_datos(numero=numero))


def test_lineas_vacias_se_rechazan():
    with pytest.raises(ValidationError):
        LoteIn(**_datos(lineas=[]))


@pytest.mark.parametrize("cantidad", [0, 501])
def test_cantidad_fuera_de_rango_se_rechaza(cantidad):
    with pytest.raises(ValidationError):
        LoteIn(**_datos(lineas=[{**LINEA, "cantidad": cantidad}]))


def test_linea_repetida_se_rechaza():
    with pytest.raises(ValidationError, match="repetirse"):
        LoteIn(**_datos(lineas=[LINEA, LINEA]))


def test_mismo_material_de_distinto_servicio_se_admite():
    datos = LoteIn(**_datos(lineas=[LINEA, {**LINEA, "servicio_id": 2}]))
    assert len(datos.lineas) == 2
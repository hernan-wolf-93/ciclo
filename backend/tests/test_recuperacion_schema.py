"""Pedido de restablecimiento de contraseña (sin base de datos)."""

import pytest
from pydantic import ValidationError

from app.schemas.recuperacion import RecuperarContrasenaIn


def _datos(**cambios):
    base = {"numero_operador": "T-0001", "codigo": "ABCD2345", "contrasena_nueva": "clave-nueva-1"}
    base.update(cambios)
    return base


def test_el_codigo_se_normaliza():
    assert RecuperarContrasenaIn(**_datos(codigo="  abcd2345 ")).codigo == "ABCD2345"


def test_contrasena_corta_se_rechaza():
    with pytest.raises(ValidationError):
        RecuperarContrasenaIn(**_datos(contrasena_nueva="corta"))


def test_contrasena_demasiado_larga_se_rechaza():
    with pytest.raises(ValidationError):
        RecuperarContrasenaIn(**_datos(contrasena_nueva="x" * 129))


def test_codigo_vacio_se_rechaza():
    with pytest.raises(ValidationError):
        RecuperarContrasenaIn(**_datos(codigo=""))
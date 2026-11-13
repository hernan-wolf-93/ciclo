import pytest
from pydantic import ValidationError

from app.schemas.recepcion import RecepcionIn


def _datos(**cambios):
    base = {"servicio_id": 1, "items": [{"material_id": 3, "cantidad": 2}], "completo": True}
    base.update(cambios)
    return base


def test_recepcion_minima_valida():
    datos = RecepcionIn(**_datos())
    assert datos.servicio_avisado is False
    assert datos.urgente is False
    assert datos.observacion is None


def test_observacion_en_blanco_se_guarda_como_nula():
    assert RecepcionIn(**_datos(observacion="   ")).observacion is None


def test_incompleta_valida():
    datos = RecepcionIn(**_datos(completo=False, servicio_avisado=True, observacion="  Falta una pinza "))
    assert datos.observacion == "Falta una pinza"


@pytest.mark.parametrize(
    "cambios",
    [
        {"items": []},
        {"items": [{"material_id": 3, "cantidad": 0}]},
        {"items": [{"material_id": 3, "cantidad": 501}]},
        {"items": [{"material_id": 3, "cantidad": 1}, {"material_id": 3, "cantidad": 2}]},
        {"completo": False, "servicio_avisado": True},
        {"completo": False, "servicio_avisado": True, "observacion": "   "},
        {"completo": False, "observacion": "Falta una pinza"},
    ],
    ids=[
        "items vacío",
        "cantidad 0",
        "cantidad 501",
        "material repetido",
        "incompleta sin observación",
        "incompleta con observación en blanco",
        "incompleta sin aviso al servicio",
    ],
)
def test_rechaza_datos_invalidos(cambios):
    with pytest.raises(ValidationError):
        RecepcionIn(**_datos(**cambios))
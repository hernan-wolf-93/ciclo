"""GET /avances/pendientes: material que espera para pasar a Lavado (2) o a Empaque (3)."""

import pytest
from sqlalchemy import select

from app.models.catalogos import Servicio

CLAVES = {"servicio_id", "servicio", "material_id", "material", "cantidad"}


def _recepcion(cliente, servicio_id, lineas):
    cuerpo = {
        "servicio_id": servicio_id,
        "items": [{"material_id": m, "cantidad": c} for m, c in lineas],
        "completo": True,
    }
    respuesta = cliente.post("/recepciones", json=cuerpo)
    assert respuesta.status_code == 201, respuesta.text


def _pendientes(cliente, etapa_orden, servicio_ids):
    """{(servicio_id, material_id): cantidad}, solo de los servicios de la prueba."""
    respuesta = cliente.get("/avances/pendientes", params={"etapa_orden": etapa_orden})
    assert respuesta.status_code == 200, respuesta.text
    return {
        (f["servicio_id"], f["material_id"]): f["cantidad"]
        for f in respuesta.json()
        if f["servicio_id"] in servicio_ids
    }


@pytest.fixture
def dos_servicios(db_pg):
    return list(
        db_pg.scalars(select(Servicio).where(Servicio.activo.is_(True)).order_by(Servicio.id).limit(2))
    )


def test_sin_token_responde_401(cliente_pg):
    assert cliente_pg.get("/avances/pendientes", params={"etapa_orden": 2}).status_code == 401


@pytest.mark.parametrize("params", [{}, {"etapa_orden": 1}, {"etapa_orden": 4}])
def test_etapa_invalida_o_ausente_responde_422(con_sesion, params):
    assert con_sesion.get("/avances/pendientes", params=params).status_code == 422


def test_cuenta_por_servicio_y_material(con_sesion, dos_servicios, materiales):
    a, b = dos_servicios
    m1, m2 = materiales
    _recepcion(con_sesion, a.id, [(m1.id, 3), (m2.id, 1)])
    _recepcion(con_sesion, b.id, [(m1.id, 2)])

    respuesta = con_sesion.get("/avances/pendientes", params={"etapa_orden": 2})

    assert respuesta.status_code == 200
    assert all(set(f) == CLAVES for f in respuesta.json())
    assert _pendientes(con_sesion, 2, {a.id, b.id}) == {
        (a.id, m1.id): 3,
        (a.id, m2.id): 1,
        (b.id, m1.id): 2,
    }
    # Lo que está en Recepción todavía no espera para Empaque
    assert _pendientes(con_sesion, 3, {a.id, b.id}) == {}


def test_un_avance_mueve_los_mas_antiguos_a_la_etapa_siguiente(con_sesion, dos_servicios, materiales):
    a, b = dos_servicios
    m1, _ = materiales
    _recepcion(con_sesion, a.id, [(m1.id, 3)])  # la más antigua
    _recepcion(con_sesion, b.id, [(m1.id, 2)])
    avance = {"etapa_orden": 2, "items": [{"material_id": m1.id, "cantidad": 2}]}
    assert con_sesion.post("/avances", json=avance).status_code == 201

    # El avance toma los más antiguos del material, sin mirar el servicio
    assert _pendientes(con_sesion, 2, {a.id, b.id}) == {(a.id, m1.id): 1, (b.id, m1.id): 2}
    assert _pendientes(con_sesion, 3, {a.id, b.id}) == {(a.id, m1.id): 2}
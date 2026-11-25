"""GET /equipos/{id}/pendientes: material que puede cargar un equipo."""

import pytest
from sqlalchemy import select

from app.models.catalogos import Servicio

CLAVES = {"servicio_id", "servicio", "material_id", "material", "cantidad"}


def _url(equipo):
    return f"/equipos/{equipo.id}/pendientes"


def _pendientes(cliente, equipo, servicio_ids):
    """{(servicio_id, material_id): cantidad}, solo de los servicios de la prueba."""
    respuesta = cliente.get(_url(equipo))
    assert respuesta.status_code == 200, respuesta.text
    assert all(set(f) == CLAVES for f in respuesta.json())
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
    assert cliente_pg.get("/equipos/1/pendientes").status_code == 401


def test_equipo_inexistente_responde_404(con_sesion):
    respuesta = con_sesion.get("/equipos/999999/pendientes")

    assert respuesta.status_code == 404
    assert respuesta.json()["detail"] == "No existe el equipo 999999"


def test_cuenta_lo_empacado_con_el_metodo_del_equipo(
    con_sesion, empacar, equipo_de, servicio, materiales, metodos
):
    m1, m2 = materiales
    empacar(servicio, m1, metodos[0], 3)
    empacar(servicio, m2, metodos[1], 1)

    assert _pendientes(con_sesion, equipo_de(metodos[0]), {servicio.id}) == {(servicio.id, m1.id): 3}
    assert _pendientes(con_sesion, equipo_de(metodos[1]), {servicio.id}) == {(servicio.id, m2.id): 1}


def test_separa_por_servicio_de_origen(con_sesion, empacar, equipo_de, dos_servicios, materiales, metodos):
    a, b = dos_servicios
    m1, _ = materiales
    empacar(a, m1, metodos[0], 3)
    empacar(b, m1, metodos[0], 2)

    assert _pendientes(con_sesion, equipo_de(metodos[0]), {a.id, b.id}) == {
        (a.id, m1.id): 3,
        (b.id, m1.id): 2,
    }


def test_no_incluye_lo_que_todavia_no_esta_empacado(
    con_sesion, equipo_de, servicio, materiales, metodos
):
    m1, _ = materiales
    recepcion = {
        "servicio_id": servicio.id,
        "items": [{"material_id": m1.id, "cantidad": 3}],
        "completo": True,
    }
    assert con_sesion.post("/recepciones", json=recepcion).status_code == 201
    lavado = {"etapa_orden": 2, "items": [{"material_id": m1.id, "cantidad": 2}]}
    assert con_sesion.post("/avances", json=lavado).status_code == 201
    empaque = {
        "etapa_orden": 3,
        "items": [{"material_id": m1.id, "cantidad": 1, "metodo_id": metodos[0].id}],
    }
    assert con_sesion.post("/avances", json=empaque).status_code == 201

    # Uno empacado, dos en Lavado y ninguno en Recepción: solo cuenta el empacado
    assert _pendientes(con_sesion, equipo_de(metodos[0]), {servicio.id}) == {(servicio.id, m1.id): 1}


def test_un_lote_fallido_devuelve_sus_items_a_la_lista(
    con_sesion, empacar, cargar_lote, equipo_de, servicio, materiales, metodos
):
    ids = empacar(servicio, materiales[0], metodos[0], 2)
    equipo = equipo_de(metodos[0])
    cargar_lote(equipo, ids, resultado="fallido")

    assert _pendientes(con_sesion, equipo, {servicio.id}) == {(servicio.id, materiales[0].id): 2}


@pytest.mark.parametrize("resultado", ["aprobado", None], ids=["aprobado", "en curso"])
def test_un_lote_aprobado_o_en_curso_no_aparece(
    con_sesion, empacar, cargar_lote, equipo_de, servicio, materiales, metodos, resultado
):
    ids = empacar(servicio, materiales[0], metodos[0], 2)
    equipo = equipo_de(metodos[0])
    cargar_lote(equipo, ids, resultado=resultado)

    assert _pendientes(con_sesion, equipo, {servicio.id}) == {}
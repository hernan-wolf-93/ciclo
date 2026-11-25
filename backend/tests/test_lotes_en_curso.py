"""GET /lotes?en_curso=true: solo los lotes que todavía no se cerraron (fin sin definir)."""

from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.models.catalogos import Equipo, MetodoEsterilizacion


@pytest.fixture
def estufa(db_pg):
    metodo = db_pg.scalar(
        select(MetodoEsterilizacion).where(MetodoEsterilizacion.nombre == "Calor seco")
    )
    equipo = db_pg.scalar(
        select(Equipo)
        .where(Equipo.metodo_id == metodo.id, Equipo.activo.is_(True))
        .order_by(Equipo.id)
        .limit(1)
    )
    return SimpleNamespace(metodo=metodo, equipo=equipo)


@pytest.fixture
def lotes(cargar_lote, empacar, estufa, servicio, materiales):
    """Un lote en curso, uno aprobado y uno fallido, con números 1, 2 y 3."""

    def _lote(resultado, numero):
        ids = empacar(servicio, materiales[0], estufa.metodo, 1)
        return cargar_lote(estufa.equipo, ids, resultado=resultado, numero=numero)

    return SimpleNamespace(
        en_curso=_lote(None, 1),
        aprobado=_lote("aprobado", 2),
        fallido=_lote("fallido", 3),
    )


def _ids(respuesta):
    return {lote["id"] for lote in respuesta.json()}


def test_sin_filtro_devuelve_los_lotes_cerrados_y_en_curso(con_sesion, lotes):
    r = con_sesion.get("/lotes")

    assert r.status_code == 200
    assert {lotes.en_curso.id, lotes.aprobado.id, lotes.fallido.id} <= _ids(r)


def test_en_curso_devuelve_solo_los_lotes_sin_cerrar(con_sesion, lotes):
    r = con_sesion.get("/lotes", params={"en_curso": True})

    assert r.status_code == 200
    ids = _ids(r)
    assert lotes.en_curso.id in ids
    assert not ids & {lotes.aprobado.id, lotes.fallido.id}
    assert all(lote["fin"] is None for lote in r.json())


def test_en_curso_falso_equivale_a_no_filtrar(con_sesion, lotes):
    r = con_sesion.get("/lotes", params={"en_curso": False})

    assert r.status_code == 200
    assert {lotes.en_curso.id, lotes.aprobado.id, lotes.fallido.id} <= _ids(r)


def test_en_curso_se_combina_con_el_numero(con_sesion, lotes):
    del_uno = con_sesion.get("/lotes", params={"en_curso": True, "numero": 1})
    del_dos = con_sesion.get("/lotes", params={"en_curso": True, "numero": 2})

    assert lotes.en_curso.id in _ids(del_uno)
    assert lotes.aprobado.id not in _ids(del_dos)


def test_en_curso_con_un_valor_que_no_es_booleano_responde_422(con_sesion):
    r = con_sesion.get("/lotes", params={"en_curso": "quizas"})

    assert r.status_code == 422
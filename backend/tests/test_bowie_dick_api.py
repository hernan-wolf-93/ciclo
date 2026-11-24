"""Control Bowie-Dick: registro por equipo y consulta de si hay uno aprobado hoy."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select

from app.models import ControlBowieDick, Equipo, MetodoEsterilizacion

CLAVES = {"id", "equipo_id", "fecha_hora", "resultado", "observacion", "numero_ciclo"}


def _url(equipo_id):
    return f"/equipos/{equipo_id}/bowie-dick"


def _contar(db):
    return db.scalar(select(func.count()).select_from(ControlBowieDick))


def _equipos_de(db, metodo):
    return list(
        db.scalars(
            select(Equipo)
            .join(MetodoEsterilizacion, MetodoEsterilizacion.id == Equipo.metodo_id)
            .where(MetodoEsterilizacion.nombre == metodo, Equipo.activo.is_(True))
            .order_by(Equipo.id)
        )
    )


@pytest.fixture
def autoclaves(db_pg):
    return _equipos_de(db_pg, "Calor húmedo")


@pytest.fixture
def estufas(db_pg):
    return _equipos_de(db_pg, "Calor seco")


# --- Acceso ---------------------------------------------------------------

def test_registrar_sin_token_responde_401(cliente_pg, autoclaves):
    r = cliente_pg.post(_url(autoclaves[0].id), json={"resultado": "aprobado"})
    assert r.status_code == 401


def test_consultar_sin_token_responde_401(cliente_pg, autoclaves):
    assert cliente_pg.get(_url(autoclaves[0].id) + "/hoy").status_code == 401


# --- Registro -------------------------------------------------------------

def test_registra_un_control_aprobado(con_sesion, db_pg, operador, autoclaves):
    r = con_sesion.post(_url(autoclaves[0].id), json={"resultado": "aprobado", "numero_ciclo": "123"})

    assert r.status_code == 201
    cuerpo = r.json()
    assert set(cuerpo) == CLAVES
    assert (cuerpo["equipo_id"], cuerpo["resultado"], cuerpo["numero_ciclo"]) == (
        autoclaves[0].id,
        "aprobado",
        "123",
    )
    guardado = db_pg.get(ControlBowieDick, cuerpo["id"])
    assert guardado.operador_id == operador.id
    assert guardado.fecha_hora is not None


def test_el_operador_sale_del_token_y_no_del_cuerpo(con_sesion, db_pg, operador, autoclaves):
    cuerpo = {"resultado": "aprobado", "operador_id": 999999, "operador": "OTRO-9999"}

    r = con_sesion.post(_url(autoclaves[0].id), json=cuerpo)

    assert r.status_code == 201
    assert db_pg.get(ControlBowieDick, r.json()["id"]).operador_id == operador.id


def test_observacion_en_blanco_se_guarda_como_nula(con_sesion, db_pg, autoclaves):
    r = con_sesion.post(_url(autoclaves[0].id), json={"resultado": "aprobado", "observacion": "   "})

    assert r.status_code == 201
    assert r.json()["observacion"] is None


def test_fallido_con_observacion_responde_201(con_sesion, autoclaves):
    cuerpo = {"resultado": "fallido", "observacion": "Cambio de color incompleto"}

    r = con_sesion.post(_url(autoclaves[0].id), json=cuerpo)

    assert r.status_code == 201
    assert r.json()["resultado"] == "fallido"
    assert r.json()["observacion"] == "Cambio de color incompleto"


@pytest.mark.parametrize(
    "cuerpo",
    [
        {},
        {"resultado": "dudoso"},
        {"resultado": "fallido"},
        {"resultado": "fallido", "observacion": "   "},
        {"resultado": "aprobado", "numero_ciclo": "x" * 21},
    ],
    ids=["sin resultado", "resultado inválido", "fallido sin observación",
         "fallido con observación en blanco", "número de ciclo largo"],
)
def test_cuerpo_invalido_responde_422_y_no_guarda(con_sesion, db_pg, autoclaves, cuerpo):
    antes = _contar(db_pg)

    r = con_sesion.post(_url(autoclaves[0].id), json=cuerpo)

    assert r.status_code == 422
    assert _contar(db_pg) == antes


def test_registrar_en_un_equipo_inexistente_responde_404(con_sesion):
    r = con_sesion.post(_url(999999), json={"resultado": "aprobado"})

    assert r.status_code == 404
    assert r.json()["detail"] == "No existe el equipo 999999"


def test_equipo_que_no_es_autoclave_responde_422(con_sesion, db_pg, estufas):
    antes = _contar(db_pg)

    r = con_sesion.post(_url(estufas[0].id), json={"resultado": "aprobado"})

    assert r.status_code == 422
    assert "autoclave" in r.json()["detail"]
    assert _contar(db_pg) == antes


def test_equipo_dado_de_baja_responde_422(con_sesion, db_pg, autoclaves):
    autoclaves[0].activo = False
    db_pg.commit()

    r = con_sesion.post(_url(autoclaves[0].id), json={"resultado": "aprobado"})

    assert r.status_code == 422
    assert "baja" in r.json()["detail"]


# --- Consulta de hoy ------------------------------------------------------

def test_sin_controles_hoy_no_hay_aprobado(con_sesion, autoclaves):
    r = con_sesion.get(_url(autoclaves[0].id) + "/hoy")

    assert r.status_code == 200
    assert r.json() == {"equipo_id": autoclaves[0].id, "aprobado_hoy": False}


def test_un_control_aprobado_de_hoy_habilita(con_sesion, autoclaves):
    con_sesion.post(_url(autoclaves[0].id), json={"resultado": "aprobado"})

    assert con_sesion.get(_url(autoclaves[0].id) + "/hoy").json()["aprobado_hoy"] is True


def test_cuenta_el_ultimo_control_de_hoy(con_sesion, autoclaves):
    con_sesion.post(_url(autoclaves[0].id), json={"resultado": "aprobado"})
    con_sesion.post(_url(autoclaves[0].id), json={"resultado": "fallido", "observacion": "Repetir"})

    assert con_sesion.get(_url(autoclaves[0].id) + "/hoy").json()["aprobado_hoy"] is False


def test_un_control_aprobado_de_hace_dos_dias_no_cuenta(con_sesion, db_pg, operador, autoclaves):
    db_pg.add(
        ControlBowieDick(
            equipo_id=autoclaves[0].id,
            operador_id=operador.id,
            resultado="aprobado",
            fecha_hora=datetime.now(timezone.utc) - timedelta(days=2),
        )
    )
    db_pg.commit()

    assert con_sesion.get(_url(autoclaves[0].id) + "/hoy").json()["aprobado_hoy"] is False


def test_el_control_es_por_equipo(con_sesion, autoclaves):
    assert len(autoclaves) >= 2
    a, b = autoclaves[0], autoclaves[1]
    con_sesion.post(_url(a.id), json={"resultado": "aprobado"})

    assert con_sesion.get(_url(a.id) + "/hoy").json()["aprobado_hoy"] is True
    assert con_sesion.get(_url(b.id) + "/hoy").json()["aprobado_hoy"] is False


def test_consultar_un_equipo_inexistente_responde_404(con_sesion):
    r = con_sesion.get(_url(999999) + "/hoy")

    assert r.status_code == 404
    assert r.json()["detail"] == "No existe el equipo 999999"
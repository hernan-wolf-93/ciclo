"""Avance de lavado y empaque: API contra PostgreSQL (ciclo_test)."""

import pytest
from sqlalchemy import func, select

from app.core.seguridad import crear_token
from app.models import Etapa, EventoItem
from app.services import avance as servicio_avance
from app.services.flujo import ErrorDeFlujo


def _auth(operador):
    return {"Authorization": f"Bearer {crear_token(operador.id)}"}


def _recibir(cliente, operador, servicio, material, cantidad):
    r = cliente.post(
        "/recepciones",
        json={
            "servicio_id": servicio.id,
            "items": [{"material_id": material.id, "cantidad": cantidad}],
            "completo": True,
        },
        headers=_auth(operador),
    )
    assert r.status_code == 201


def _cuerpo(materiales, **cambios):
    base = {
        "etapa_orden": 2,
        "items": [{"material_id": materiales[0].id, "cantidad": 2}],
    }
    base.update(cambios)
    return base


def _contar(db):
    return db.scalar(select(func.count()).select_from(EventoItem))


def _eventos_de_etapa(db, orden):
    return list(
        db.scalars(
            select(EventoItem)
            .join(Etapa, Etapa.id == EventoItem.etapa_id)
            .where(Etapa.orden == orden)
            .order_by(EventoItem.id)
        )
    )


def test_sin_token_responde_401(cliente_pg, materiales):
    r = cliente_pg.post("/avances", json=_cuerpo(materiales))
    assert r.status_code == 401


def test_token_invalido_responde_401(cliente_pg, materiales):
    r = cliente_pg.post(
        "/avances", json=_cuerpo(materiales), headers={"Authorization": "Bearer token-falso"}
    )
    assert r.status_code == 401


def test_operador_dado_de_baja_responde_401(cliente_pg, db_pg, operador, materiales):
    headers = _auth(operador)
    operador.activo = False
    db_pg.commit()
    r = cliente_pg.post("/avances", json=_cuerpo(materiales), headers=headers)
    assert r.status_code == 401


def test_avanza_a_lavado_y_responde_201(cliente_pg, db_pg, operador, servicio, materiales):
    _recibir(cliente_pg, operador, servicio, materiales[0], 2)
    r = cliente_pg.post("/avances", json=_cuerpo(materiales), headers=_auth(operador))
    assert r.status_code == 201
    assert r.json() == {"etapa_orden": 2, "total_items": 2, "solo_desinfeccion": False}
    eventos = _eventos_de_etapa(db_pg, 2)
    assert len(eventos) == 2
    assert {e.operador_id for e in eventos} == {operador.id}


def test_circuito_lavado_y_luego_empaque(cliente_pg, db_pg, operador, servicio, materiales):
    _recibir(cliente_pg, operador, servicio, materiales[0], 2)
    headers = _auth(operador)
    assert cliente_pg.post("/avances", json=_cuerpo(materiales), headers=headers).status_code == 201
    r = cliente_pg.post("/avances", json=_cuerpo(materiales, etapa_orden=3), headers=headers)
    assert r.status_code == 201
    assert r.json()["etapa_orden"] == 3
    assert len(_eventos_de_etapa(db_pg, 3)) == 2


def test_el_operador_sale_del_token_y_no_del_cuerpo(cliente_pg, db_pg, operador, servicio, materiales):
    _recibir(cliente_pg, operador, servicio, materiales[0], 2)
    cuerpo = _cuerpo(materiales, operador="OTRO-9999", operador_id=999999)
    r = cliente_pg.post("/avances", json=cuerpo, headers=_auth(operador))
    assert r.status_code == 201
    assert {e.operador_id for e in _eventos_de_etapa(db_pg, 2)} == {operador.id}


@pytest.mark.parametrize(
    "cambios",
    [
        {"etapa_orden": 4},
        {"items": []},
        {"solo_desinfeccion": True},
        {"etapa_orden": 3, "solo_desinfeccion": True, "observacion": "prueba"},
    ],
    ids=["etapa inválida", "items vacío", "excepción sin observación", "excepción en empaque"],
)
def test_cuerpo_invalido_responde_422_y_no_guarda(cliente_pg, db_pg, operador, servicio, materiales, cambios):
    _recibir(cliente_pg, operador, servicio, materiales[0], 2)
    antes = _contar(db_pg)
    r = cliente_pg.post("/avances", json=_cuerpo(materiales, **cambios), headers=_auth(operador))
    assert r.status_code == 422
    assert _contar(db_pg) == antes


def test_sin_items_esperando_responde_422_con_motivo(cliente_pg, db_pg, operador, materiales):
    antes = _contar(db_pg)
    r = cliente_pg.post("/avances", json=_cuerpo(materiales), headers=_auth(operador))
    assert r.status_code == 422
    assert "esperando" in r.json()["detail"]
    assert _contar(db_pg) == antes


def test_solo_desinfeccion_con_observacion_responde_201(cliente_pg, db_pg, operador, servicio, materiales):
    _recibir(cliente_pg, operador, servicio, materiales[0], 1)
    cuerpo = _cuerpo(
        materiales,
        items=[{"material_id": materiales[0].id, "cantidad": 1}],
        solo_desinfeccion=True,
        observacion="Ortopedia: llegó lavada",
    )
    r = cliente_pg.post("/avances", json=cuerpo, headers=_auth(operador))
    assert r.status_code == 201
    assert r.json()["solo_desinfeccion"] is True
    evento = _eventos_de_etapa(db_pg, 2)[0]
    assert evento.solo_desinfeccion is True
    assert evento.observacion == "Ortopedia: llegó lavada"


def test_error_de_flujo_responde_422_con_motivo(cliente_pg, db_pg, operador, servicio, materiales, monkeypatch):
    _recibir(cliente_pg, operador, servicio, materiales[0], 2)

    def _rechaza(db, item_ids, orden_destino):
        raise ErrorDeFlujo("Ítem 1: regla de flujo incumplida")

    monkeypatch.setattr(servicio_avance, "validar_avance_varios", _rechaza)
    antes = _contar(db_pg)
    r = cliente_pg.post("/avances", json=_cuerpo(materiales), headers=_auth(operador))
    assert r.status_code == 422
    assert "regla de flujo" in r.json()["detail"]
    assert _contar(db_pg) == antes
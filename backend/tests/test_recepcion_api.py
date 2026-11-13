import pytest
from sqlalchemy import func, select

from app.core.seguridad import crear_token
from app.models import EventoItem, Item, Recepcion


def _auth(operador):
    return {"Authorization": f"Bearer {crear_token(operador.id)}"}


def _cuerpo(servicio, materiales, **cambios):
    base = {
        "servicio_id": servicio.id,
        "items": [{"material_id": materiales[0].id, "cantidad": 2}],
        "completo": True,
    }
    base.update(cambios)
    return base


def _contar(db, modelo):
    return db.scalar(select(func.count()).select_from(modelo))


def test_sin_token_responde_401(cliente_pg, servicio, materiales):
    r = cliente_pg.post("/recepciones", json=_cuerpo(servicio, materiales))
    assert r.status_code == 401


def test_token_invalido_responde_401(cliente_pg, servicio, materiales):
    r = cliente_pg.post(
        "/recepciones",
        json=_cuerpo(servicio, materiales),
        headers={"Authorization": "Bearer token-falso"},
    )
    assert r.status_code == 401


def test_operador_dado_de_baja_responde_401(cliente_pg, db_pg, operador, servicio, materiales):
    headers = _auth(operador)
    operador.activo = False
    db_pg.commit()
    r = cliente_pg.post("/recepciones", json=_cuerpo(servicio, materiales), headers=headers)
    assert r.status_code == 401


def test_registra_y_responde_201(cliente_pg, db_pg, operador, servicio, materiales):
    r = cliente_pg.post("/recepciones", json=_cuerpo(servicio, materiales), headers=_auth(operador))
    assert r.status_code == 201
    cuerpo = r.json()
    assert cuerpo["servicio_id"] == servicio.id
    assert cuerpo["total_items"] == 2
    assert cuerpo["fecha_hora"]

    items = list(db_pg.scalars(select(Item).where(Item.recepcion_id == cuerpo["id"])))
    assert len(items) == 2
    eventos = list(db_pg.scalars(select(EventoItem).where(EventoItem.item_id.in_([i.id for i in items]))))
    assert len(eventos) == 2
    assert {e.operador_id for e in eventos} == {operador.id}


def test_el_operador_sale_del_token_y_no_del_cuerpo(cliente_pg, db_pg, operador, servicio, materiales):
    cuerpo = _cuerpo(servicio, materiales, operador="OTRO-9999", operador_id=999999)
    r = cliente_pg.post("/recepciones", json=cuerpo, headers=_auth(operador))
    assert r.status_code == 201
    eventos = list(
        db_pg.scalars(
            select(EventoItem).join(Item, Item.id == EventoItem.item_id).where(Item.recepcion_id == r.json()["id"])
        )
    )
    assert {e.operador_id for e in eventos} == {operador.id}


@pytest.mark.parametrize(
    "cambios",
    [
        {"items": []},
        {"completo": False, "servicio_avisado": True},
        {"items": [{"material_id": 1, "cantidad": 1}, {"material_id": 1, "cantidad": 2}]},
    ],
    ids=["items vacío", "incompleta sin observación", "material repetido"],
)
def test_cuerpo_invalido_responde_422_y_no_guarda(cliente_pg, db_pg, operador, servicio, materiales, cambios):
    antes = _contar(db_pg, Recepcion)
    r = cliente_pg.post("/recepciones", json=_cuerpo(servicio, materiales, **cambios), headers=_auth(operador))
    assert r.status_code == 422
    assert _contar(db_pg, Recepcion) == antes


def test_servicio_inexistente_responde_422_con_motivo(cliente_pg, db_pg, operador, servicio, materiales):
    antes = _contar(db_pg, Recepcion)
    r = cliente_pg.post(
        "/recepciones",
        json=_cuerpo(servicio, materiales, servicio_id=999999),
        headers=_auth(operador),
    )
    assert r.status_code == 422
    assert "servicio de origen" in r.json()["detail"]
    assert _contar(db_pg, Recepcion) == antes


def test_material_inexistente_responde_422_con_motivo(cliente_pg, operador, servicio, materiales):
    r = cliente_pg.post(
        "/recepciones",
        json=_cuerpo(servicio, materiales, items=[{"material_id": 999999, "cantidad": 1}]),
        headers=_auth(operador),
    )
    assert r.status_code == 422
    assert "Materiales" in r.json()["detail"]
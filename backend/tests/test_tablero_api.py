"""Tablero de material en curso: API contra PostgreSQL (ciclo_test)."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.core.seguridad import crear_token
from app.models import Equipo, Etapa, EventoItem, Item, Lote, Programa, Recepcion, Servicio

INICIO = datetime(2026, 11, 20, 8, 0, tzinfo=timezone.utc)


def _auth(operador):
    return {"Authorization": f"Bearer {crear_token(operador.id)}"}


@pytest.fixture
def autoclave(db_pg):
    equipo = db_pg.scalar(select(Equipo).where(Equipo.nombre == "Autoclave 1"))
    programa = db_pg.scalar(select(Programa).where(Programa.metodo_id == equipo.metodo_id))
    return equipo, programa


def _servicio(db, nombre):
    return db.scalar(select(Servicio).where(Servicio.nombre == nombre))


def _evento(db, item, operador, orden, lote=None):
    etapa = db.scalar(select(Etapa).where(Etapa.orden == orden))
    db.add(EventoItem(item_id=item.id, etapa_id=etapa.id, operador_id=operador.id, lote_id=lote.id if lote else None))
    db.flush()


def _recepcion(db, operador, servicio, materiales_y_cantidades, urgente=False, fecha_hora=INICIO):
    """Recepción con un ítem por unidad y su evento de Recepción, como la crea el servicio real."""
    recepcion = Recepcion(servicio_id=servicio.id, completo=True, urgente=urgente, fecha_hora=fecha_hora)
    db.add(recepcion)
    db.flush()
    items = []
    for material, cantidad in materiales_y_cantidades:
        for _ in range(cantidad):
            item = Item(recepcion_id=recepcion.id, material_id=material.id)
            db.add(item)
            db.flush()
            _evento(db, item, operador, 1)
            items.append(item)
    return recepcion, items


def _avanzar(db, items, operador, hasta_orden, lote=None):
    """Lleva los ítems de Recepción hasta la etapa indicada (con lote en Esterilización)."""
    for item in items:
        for orden in range(2, hasta_orden + 1):
            _evento(db, item, operador, orden, lote if orden == 4 else None)


def _lote(db, operador, autoclave, numero, resultado=None):
    equipo, programa = autoclave
    lote = Lote(
        numero=numero,
        equipo_id=equipo.id,
        programa_id=programa.id,
        operador_id=operador.id,
        resultado=resultado,
        observacion="Indicador químico sin virar" if resultado == "fallido" else None,
    )
    db.add(lote)
    db.flush()
    return lote


def _get(cliente, operador, params=None):
    r = cliente.get("/tablero", params=params, headers=_auth(operador))
    assert r.status_code == 200, r.text
    return r.json()


# ---------------------------------------------------------------------------
# Autenticación y lista vacía
# ---------------------------------------------------------------------------


def test_sin_token_responde_401(cliente_pg):
    assert cliente_pg.get("/tablero").status_code == 401


def test_sin_recepciones_devuelve_lista_vacia(cliente_pg, operador):
    assert _get(cliente_pg, operador) == []


# ---------------------------------------------------------------------------
# Recorrido por etapas
# ---------------------------------------------------------------------------


def test_fila_cuenta_los_items_en_cada_etapa(cliente_pg, db_pg, operador, servicio, materiales):
    recepcion, items = _recepcion(db_pg, operador, servicio, [(materiales[0], 3), (materiales[1], 1)])
    _avanzar(db_pg, items[:2], operador, 3)  # dos unidades del primer material llegan a Empaque

    fila = _get(cliente_pg, operador)[0]
    assert fila["recepcion_id"] == recepcion.id
    assert fila["servicio"] == {"id": servicio.id, "nombre": servicio.nombre}
    assert fila["total_items"] == 4
    assert fila["por_etapa"] == {"1": 2, "2": 0, "3": 2, "4": 0, "5": 0, "6": 0}
    assert fila["lotes"] == []
    por_material = {(m["material_id"], m["etapa_orden"]): m["cantidad"] for m in fila["materiales"]}
    assert por_material == {(materiales[0].id, 3): 2, (materiales[0].id, 1): 1, (materiales[1].id, 1): 1}


def test_recepcion_entregada_completa_no_aparece(cliente_pg, db_pg, operador, autoclave, servicio, materiales):
    lote = _lote(db_pg, operador, autoclave, numero=1, resultado="aprobado")
    entregada, items = _recepcion(db_pg, operador, servicio, [(materiales[0], 2)])
    _avanzar(db_pg, items, operador, 6, lote)
    parcial, items_parcial = _recepcion(db_pg, operador, servicio, [(materiales[0], 2)])
    _avanzar(db_pg, items_parcial[:1], operador, 6, lote)  # una unidad entregada y otra en Recepción

    filas = _get(cliente_pg, operador)
    assert [f["recepcion_id"] for f in filas] == [parcial.id]
    assert filas[0]["por_etapa"]["6"] == 1 and filas[0]["por_etapa"]["1"] == 1


def test_urgentes_primero_y_despues_la_mas_antigua(cliente_pg, db_pg, operador, servicio, materiales):
    vieja, _ = _recepcion(db_pg, operador, servicio, [(materiales[0], 1)], fecha_hora=INICIO)
    nueva, _ = _recepcion(db_pg, operador, servicio, [(materiales[0], 1)], fecha_hora=INICIO + timedelta(hours=3))
    urgente_nueva, _ = _recepcion(
        db_pg, operador, servicio, [(materiales[0], 1)], urgente=True, fecha_hora=INICIO + timedelta(hours=5)
    )
    urgente_vieja, _ = _recepcion(
        db_pg, operador, servicio, [(materiales[0], 1)], urgente=True, fecha_hora=INICIO + timedelta(hours=1)
    )

    ids = [f["recepcion_id"] for f in _get(cliente_pg, operador)]
    assert ids == [urgente_vieja.id, urgente_nueva.id, vieja.id, nueva.id]


# ---------------------------------------------------------------------------
# Filtros
# ---------------------------------------------------------------------------


def test_filtro_urgentes(cliente_pg, db_pg, operador, servicio, materiales):
    _recepcion(db_pg, operador, servicio, [(materiales[0], 1)])
    urgente, _ = _recepcion(db_pg, operador, servicio, [(materiales[0], 1)], urgente=True)
    filas = _get(cliente_pg, operador, {"urgente": "true"})
    assert [f["recepcion_id"] for f in filas] == [urgente.id]
    assert filas[0]["urgente"] is True


def test_filtro_por_servicio_y_por_material(cliente_pg, db_pg, operador, materiales):
    quirofano, guardia = _servicio(db_pg, "Quirófano"), _servicio(db_pg, "Guardia")
    de_quirofano, _ = _recepcion(db_pg, operador, quirofano, [(materiales[0], 1)])
    de_guardia, _ = _recepcion(db_pg, operador, guardia, [(materiales[1], 1)])

    assert [f["recepcion_id"] for f in _get(cliente_pg, operador, {"servicio_id": guardia.id})] == [de_guardia.id]
    assert [f["recepcion_id"] for f in _get(cliente_pg, operador, {"material_id": materiales[0].id})] == [
        de_quirofano.id
    ]


# ---------------------------------------------------------------------------
# Lotes (desde Esterilización)
# ---------------------------------------------------------------------------


def test_desde_esterilizacion_muestra_el_lote(cliente_pg, db_pg, operador, autoclave, servicio, materiales):
    lote = _lote(db_pg, operador, autoclave, numero=12)
    _, items = _recepcion(db_pg, operador, servicio, [(materiales[0], 3)])
    _avanzar(db_pg, items[:2], operador, 4, lote)

    fila = _get(cliente_pg, operador)[0]
    assert fila["por_etapa"]["4"] == 2 and fila["por_etapa"]["1"] == 1
    assert fila["lotes"] == [{"id": lote.id, "numero": 12, "equipo": "Autoclave 1", "resultado": None}]


def test_reesterilizacion_muestra_solo_el_ultimo_lote(cliente_pg, db_pg, operador, autoclave, servicio, materiales):
    fallido = _lote(db_pg, operador, autoclave, numero=13, resultado="fallido")
    reemplazo = _lote(db_pg, operador, autoclave, numero=14)
    _, items = _recepcion(db_pg, operador, servicio, [(materiales[0], 1)])
    _avanzar(db_pg, items, operador, 4, fallido)
    _evento(db_pg, items[0], operador, 4, reemplazo)

    fila = _get(cliente_pg, operador)[0]
    assert [lote["numero"] for lote in fila["lotes"]] == [14]


def test_filtro_por_lote(cliente_pg, db_pg, operador, autoclave, servicio, materiales):
    lote = _lote(db_pg, operador, autoclave, numero=20)
    con_lote, items = _recepcion(db_pg, operador, servicio, [(materiales[0], 1)])
    _avanzar(db_pg, items, operador, 4, lote)
    _recepcion(db_pg, operador, servicio, [(materiales[0], 1)])  # sin lote: no debe aparecer

    filas = _get(cliente_pg, operador, {"lote_id": [lote.id]})
    assert [f["recepcion_id"] for f in filas] == [con_lote.id]
    assert _get(cliente_pg, operador, {"lote_id": [999999]}) == []


def test_no_se_filtra_el_hash_de_la_contrasena(cliente_pg, db_pg, operador, servicio, materiales):
    _recepcion(db_pg, operador, servicio, [(materiales[0], 1)])
    r = cliente_pg.get("/tablero", headers=_auth(operador))
    assert r.status_code == 200
    assert "contrasena" not in r.text
    assert operador.contrasena_hash not in r.text

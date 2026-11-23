from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.core.seguridad import crear_token
from app.models import Equipo, Etapa, EventoItem, Item, Lote, Programa, Recepcion, Servicio

INICIO = datetime(2026, 11, 10, 9, 0, tzinfo=timezone.utc)


def _auth(operador):
    return {"Authorization": f"Bearer {crear_token(operador.id)}"}


def _fecha(texto):
    return datetime.fromisoformat(texto)


@pytest.fixture
def autoclave(db_pg):
    equipo = db_pg.scalar(select(Equipo).where(Equipo.nombre == "Autoclave 1"))
    programa = db_pg.scalar(select(Programa).where(Programa.metodo_id == equipo.metodo_id))
    return equipo, programa


@pytest.fixture
def oxido(db_pg):
    """Equipo de óxido de etileno con un programa ficticio: la base todavía no tiene uno."""
    equipo = db_pg.scalar(select(Equipo).where(Equipo.nombre == "Óxido de etileno 1"))
    programa = Programa(nombre="Ciclo de prueba 56 °C", metodo_id=equipo.metodo_id)
    db_pg.add(programa)
    db_pg.flush()
    return equipo, programa


def _servicio(db, nombre):
    return db.scalar(select(Servicio).where(Servicio.nombre == nombre))


def _evento(db, item, operador, orden, lote=None):
    etapa = db.scalar(select(Etapa).where(Etapa.orden == orden))
    db.add(EventoItem(item_id=item.id, etapa_id=etapa.id, operador_id=operador.id, lote_id=lote.id if lote else None))
    db.flush()


def _item(db, operador, servicio, material):
    """Ítem recibido de un servicio, con su evento de Recepción."""
    recepcion = Recepcion(servicio_id=servicio.id, completo=True)
    db.add(recepcion)
    db.flush()
    item = Item(recepcion_id=recepcion.id, material_id=material.id)
    db.add(item)
    db.flush()
    _evento(db, item, operador, 1)
    return item


def _lote(db, operador, equipo_programa, numero, resultado=None, inicio=INICIO, fin=None):
    equipo, programa = equipo_programa
    lote = Lote(
        numero=numero,
        equipo_id=equipo.id,
        programa_id=programa.id,
        operador_id=operador.id,
        inicio=inicio,
        fin=fin,
        resultado=resultado,
        observacion="Indicador químico sin virar" if resultado == "fallido" else None,
    )
    db.add(lote)
    db.flush()
    return lote


def _esterilizar(db, item, operador, lote):
    """Lleva el ítem a Esterilización en ese lote, como lo deja el backend."""
    _evento(db, item, operador, 4, lote)
    item.metodo_id = db.get(Equipo, lote.equipo_id).metodo_id
    item.lote_id = lote.id
    db.flush()


def _hasta_esterilizacion(db, item, operador, lote):
    _evento(db, item, operador, 2)
    _evento(db, item, operador, 3)
    _esterilizar(db, item, operador, lote)


# ---------------------------------------------------------------------------
# Autenticación y validación
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("ruta", ["/lotes", "/lotes/1"])
def test_sin_token_responde_401(cliente_pg, ruta):
    assert cliente_pg.get(ruta).status_code == 401


def test_numero_fuera_de_rango_responde_422(cliente_pg, operador):
    assert cliente_pg.get("/lotes?numero=1000", headers=_auth(operador)).status_code == 422


# ---------------------------------------------------------------------------
# Lista
# ---------------------------------------------------------------------------


def test_lista_vacia(cliente_pg, operador):
    # ciclo_test solo tiene los datos de las migraciones: no hay lotes.
    r = cliente_pg.get("/lotes", headers=_auth(operador))
    assert r.status_code == 200
    assert r.json() == []


def test_busqueda_por_numero_repetido_devuelve_todos(cliente_pg, db_pg, operador, autoclave):
    viejo = _lote(db_pg, operador, autoclave, numero=12, inicio=INICIO - timedelta(days=150))
    nuevo = _lote(db_pg, operador, autoclave, numero=12, inicio=INICIO)
    otro = _lote(db_pg, operador, autoclave, numero=13, inicio=INICIO + timedelta(hours=2))

    r = cliente_pg.get("/lotes?numero=12", headers=_auth(operador))
    assert r.status_code == 200
    assert [lote["id"] for lote in r.json()] == [nuevo.id, viejo.id]  # del más nuevo al más viejo

    todos = cliente_pg.get("/lotes", headers=_auth(operador)).json()
    assert [lote["id"] for lote in todos] == [otro.id, nuevo.id, viejo.id]


def test_resumen_trae_equipo_con_metodo_y_resultado(cliente_pg, db_pg, operador, autoclave):
    _lote(db_pg, operador, autoclave, numero=5, resultado="aprobado", fin=INICIO + timedelta(hours=1))
    resumen = cliente_pg.get("/lotes", headers=_auth(operador)).json()[0]
    assert resumen["equipo"]["nombre"] == "Autoclave 1"
    assert resumen["equipo"]["metodo"]["nombre"] == "Calor húmedo"
    assert resumen["resultado"] == "aprobado"
    assert resumen["aireacion_fin_max"] is None  # el autoclave no lleva aireación


# ---------------------------------------------------------------------------
# Detalle
# ---------------------------------------------------------------------------


def test_detalle_inexistente_responde_404(cliente_pg, operador):
    r = cliente_pg.get("/lotes/999999", headers=_auth(operador))
    assert r.status_code == 404
    assert r.json()["detail"] == "El lote no existe"


def test_detalle_con_items_e_historial(cliente_pg, db_pg, operador, autoclave, servicio, materiales):
    lote = _lote(db_pg, operador, autoclave, numero=7, resultado="aprobado", fin=INICIO + timedelta(hours=1))
    item = _item(db_pg, operador, servicio, materiales[0])
    _hasta_esterilizacion(db_pg, item, operador, lote)
    _evento(db_pg, item, operador, 5)
    _item(db_pg, operador, servicio, materiales[1])  # recibido pero sin lote: no debe aparecer

    r = cliente_pg.get(f"/lotes/{lote.id}", headers=_auth(operador))
    assert r.status_code == 200
    detalle = r.json()

    assert detalle["numero"] == 7
    assert detalle["resultado"] == "aprobado"
    assert detalle["equipo"]["metodo"]["nombre"] == "Calor húmedo"
    assert detalle["operador"] == {"id": operador.id, "numero_operador": operador.numero_operador}
    # Desde la migración 0010: el lote de la prueba no tiene número de ciclo, y el
    # programa trae los parámetros reales cargados en la base
    assert detalle["numero_ciclo"] is None
    programa = db_pg.get(Programa, lote.programa_id)
    assert detalle["programa"]["temperatura_c"] == float(programa.temperatura_c)
    assert detalle["programa"]["tiempo_esterilizacion_min"] == programa.tiempo_esterilizacion_min
    assert detalle["programa"]["tiempo_desgasificacion_min"] is None
    assert detalle["reemplazado_por"] is None and detalle["reemplaza_a"] is None

    assert [i["id"] for i in detalle["items"]] == [item.id]
    item_out = detalle["items"][0]
    assert item_out["material"]["id"] == materiales[0].id
    assert item_out["servicio"] == {"id": servicio.id, "nombre": servicio.nombre, "dias_aireacion": servicio.dias_aireacion}
    assert [e["etapa"]["orden"] for e in item_out["eventos"]] == [1, 2, 3, 4, 5]
    # lote_id solo en el evento de Esterilización
    assert [e["lote_id"] for e in item_out["eventos"]] == [None, None, None, lote.id, None]
    assert {e["operador"]["numero_operador"] for e in item_out["eventos"]} == {operador.numero_operador}


def test_lote_fallido_y_su_reemplazo(cliente_pg, db_pg, operador, autoclave, servicio, materiales):
    fallido = _lote(db_pg, operador, autoclave, numero=13, resultado="fallido")
    reemplazo = _lote(db_pg, operador, autoclave, numero=14, resultado="aprobado", inicio=INICIO + timedelta(hours=2))
    item = _item(db_pg, operador, servicio, materiales[0])
    _hasta_esterilizacion(db_pg, item, operador, fallido)
    _esterilizar(db_pg, item, operador, reemplazo)  # item.lote_id pasa a ser el del reemplazo

    detalle_fallido = cliente_pg.get(f"/lotes/{fallido.id}", headers=_auth(operador)).json()
    # El lote fallido sigue mostrando su material, aunque item.lote_id ya sea otro
    assert [i["id"] for i in detalle_fallido["items"]] == [item.id]
    assert detalle_fallido["items"][0]["lote_id"] == reemplazo.id
    assert detalle_fallido["observacion"] == "Indicador químico sin virar"
    assert detalle_fallido["reemplazado_por"] == {"id": reemplazo.id, "numero": 14}
    assert detalle_fallido["reemplaza_a"] is None

    detalle_reemplazo = cliente_pg.get(f"/lotes/{reemplazo.id}", headers=_auth(operador)).json()
    assert [i["id"] for i in detalle_reemplazo["items"]] == [item.id]
    assert detalle_reemplazo["reemplaza_a"] == {"id": fallido.id, "numero": 13}
    assert detalle_reemplazo["reemplazado_por"] is None

    esterilizaciones = [e["lote_id"] for e in detalle_reemplazo["items"][0]["eventos"] if e["etapa"]["orden"] == 4]
    assert esterilizaciones == [fallido.id, reemplazo.id]


def test_aireacion_usa_el_servicio_con_mas_dias(cliente_pg, db_pg, operador, oxido, materiales):
    consultorios = _servicio(db_pg, "Consultorios Externos")
    pediatria = _servicio(db_pg, "Pediatría")
    pediatria.dias_aireacion = 7  # ya vale 7 desde la migración 0010; se fija igual para que la prueba no dependa de eso
    fin = INICIO + timedelta(hours=5)
    lote = _lote(db_pg, operador, oxido, numero=11, resultado="aprobado", fin=fin)
    for servicio_origen in (consultorios, pediatria):
        item = _item(db_pg, operador, servicio_origen, materiales[0])
        _hasta_esterilizacion(db_pg, item, operador, lote)

    resumen = cliente_pg.get("/lotes?numero=11", headers=_auth(operador)).json()[0]
    assert _fecha(resumen["aireacion_fin_max"]) == fin + timedelta(days=7)

    detalle = cliente_pg.get(f"/lotes/{lote.id}", headers=_auth(operador)).json()
    assert sorted(i["servicio"]["dias_aireacion"] for i in detalle["items"]) == [3, 7]


def test_aireacion_nula_si_el_lote_no_termino(cliente_pg, db_pg, operador, oxido, servicio, materiales):
    lote = _lote(db_pg, operador, oxido, numero=11)  # en curso: sin fin
    _hasta_esterilizacion(db_pg, _item(db_pg, operador, servicio, materiales[0]), operador, lote)
    resumen = cliente_pg.get("/lotes?numero=11", headers=_auth(operador)).json()[0]
    assert resumen["aireacion_fin_max"] is None


def test_no_se_filtra_el_hash_de_la_contrasena(cliente_pg, db_pg, operador, autoclave, servicio, materiales):
    lote = _lote(db_pg, operador, autoclave, numero=3)
    _hasta_esterilizacion(db_pg, _item(db_pg, operador, servicio, materiales[0]), operador, lote)

    for ruta in ("/lotes", f"/lotes/{lote.id}"):
        r = cliente_pg.get(ruta, headers=_auth(operador))
        assert r.status_code == 200
        assert "contrasena" not in r.text
        assert operador.contrasena_hash not in r.text

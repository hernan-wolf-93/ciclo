"""Avisos de material detenido: API contra PostgreSQL (ciclo_test), con "ahora" fijo."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.api.avisos import obtener_ahora
from app.core.seguridad import crear_token
from app.main import app
from app.models import Equipo, Etapa, EventoItem, Item, Lote, Programa, Recepcion, Servicio
from app.services import reglas_avisos as reglas

AHORA = datetime(2026, 11, 20, 15, 0, tzinfo=timezone.utc)  # fijo: no depende de la hora real


@pytest.fixture(autouse=True)
def ahora_fijo(cliente_pg):
    app.dependency_overrides[obtener_ahora] = lambda: AHORA
    yield
    app.dependency_overrides.pop(obtener_ahora, None)


def _auth(operador):
    return {"Authorization": f"Bearer {crear_token(operador.id)}"}


def _equipo(db, nombre, programa_nombre=None):
    equipo = db.scalar(select(Equipo).where(Equipo.nombre == nombre))
    programa = db.scalar(select(Programa).where(Programa.metodo_id == equipo.metodo_id))
    if programa is None:  # la base no tiene programas de óxido de etileno: uno ficticio
        programa = Programa(nombre=programa_nombre or "Programa de prueba", metodo_id=equipo.metodo_id)
        db.add(programa)
        db.flush()
    return equipo, programa


@pytest.fixture
def autoclave(db_pg):
    return _equipo(db_pg, "Autoclave 1")


@pytest.fixture
def oxido(db_pg):
    return _equipo(db_pg, "Óxido de etileno 1", "Ciclo de prueba 56 °C")


def _evento(db, item, operador, orden, fecha, lote=None):
    etapa = db.scalar(select(Etapa).where(Etapa.orden == orden))
    db.add(
        EventoItem(
            item_id=item.id, etapa_id=etapa.id, operador_id=operador.id,
            lote_id=lote.id if lote else None, fecha_hora=fecha,
        )
    )
    db.flush()


def _items(db, operador, servicio, material, cantidad, recibidos):
    """Ítems recibidos en una fecha dada, con su evento de Recepción."""
    recepcion = Recepcion(servicio_id=servicio.id, completo=True, fecha_hora=recibidos)
    db.add(recepcion)
    db.flush()
    items = []
    for _ in range(cantidad):
        item = Item(recepcion_id=recepcion.id, material_id=material.id)
        db.add(item)
        db.flush()
        _evento(db, item, operador, 1, recibidos)
        items.append(item)
    return items


def _a_etapa(db, items, operador, hasta, fecha, lote=None):
    """Avanza los ítems hasta la etapa indicada; el último evento queda con esa fecha."""
    for item in items:
        for orden in range(2, hasta + 1):
            _evento(db, item, operador, orden, fecha, lote if orden == 4 else None)


def _lote(db, operador, equipo_programa, numero, inicio, fin=None, resultado=None):
    equipo, programa = equipo_programa
    lote = Lote(
        numero=numero, equipo_id=equipo.id, programa_id=programa.id, operador_id=operador.id,
        inicio=inicio, fin=fin, resultado=resultado,
        observacion="Indicador químico sin virar" if resultado == "fallido" else None,
    )
    db.add(lote)
    db.flush()
    return lote


def _avisos(cliente, operador):
    r = cliente.get("/avisos", headers=_auth(operador))
    assert r.status_code == 200, r.text
    return r.json()


def test_sin_token_responde_401(cliente_pg):
    assert cliente_pg.get("/avisos").status_code == 401


def test_sin_material_no_hay_avisos(cliente_pg, operador):
    assert _avisos(cliente_pg, operador) == []


# ---------------------------------------------------------------------------
# Etapas 1 a 3: tiempo desde el último evento
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("orden", [1, 2, 3])
def test_etapas_1_a_3_avisan_solo_al_superar_su_umbral(cliente_pg, db_pg, operador, servicio, materiales, orden):
    umbral = reglas.UMBRAL_POR_ETAPA_MIN[orden]
    dentro = _items(db_pg, operador, servicio, materiales[0], 1, AHORA - timedelta(minutes=umbral - 1))
    fuera = _items(db_pg, operador, servicio, materiales[1], 2, AHORA - timedelta(minutes=umbral + 10))
    if orden > 1:
        _a_etapa(db_pg, dentro, operador, orden, AHORA - timedelta(minutes=umbral - 1))
        _a_etapa(db_pg, fuera, operador, orden, AHORA - timedelta(minutes=umbral + 10))

    avisos = _avisos(cliente_pg, operador)
    assert len(avisos) == 1  # el que está dentro de su tiempo no avisa
    aviso = avisos[0]
    assert aviso["tipo"] == "detenido"
    assert aviso["etapa_orden"] == orden
    assert aviso["material"]["id"] == materiales[1].id
    assert aviso["cantidad"] == 2  # agrupa los ítems de la misma recepción y material
    assert aviso["servicio"] == {"id": servicio.id, "nombre": servicio.nombre}
    assert aviso["minutos_transcurridos"] == umbral + 10
    assert aviso["umbral_minutos"] == umbral
    assert aviso["lote"] is None


def test_material_entregado_no_avisa(cliente_pg, db_pg, operador, autoclave, servicio, materiales):
    lote = _lote(db_pg, operador, autoclave, 1, AHORA - timedelta(days=3), AHORA - timedelta(days=3), "aprobado")
    items = _items(db_pg, operador, servicio, materiales[0], 1, AHORA - timedelta(days=4))
    _a_etapa(db_pg, items, operador, 6, AHORA - timedelta(days=2), lote)
    assert _avisos(cliente_pg, operador) == []


# ---------------------------------------------------------------------------
# Esterilización
# ---------------------------------------------------------------------------


def test_lote_sin_cerrar_respeta_el_tiempo_del_metodo(cliente_pg, db_pg, operador, autoclave, servicio, materiales):
    umbral = reglas.UMBRAL_ESTERILIZACION_POR_METODO_MIN["Calor húmedo"]
    a_tiempo = _lote(db_pg, operador, autoclave, 1, AHORA - timedelta(minutes=umbral - 5))
    demorado = _lote(db_pg, operador, autoclave, 2, AHORA - timedelta(minutes=umbral + 30))
    _a_etapa(db_pg, _items(db_pg, operador, servicio, materiales[0], 1, AHORA - timedelta(hours=5)), operador, 4,
             AHORA - timedelta(minutes=umbral - 5), a_tiempo)
    _a_etapa(db_pg, _items(db_pg, operador, servicio, materiales[1], 1, AHORA - timedelta(hours=5)), operador, 4,
             AHORA - timedelta(minutes=umbral + 30), demorado)

    avisos = _avisos(cliente_pg, operador)
    assert len(avisos) == 1
    assert avisos[0]["lote"] == {"id": demorado.id, "numero": 2, "equipo": "Autoclave 1"}
    assert avisos[0]["umbral_minutos"] == umbral
    assert "sin cerrarse" in avisos[0]["motivo"]


def test_oxido_de_etileno_tiene_un_umbral_mas_largo(cliente_pg, db_pg, operador, oxido, servicio, materiales):
    lote = _lote(db_pg, operador, oxido, 1, AHORA - timedelta(hours=10))  # 10 h: dentro de su tiempo
    _a_etapa(db_pg, _items(db_pg, operador, servicio, materiales[0], 1, AHORA - timedelta(hours=12)), operador, 4,
             AHORA - timedelta(hours=10), lote)
    assert _avisos(cliente_pg, operador) == []


def test_lote_fallido_sin_reesterilizar(cliente_pg, db_pg, operador, autoclave, servicio, materiales):
    lote = _lote(db_pg, operador, autoclave, 1, AHORA - timedelta(hours=3), AHORA - timedelta(hours=2), "fallido")
    _a_etapa(db_pg, _items(db_pg, operador, servicio, materiales[0], 1, AHORA - timedelta(hours=5)), operador, 4,
             AHORA - timedelta(hours=3), lote)
    aviso = _avisos(cliente_pg, operador)[0]
    assert "falta reesterilizar" in aviso["motivo"]
    assert aviso["minutos_transcurridos"] == 120


def test_lote_cerrado_sin_pasar_a_almacen_y_su_interruptor(cliente_pg, db_pg, operador, autoclave, servicio,
                                                           materiales, monkeypatch):
    lote = _lote(db_pg, operador, autoclave, 1, AHORA - timedelta(hours=3), AHORA - timedelta(hours=2), "aprobado")
    _a_etapa(db_pg, _items(db_pg, operador, servicio, materiales[0], 1, AHORA - timedelta(hours=5)), operador, 4,
             AHORA - timedelta(hours=3), lote)

    assert "falta pasar a Almacén" in _avisos(cliente_pg, operador)[0]["motivo"]
    monkeypatch.setattr(reglas, "AVISAR_FALTA_ALMACEN", False)  # si se omite la etapa de almacén
    assert _avisos(cliente_pg, operador) == []


def test_reesterilizado_solo_cuenta_el_ultimo_lote(cliente_pg, db_pg, operador, autoclave, servicio, materiales):
    fallido = _lote(db_pg, operador, autoclave, 1, AHORA - timedelta(hours=5), AHORA - timedelta(hours=4), "fallido")
    nuevo = _lote(db_pg, operador, autoclave, 2, AHORA - timedelta(minutes=20))  # en curso, a tiempo
    items = _items(db_pg, operador, servicio, materiales[0], 1, AHORA - timedelta(hours=6))
    _a_etapa(db_pg, items, operador, 4, AHORA - timedelta(hours=5), fallido)
    _evento(db_pg, items[0], operador, 4, AHORA - timedelta(minutes=20), nuevo)
    assert _avisos(cliente_pg, operador) == []


# ---------------------------------------------------------------------------
# Óxido de etileno: listo para retirar al cumplirse la aireación
# ---------------------------------------------------------------------------


def test_aireacion_en_curso_no_avisa_y_cumplida_avisa_listo(cliente_pg, db_pg, operador, oxido, materiales):
    consultorios = db_pg.scalar(select(Servicio).where(Servicio.nombre == "Consultorios Externos"))
    pediatria = db_pg.scalar(select(Servicio).where(Servicio.nombre == "Pediatría"))
    consultorios.dias_aireacion, pediatria.dias_aireacion = 3, 7
    fin = AHORA - timedelta(days=4)
    lote = _lote(db_pg, operador, oxido, 1, fin - timedelta(hours=15), fin, "aprobado")
    de_consultorios = _items(db_pg, operador, consultorios, materiales[0], 2, fin - timedelta(days=1))
    de_pediatria = _items(db_pg, operador, pediatria, materiales[1], 1, fin - timedelta(days=1))
    _a_etapa(db_pg, de_consultorios, operador, 5, fin - timedelta(hours=15), lote)  # ya en Almacén
    _a_etapa(db_pg, de_pediatria, operador, 4, fin - timedelta(hours=15), lote)

    avisos = _avisos(cliente_pg, operador)
    assert len(avisos) == 1  # Pediatría (7 días) todavía está en aireación
    aviso = avisos[0]
    assert aviso["tipo"] == "listo_para_retirar"
    assert aviso["servicio"]["nombre"] == "Consultorios Externos"
    assert aviso["cantidad"] == 2
    assert datetime.fromisoformat(aviso["desde"]) == fin + timedelta(days=3)
    assert aviso["minutos_transcurridos"] == 24 * 60
    assert aviso["umbral_minutos"] is None


def test_detenidos_primero_y_despues_listos(cliente_pg, db_pg, operador, oxido, servicio, materiales):
    fin = AHORA - timedelta(days=5)
    lote = _lote(db_pg, operador, oxido, 1, fin - timedelta(hours=15), fin, "aprobado")
    _a_etapa(db_pg, _items(db_pg, operador, servicio, materiales[0], 1, fin - timedelta(days=1)), operador, 5,
             fin, lote)
    _items(db_pg, operador, servicio, materiales[1], 1, AHORA - timedelta(hours=6))  # detenido en Recepción

    assert [a["tipo"] for a in _avisos(cliente_pg, operador)] == ["detenido", "listo_para_retirar"]


def test_no_se_filtra_el_hash_de_la_contrasena(cliente_pg, db_pg, operador, servicio, materiales):
    _items(db_pg, operador, servicio, materiales[0], 1, AHORA - timedelta(hours=6))
    r = cliente_pg.get("/avisos", headers=_auth(operador))
    assert r.status_code == 200 and r.json()
    assert "contrasena" not in r.text
    assert operador.contrasena_hash not in r.text

"""Cambios de la API por la migración 0010: umbral de esterilización desde el
programa, aireación con requiere_aireacion, filtro de centros externos en el tablero
y número de ciclo y parámetros reales en el historial. Contra ciclo_test."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.api.avisos import obtener_ahora
from app.core.seguridad import crear_token
from app.main import app
from app.models import Equipo, Etapa, EventoItem, Item, Lote, Programa, Recepcion, Servicio
from app.services import reglas_avisos as reglas

AHORA = datetime(2026, 11, 20, 15, 0, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def ahora_fijo(cliente_pg):
    app.dependency_overrides[obtener_ahora] = lambda: AHORA
    yield
    app.dependency_overrides.pop(obtener_ahora, None)


def _auth(operador):
    return {"Authorization": f"Bearer {crear_token(operador.id)}"}


def _programa(db, nombre):
    return db.scalar(select(Programa).where(Programa.nombre == nombre))


def _equipo(db, nombre):
    return db.scalar(select(Equipo).where(Equipo.nombre == nombre))


def _servicio(db, nombre):
    return db.scalar(select(Servicio).where(Servicio.nombre == nombre))


def _evento(db, item, operador, orden, fecha, lote=None):
    etapa = db.scalar(select(Etapa).where(Etapa.orden == orden))
    db.add(EventoItem(item_id=item.id, etapa_id=etapa.id, operador_id=operador.id, fecha_hora=fecha,
                      lote_id=lote.id if lote else None))
    db.flush()


def _item_en_lote(db, operador, servicio, material, lote, fecha):
    recepcion = Recepcion(servicio_id=servicio.id, completo=True, fecha_hora=fecha - timedelta(hours=3))
    db.add(recepcion)
    db.flush()
    item = Item(recepcion_id=recepcion.id, material_id=material.id)
    db.add(item)
    db.flush()
    for orden in (1, 2, 3):
        _evento(db, item, operador, orden, fecha - timedelta(hours=3))
    _evento(db, item, operador, 4, fecha, lote)
    return item


def _lote(db, operador, equipo, programa, inicio, fin=None, resultado=None, numero_ciclo=None):
    lote = Lote(numero=1, equipo_id=equipo.id, programa_id=programa.id, operador_id=operador.id,
                inicio=inicio, fin=fin, resultado=resultado, numero_ciclo=numero_ciclo)
    db.add(lote)
    db.flush()
    return lote


# ---------------------------------------------------------------------------
# Reglas puras del umbral
# ---------------------------------------------------------------------------


def test_duracion_del_programa_suma_sus_tiempos():
    assert reglas.duracion_programa(180, None, 720) == 900
    assert reglas.duracion_programa(None, None, None) is None


def test_umbral_desde_el_programa_con_margen_y_piso():
    margen = reglas.MARGEN_ESTERILIZACION_MIN
    assert reglas.umbral_esterilizacion_programa("Óxido de etileno", 900) == 900 + margen
    assert reglas.umbral_esterilizacion_programa("Calor húmedo", 80) == max(80 + margen, 90)
    assert reglas.umbral_esterilizacion_programa("Calor seco", None) == reglas.umbral_esterilizacion("Calor seco")


# ---------------------------------------------------------------------------
# Avisos con los tiempos del programa
# ---------------------------------------------------------------------------


def test_oxido_de_etileno_usa_esterilizacion_mas_desgasificacion(cliente_pg, db_pg, operador, servicio, materiales):
    umbral = 180 + 720 + reglas.MARGEN_ESTERILIZACION_MIN
    equipo, programa = _equipo(db_pg, "Óxido de etileno 1"), _programa(db_pg, "Ciclo caliente 55 °C")
    a_tiempo = _lote(db_pg, operador, equipo, programa, AHORA - timedelta(minutes=umbral - 10))
    _item_en_lote(db_pg, operador, servicio, materiales[0], a_tiempo, AHORA - timedelta(minutes=umbral - 10))
    r = cliente_pg.get("/avisos", headers=_auth(operador))
    assert r.json() == []  # 15 h 20 min: todavía dentro del tiempo del programa

    a_tiempo.inicio = AHORA - timedelta(minutes=umbral + 5)
    db_pg.flush()
    avisos = cliente_pg.get("/avisos", headers=_auth(operador)).json()
    assert [(a["tipo"], a["umbral_minutos"]) for a in avisos] == [("detenido", umbral)]


def test_priones_usa_su_tiempo_y_no_el_piso(cliente_pg, db_pg, operador, servicio, materiales):
    umbral = 60 + 20 + reglas.MARGEN_ESTERILIZACION_MIN  # 110 min, más que el piso de 90
    equipo, programa = _equipo(db_pg, "Autoclave 1"), _programa(db_pg, "Priones 134 °C")
    lote = _lote(db_pg, operador, equipo, programa, AHORA - timedelta(minutes=100))
    _item_en_lote(db_pg, operador, servicio, materiales[0], lote, AHORA - timedelta(minutes=100))
    assert cliente_pg.get("/avisos", headers=_auth(operador)).json() == []  # 100 min < 110

    lote.inicio = AHORA - timedelta(minutes=umbral + 1)
    db_pg.flush()
    aviso = cliente_pg.get("/avisos", headers=_auth(operador)).json()[0]
    assert aviso["umbral_minutos"] == umbral


def test_listo_para_retirar_usa_requiere_aireacion(cliente_pg, db_pg, operador, materiales):
    neonatologia = _servicio(db_pg, "Neonatología")  # 10 días según la 0010
    equipo, programa = _equipo(db_pg, "Óxido de etileno 1"), _programa(db_pg, "Ciclo caliente 55 °C")
    fin = AHORA - timedelta(days=11)
    lote = _lote(db_pg, operador, equipo, programa, fin - timedelta(hours=16), fin, "aprobado")
    _item_en_lote(db_pg, operador, neonatologia, materiales[0], lote, fin - timedelta(hours=16))
    aviso = cliente_pg.get("/avisos", headers=_auth(operador)).json()[0]
    assert aviso["tipo"] == "listo_para_retirar"
    assert datetime.fromisoformat(aviso["desde"]) == fin + timedelta(days=10)


# ---------------------------------------------------------------------------
# Tablero: filtro de centros externos
# ---------------------------------------------------------------------------


def test_tablero_filtra_centros_externos(cliente_pg, db_pg, operador, materiales):
    aguilares, quirofano = _servicio(db_pg, "Aguilares"), _servicio(db_pg, "Quirófano")
    recepciones = {}
    for servicio in (aguilares, quirofano):
        recepcion = Recepcion(servicio_id=servicio.id, completo=True, fecha_hora=AHORA)
        db_pg.add(recepcion)
        db_pg.flush()
        item = Item(recepcion_id=recepcion.id, material_id=materiales[0].id)
        db_pg.add(item)
        db_pg.flush()
        _evento(db_pg, item, operador, 1, AHORA)
        recepciones[servicio.nombre] = recepcion.id

    externos = cliente_pg.get("/tablero", params={"externo": "true"}, headers=_auth(operador)).json()
    internos = cliente_pg.get("/tablero", params={"externo": "false"}, headers=_auth(operador)).json()
    assert [f["recepcion_id"] for f in externos] == [recepciones["Aguilares"]]
    assert [f["recepcion_id"] for f in internos] == [recepciones["Quirófano"]]


# ---------------------------------------------------------------------------
# Historial: número de ciclo, parámetros reales y datos del método
# ---------------------------------------------------------------------------


def test_historial_devuelve_numero_de_ciclo_y_parametros(cliente_pg, db_pg, operador, servicio, materiales):
    equipo, programa = _equipo(db_pg, "Óxido de etileno 1"), _programa(db_pg, "Ciclo caliente 55 °C")
    lote = _lote(db_pg, operador, equipo, programa, AHORA - timedelta(hours=2), numero_ciclo="0087")
    _item_en_lote(db_pg, operador, servicio, materiales[0], lote, AHORA - timedelta(hours=2))

    detalle = cliente_pg.get(f"/lotes/{lote.id}", headers=_auth(operador)).json()
    assert detalle["numero_ciclo"] == "0087"
    assert {k: detalle["programa"][k] for k in ("temperatura_c", "tiempo_esterilizacion_min",
                                                 "tiempo_desgasificacion_min", "tiempo_secado_min")} == {
        "temperatura_c": 55.0, "tiempo_esterilizacion_min": 180,
        "tiempo_desgasificacion_min": 720, "tiempo_secado_min": None,
    }
    assert detalle["equipo"]["metodo"]["requiere_aireacion"] is True
    assert detalle["equipo"]["metodo"]["vencimiento_dias"] == 365

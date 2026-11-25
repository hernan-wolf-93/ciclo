"""POST /lotes/{id}/cierre: cierra la carga de un equipo con el resultado del ciclo."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy import func, select

from app.models import EventoItem, Item
from app.models.catalogos import Equipo, MetodoEsterilizacion

CLAVES = {"id", "numero", "resultado", "fin", "numero_ciclo", "observacion"}


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
def lote_abierto(cargar_lote, empacar, estufa, servicio, materiales):
    """Un lote en curso (sin fin ni resultado) con dos ítems."""
    ids = empacar(servicio, materiales[0], estufa.metodo, 2)
    lote = cargar_lote(estufa.equipo, ids, resultado=None, numero=7)
    return SimpleNamespace(lote=lote, item_ids=ids)


def _cierre(**cambios):
    cuerpo = {"numero_ciclo": 10211, "resultado": "aprobado"}
    cuerpo.update(cambios)
    return cuerpo


def _estado(lote):
    return (lote.resultado, lote.fin, lote.observacion, lote.numero_ciclo)


# --- Acceso -----------------------------------------------------------------

def test_sin_token_responde_401(cliente_pg):
    r = cliente_pg.post("/lotes/1/cierre", json=_cierre())

    assert r.status_code == 401


# --- Cierre correcto ---------------------------------------------------------

def test_cierra_el_lote_como_aprobado(con_sesion, db_pg, lote_abierto):
    lote = lote_abierto.lote

    r = con_sesion.post(f"/lotes/{lote.id}/cierre", json=_cierre())

    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert set(cuerpo) == CLAVES
    assert (cuerpo["id"], cuerpo["numero"], cuerpo["resultado"], cuerpo["numero_ciclo"]) == (
        lote.id,
        7,
        "aprobado",
        "10211",
    )
    db_pg.refresh(lote)
    assert lote.resultado == "aprobado"
    assert lote.numero_ciclo == "10211"
    assert lote.fin is not None
    assert lote.observacion is None


def test_el_fin_lo_pone_el_servidor(con_sesion, db_pg, lote_abierto):
    lote = lote_abierto.lote

    r = con_sesion.post(f"/lotes/{lote.id}/cierre", json=_cierre(fin="2000-01-01T00:00:00Z"))

    assert r.status_code == 200, r.text
    db_pg.refresh(lote)
    assert abs(datetime.now(timezone.utc) - lote.fin) < timedelta(minutes=1)


def test_cierra_el_lote_como_fallido_con_motivo(con_sesion, db_pg, lote_abierto):
    lote = lote_abierto.lote

    r = con_sesion.post(
        f"/lotes/{lote.id}/cierre",
        json=_cierre(resultado="fallido", observacion="Falla del equipo durante el ciclo"),
    )

    assert r.status_code == 200, r.text
    assert r.json()["resultado"] == "fallido"
    db_pg.refresh(lote)
    assert lote.resultado == "fallido"
    assert lote.observacion == "Falla del equipo durante el ciclo"
    assert lote.fin is not None


def test_el_aprobado_admite_una_observacion_opcional(con_sesion, db_pg, lote_abierto):
    lote = lote_abierto.lote

    r = con_sesion.post(f"/lotes/{lote.id}/cierre", json=_cierre(observacion="Sin novedades"))

    assert r.status_code == 200, r.text
    db_pg.refresh(lote)
    assert lote.observacion == "Sin novedades"


# --- Cuerpo inválido: 422 y el lote sigue abierto ---------------------------

@pytest.mark.parametrize(
    "cambios",
    [{}, {"observacion": None}, {"observacion": ""}, {"observacion": "   "}],
    ids=["ausente", "nula", "vacia", "en blanco"],
)
def test_fallido_sin_motivo_se_rechaza(con_sesion, db_pg, lote_abierto, cambios):
    lote = lote_abierto.lote

    r = con_sesion.post(f"/lotes/{lote.id}/cierre", json=_cierre(resultado="fallido", **cambios))

    assert r.status_code == 422
    db_pg.refresh(lote)
    assert _estado(lote) == (None, None, None, None)


@pytest.mark.parametrize("numero_ciclo", [0, -5, "abc", None], ids=["cero", "negativo", "texto", "nulo"])
def test_numero_ciclo_invalido_se_rechaza(con_sesion, db_pg, lote_abierto, numero_ciclo):
    lote = lote_abierto.lote

    r = con_sesion.post(f"/lotes/{lote.id}/cierre", json=_cierre(numero_ciclo=numero_ciclo))

    assert r.status_code == 422
    db_pg.refresh(lote)
    assert _estado(lote) == (None, None, None, None)


@pytest.mark.parametrize("resultado", ["pendiente", None], ids=["desconocido", "nulo"])
def test_resultado_invalido_se_rechaza(con_sesion, db_pg, lote_abierto, resultado):
    lote = lote_abierto.lote

    r = con_sesion.post(f"/lotes/{lote.id}/cierre", json=_cierre(resultado=resultado))

    assert r.status_code == 422
    db_pg.refresh(lote)
    assert _estado(lote) == (None, None, None, None)


# --- Lote inexistente o ya cerrado ------------------------------------------

def test_lote_inexistente_responde_404(con_sesion):
    r = con_sesion.post("/lotes/999999/cierre", json=_cierre())

    assert r.status_code == 404
    assert r.json()["detail"] == "No existe el lote 999999"


@pytest.mark.parametrize("resultado", ["aprobado", "fallido"])
def test_un_lote_ya_cerrado_no_se_cierra_de_nuevo(
    con_sesion, db_pg, cargar_lote, empacar, estufa, servicio, materiales, resultado
):
    ids = empacar(servicio, materiales[0], estufa.metodo, 1)
    lote = cargar_lote(estufa.equipo, ids, resultado=resultado)
    antes = _estado(lote)

    r = con_sesion.post(
        f"/lotes/{lote.id}/cierre",
        json=_cierre(numero_ciclo=99, resultado="fallido", observacion="Otro motivo"),
    )

    assert r.status_code == 409
    assert "cerrado" in r.json()["detail"]
    db_pg.refresh(lote)
    assert _estado(lote) == antes


# --- Efectos sobre los ítems (opción A) -------------------------------------

def test_cerrar_no_mueve_los_items_de_etapa(con_sesion, db_pg, lote_abierto):
    lote, item_ids = lote_abierto.lote, lote_abierto.item_ids

    def _eventos():
        return db_pg.scalar(
            select(func.count()).select_from(EventoItem).where(EventoItem.item_id.in_(item_ids))
        )

    antes = _eventos()

    r = con_sesion.post(f"/lotes/{lote.id}/cierre", json=_cierre())

    assert r.status_code == 200, r.text
    assert _eventos() == antes
    assert set(db_pg.scalars(select(Item.lote_id).where(Item.id.in_(item_ids)))) == {lote.id}


def test_los_items_de_un_lote_fallido_cerrado_quedan_para_reesterilizar(
    con_sesion, lote_abierto, estufa, servicio, materiales
):
    def _disponibles():
        pendientes = con_sesion.get(f"/equipos/{estufa.equipo.id}/pendientes").json()
        return sum(
            p["cantidad"]
            for p in pendientes
            if p["servicio_id"] == servicio.id and p["material_id"] == materiales[0].id
        )

    antes = _disponibles()

    r = con_sesion.post(
        f"/lotes/{lote_abierto.lote.id}/cierre",
        json=_cierre(resultado="fallido", observacion="Falla del equipo"),
    )

    assert r.status_code == 200, r.text
    assert _disponibles() == antes + 2
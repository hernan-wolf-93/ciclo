"""POST /lotes/{id}/falla-posterior: falla detectada después del cierre del lote."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.models import Etapa, EventoItem, Item
from app.models.catalogos import Equipo, MetodoEsterilizacion
from app.models.circuito import Entrega

CLAVES = {"id", "numero", "resultado", "observacion", "falla_posterior_en", "marcado_por"}


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
def lote_aprobado(cargar_lote, empacar, estufa, servicio, materiales):
    """Un lote cerrado como aprobado, con dos ítems todavía sin entregar."""
    ids = empacar(servicio, materiales[0], estufa.metodo, 2)
    lote = cargar_lote(estufa.equipo, ids, resultado="aprobado", numero=7)
    return SimpleNamespace(lote=lote, item_ids=ids)


def _falla(**cambios):
    cuerpo = {"motivo": "Indicador biológico positivo"}
    cuerpo.update(cambios)
    return cuerpo


def _estado(lote):
    return (
        lote.resultado,
        lote.fin,
        lote.observacion,
        lote.falla_posterior_en,
        lote.falla_posterior_por,
    )


def _a_almacen(db, operador, item_ids, lote):
    etapa = db.scalar(select(Etapa).where(Etapa.orden == 5))
    db.add_all(
        [
            EventoItem(item_id=i, etapa_id=etapa.id, lote_id=lote.id, operador_id=operador.id)
            for i in item_ids
        ]
    )
    db.commit()


def _entregar(db, servicio, item_ids):
    """Marca los ítems como entregados (todavía no hay API de entrega)."""
    entrega = Entrega(servicio_id=servicio.id)
    db.add(entrega)
    db.flush()
    for item_id in item_ids:
        db.get(Item, item_id).entrega_id = entrega.id
    db.commit()


# --- Acceso -----------------------------------------------------------------

def test_sin_token_responde_401(cliente_pg):
    r = cliente_pg.post("/lotes/1/falla-posterior", json=_falla())

    assert r.status_code == 401


# --- Marca correcta ----------------------------------------------------------

def test_marca_el_lote_como_fallido_y_registra_quien_y_cuando(
    con_sesion, db_pg, operador, lote_aprobado
):
    lote = lote_aprobado.lote
    fin = lote.fin

    r = con_sesion.post(f"/lotes/{lote.id}/falla-posterior", json=_falla())

    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert set(cuerpo) == CLAVES
    assert (cuerpo["id"], cuerpo["numero"], cuerpo["resultado"], cuerpo["marcado_por"]) == (
        lote.id,
        7,
        "fallido",
        operador.numero_operador,
    )
    assert cuerpo["observacion"] == "Falla posterior: Indicador biológico positivo"
    db_pg.refresh(lote)
    assert lote.resultado == "fallido"
    assert lote.falla_posterior_por == operador.id
    assert abs(datetime.now(timezone.utc) - lote.falla_posterior_en) < timedelta(minutes=1)
    assert lote.fin == fin


def test_agrega_el_motivo_a_la_observacion_existente(con_sesion, db_pg, lote_aprobado):
    lote = lote_aprobado.lote
    lote.observacion = "Sin novedades"
    db_pg.commit()

    r = con_sesion.post(f"/lotes/{lote.id}/falla-posterior", json=_falla(motivo="Control externo"))

    assert r.status_code == 200, r.text
    assert r.json()["observacion"] == "Sin novedades\nFalla posterior: Control externo"
    db_pg.refresh(lote)
    assert lote.observacion == "Sin novedades\nFalla posterior: Control externo"


def test_el_motivo_se_guarda_sin_espacios_en_los_extremos(con_sesion, lote_aprobado):
    r = con_sesion.post(
        f"/lotes/{lote_aprobado.lote.id}/falla-posterior", json=_falla(motivo="  Control externo  ")
    )

    assert r.status_code == 200, r.text
    assert r.json()["observacion"] == "Falla posterior: Control externo"


def test_el_operador_sale_del_token_y_no_del_cuerpo(con_sesion, db_pg, operador, lote_aprobado):
    lote = lote_aprobado.lote

    r = con_sesion.post(
        f"/lotes/{lote.id}/falla-posterior", json=_falla(operador_id=999999, marcado_por="otro")
    )

    assert r.status_code == 200, r.text
    assert r.json()["marcado_por"] == operador.numero_operador
    db_pg.refresh(lote)
    assert lote.falla_posterior_por == operador.id


# --- Cuerpo inválido: 422 y el lote queda igual -----------------------------

@pytest.mark.parametrize(
    "cuerpo",
    [{}, {"motivo": None}, {"motivo": ""}, {"motivo": "   "}, {"motivo": "x" * 1001}],
    ids=["ausente", "nulo", "vacio", "en blanco", "demasiado largo"],
)
def test_motivo_invalido_se_rechaza(con_sesion, db_pg, lote_aprobado, cuerpo):
    lote = lote_aprobado.lote
    antes = _estado(lote)

    r = con_sesion.post(f"/lotes/{lote.id}/falla-posterior", json=cuerpo)

    assert r.status_code == 422
    db_pg.refresh(lote)
    assert _estado(lote) == antes


# --- Lote inexistente, en curso o ya fallido --------------------------------

def test_lote_inexistente_responde_404(con_sesion):
    r = con_sesion.post("/lotes/999999/falla-posterior", json=_falla())

    assert r.status_code == 404
    assert r.json()["detail"] == "No existe el lote 999999"


def test_un_lote_en_curso_no_admite_falla_posterior(con_sesion, db_pg, cargar_lote, estufa):
    lote = cargar_lote(estufa.equipo, [], resultado=None)
    antes = _estado(lote)

    r = con_sesion.post(f"/lotes/{lote.id}/falla-posterior", json=_falla())

    assert r.status_code == 409
    assert "en curso" in r.json()["detail"]
    db_pg.refresh(lote)
    assert _estado(lote) == antes


def test_un_lote_que_ya_fallo_en_el_cierre_no_se_marca_de_nuevo(
    con_sesion, db_pg, cargar_lote, estufa
):
    lote = cargar_lote(estufa.equipo, [], resultado="fallido")
    antes = _estado(lote)

    r = con_sesion.post(f"/lotes/{lote.id}/falla-posterior", json=_falla())

    assert r.status_code == 409
    assert "fallido" in r.json()["detail"]
    db_pg.refresh(lote)
    assert _estado(lote) == antes


def test_la_segunda_marca_se_rechaza_y_no_repite_el_motivo(con_sesion, db_pg, lote_aprobado):
    lote = lote_aprobado.lote
    primera = con_sesion.post(f"/lotes/{lote.id}/falla-posterior", json=_falla())
    assert primera.status_code == 200, primera.text
    db_pg.refresh(lote)
    tras_la_primera = _estado(lote)

    segunda = con_sesion.post(f"/lotes/{lote.id}/falla-posterior", json=_falla(motivo="Otro motivo"))

    assert segunda.status_code == 409
    assert "fallido" in segunda.json()["detail"]
    db_pg.refresh(lote)
    assert _estado(lote) == tras_la_primera


# --- Ítems entregados --------------------------------------------------------

def test_con_un_item_entregado_se_rechaza(con_sesion, db_pg, servicio, lote_aprobado):
    lote = lote_aprobado.lote
    _entregar(db_pg, servicio, lote_aprobado.item_ids[:1])
    antes = _estado(lote)

    r = con_sesion.post(f"/lotes/{lote.id}/falla-posterior", json=_falla())

    assert r.status_code == 409
    assert "entreg" in r.json()["detail"]
    db_pg.refresh(lote)
    assert _estado(lote) == antes


def test_un_item_entregado_de_otro_lote_no_bloquea(
    con_sesion, db_pg, cargar_lote, empacar, estufa, servicio, materiales, lote_aprobado
):
    otros = empacar(servicio, materiales[1], estufa.metodo, 1)
    cargar_lote(estufa.equipo, otros, resultado="aprobado", numero=8)
    _entregar(db_pg, servicio, otros)

    r = con_sesion.post(f"/lotes/{lote_aprobado.lote.id}/falla-posterior", json=_falla())

    assert r.status_code == 200, r.text


# --- Efecto sobre los ítems --------------------------------------------------

def test_los_items_en_almacen_quedan_disponibles_para_reesterilizar(
    con_sesion, db_pg, operador, lote_aprobado, estufa, servicio, materiales
):
    _a_almacen(db_pg, operador, lote_aprobado.item_ids, lote_aprobado.lote)

    def _disponibles():
        pendientes = con_sesion.get(f"/equipos/{estufa.equipo.id}/pendientes").json()
        return sum(
            p["cantidad"]
            for p in pendientes
            if p["servicio_id"] == servicio.id and p["material_id"] == materiales[0].id
        )

    antes = _disponibles()

    r = con_sesion.post(f"/lotes/{lote_aprobado.lote.id}/falla-posterior", json=_falla())

    assert r.status_code == 200, r.text
    assert _disponibles() == antes + 2
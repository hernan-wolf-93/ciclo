"""Ítems en Almacén cuyo lote quedó fallido después del cierre: vuelven a Esterilización."""

from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.models import Etapa, EventoItem, Item
from app.models.catalogos import Equipo, MetodoEsterilizacion, Programa
from app.services.flujo import ErrorDeFlujo, situacion_del_item, validar_avance


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
    programa = db_pg.scalar(
        select(Programa).where(Programa.metodo_id == metodo.id).order_by(Programa.id).limit(1)
    )
    return SimpleNamespace(metodo=metodo, equipo=equipo, programa=programa)


def _a_almacen(db, operador, item_ids, lote):
    """Registra el evento de Almacén. Con lote=None simula uno sin lote registrado."""
    etapa = db.scalar(select(Etapa).where(Etapa.orden == 5))
    db.add_all(
        [
            EventoItem(
                item_id=i,
                etapa_id=etapa.id,
                lote_id=lote.id if lote else None,
                operador_id=operador.id,
            )
            for i in item_ids
        ]
    )
    db.commit()


def _marcar_fallido(db, lote):
    """Simula la falla posterior al cierre (todavía no hay endpoint)."""
    lote.resultado = "fallido"
    lote.observacion = "Falla posterior de prueba"
    db.commit()


@pytest.fixture
def en_almacen(db_pg, operador, cargar_lote, empacar, estufa, servicio, materiales):
    """Dos ítems de un lote aprobado, ya en Almacén (el evento lleva el lote)."""
    ids = empacar(servicio, materiales[0], estufa.metodo, 2)
    lote = cargar_lote(estufa.equipo, ids, resultado="aprobado", numero=3)
    _a_almacen(db_pg, operador, ids, lote)
    return SimpleNamespace(lote=lote, item_ids=ids)


def test_en_almacen_el_resultado_sale_del_lote_del_ultimo_evento(db_pg, en_almacen):
    antes = situacion_del_item(db_pg, en_almacen.item_ids[0])
    _marcar_fallido(db_pg, en_almacen.lote)
    despues = situacion_del_item(db_pg, en_almacen.item_ids[0])

    assert (antes.orden_etapa, antes.resultado_ultimo_lote) == (5, "aprobado")
    assert (despues.orden_etapa, despues.resultado_ultimo_lote) == (5, "fallido")


def test_item_en_almacen_de_lote_aprobado_va_a_entrega(db_pg, en_almacen):
    validar_avance(db_pg, en_almacen.item_ids[0], 6)  # no debe lanzar nada


def test_item_en_almacen_de_lote_fallido_no_va_a_entrega(db_pg, en_almacen):
    _marcar_fallido(db_pg, en_almacen.lote)

    with pytest.raises(ErrorDeFlujo, match="fallido"):
        validar_avance(db_pg, en_almacen.item_ids[0], 6)


def test_item_en_almacen_de_lote_fallido_puede_reesterilizarse(db_pg, en_almacen):
    _marcar_fallido(db_pg, en_almacen.lote)

    validar_avance(db_pg, en_almacen.item_ids[0], 4)  # no debe lanzar nada


def test_item_en_almacen_de_lote_aprobado_no_puede_reesterilizarse(db_pg, en_almacen):
    with pytest.raises(ErrorDeFlujo, match="fallido"):
        validar_avance(db_pg, en_almacen.item_ids[0], 4)


def test_item_en_almacen_sin_lote_registrado_no_avanza(
    db_pg, operador, cargar_lote, empacar, estufa, servicio, materiales
):
    ids = empacar(servicio, materiales[0], estufa.metodo, 1)
    cargar_lote(estufa.equipo, ids, resultado="aprobado")
    _a_almacen(db_pg, operador, ids, None)

    with pytest.raises(ErrorDeFlujo, match="no tiene lote"):
        validar_avance(db_pg, ids[0], 6)


def test_los_items_de_almacen_de_un_lote_fallido_quedan_disponibles_para_el_equipo(
    con_sesion, db_pg, en_almacen, estufa, servicio, materiales
):
    def _disponibles():
        pendientes = con_sesion.get(f"/equipos/{estufa.equipo.id}/pendientes").json()
        return sum(
            p["cantidad"]
            for p in pendientes
            if p["servicio_id"] == servicio.id and p["material_id"] == materiales[0].id
        )

    antes = _disponibles()
    _marcar_fallido(db_pg, en_almacen.lote)

    assert _disponibles() == antes + 2


def test_se_pueden_cargar_de_nuevo_en_otro_lote_los_items_de_almacen(
    con_sesion, db_pg, en_almacen, estufa, servicio, materiales
):
    _marcar_fallido(db_pg, en_almacen.lote)

    r = con_sesion.post(
        "/lotes",
        json={
            "equipo_id": estufa.equipo.id,
            "programa_id": estufa.programa.id,
            "numero": 4,
            "lineas": [
                {"servicio_id": servicio.id, "material_id": materiales[0].id, "cantidad": 2}
            ],
        },
    )

    assert r.status_code == 201, r.text
    assert r.json()["total_items"] == 2
    nuevo = r.json()["id"]
    assert set(db_pg.scalars(select(Item.id).where(Item.lote_id == nuevo))) == set(
        en_almacen.item_ids
    )
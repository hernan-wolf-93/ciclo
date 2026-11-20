"""Avance de lavado y empaque: servicio contra PostgreSQL (ciclo_test)."""

import re

import pytest
from sqlalchemy import select

from app.models import Etapa, EventoItem, Item
from app.schemas.avance import AvanceIn, LineaAvanceIn
from app.schemas.recepcion import LineaRecepcionIn, RecepcionIn
from app.services import avance as servicio_avance
from app.services.avance import ErrorDeAvance, registrar_avance
from app.services.recepcion import registrar_recepcion


def _recibir(db, operador, servicio, material, cantidad):
    """Recibe unidades con el servicio real y devuelve los ids de los ítems del material."""
    registrar_recepcion(
        db,
        operador,
        RecepcionIn(
            servicio_id=servicio.id,
            items=[LineaRecepcionIn(material_id=material.id, cantidad=cantidad)],
            completo=True,
        ),
    )
    return list(db.scalars(select(Item.id).where(Item.material_id == material.id).order_by(Item.id)))


def _avance(etapa, *lineas, **extra):
    return AvanceIn(
        etapa_orden=etapa,
        items=[LineaAvanceIn(material_id=m.id, cantidad=c) for m, c in lineas],
        **extra,
    )


def _eventos(db, item_ids, orden):
    return list(
        db.scalars(
            select(EventoItem)
            .join(Etapa, Etapa.id == EventoItem.etapa_id)
            .where(EventoItem.item_id.in_(item_ids), Etapa.orden == orden)
            .order_by(EventoItem.id)
        )
    )


def test_avanza_a_lavado_y_firma_con_el_operador(db_pg, operador, servicio, materiales):
    ids = _recibir(db_pg, operador, servicio, materiales[0], 3)
    total = registrar_avance(db_pg, operador, _avance(2, (materiales[0], 3)))
    assert total == 3
    eventos = _eventos(db_pg, ids, 2)
    assert {e.item_id for e in eventos} == set(ids)
    assert {e.operador_id for e in eventos} == {operador.id}


def test_toma_los_items_mas_antiguos(db_pg, operador, servicio, materiales):
    ids = _recibir(db_pg, operador, servicio, materiales[0], 3)
    registrar_avance(db_pg, operador, _avance(2, (materiales[0], 2)))
    assert {e.item_id for e in _eventos(db_pg, ids, 2)} == set(ids[:2])


def test_no_toma_items_de_otro_material(db_pg, operador, servicio, materiales):
    _recibir(db_pg, operador, servicio, materiales[0], 2)
    ids_otro = _recibir(db_pg, operador, servicio, materiales[1], 2)
    registrar_avance(db_pg, operador, _avance(2, (materiales[0], 2)))
    assert _eventos(db_pg, ids_otro, 2) == []


def test_empaque_exige_haber_pasado_por_lavado(db_pg, operador, servicio, materiales):
    _recibir(db_pg, operador, servicio, materiales[0], 2)
    with pytest.raises(ErrorDeAvance, match="esperando"):
        registrar_avance(db_pg, operador, _avance(3, (materiales[0], 2)))


def test_avanza_a_empaque_despues_de_lavado(db_pg, operador, servicio, materiales):
    ids = _recibir(db_pg, operador, servicio, materiales[0], 2)
    registrar_avance(db_pg, operador, _avance(2, (materiales[0], 2)))
    assert registrar_avance(db_pg, operador, _avance(3, (materiales[0], 2))) == 2
    assert {e.item_id for e in _eventos(db_pg, ids, 3)} == set(ids)


def test_pedir_mas_de_lo_que_hay_se_rechaza(db_pg, operador, servicio, materiales):
    _recibir(db_pg, operador, servicio, materiales[0], 2)
    with pytest.raises(ErrorDeAvance, match=re.escape(materiales[0].nombre)) as error:
        registrar_avance(db_pg, operador, _avance(2, (materiales[0], 5)))
    assert "solo hay 2" in str(error.value)


def test_todo_o_nada_entre_lineas(db_pg, operador, servicio, materiales):
    ids_a = _recibir(db_pg, operador, servicio, materiales[0], 1)
    _recibir(db_pg, operador, servicio, materiales[1], 1)
    with pytest.raises(ErrorDeAvance):
        registrar_avance(db_pg, operador, _avance(2, (materiales[0], 1), (materiales[1], 5)))
    assert _eventos(db_pg, ids_a, 2) == []


def test_repetir_el_pedido_no_avanza_dos_veces(db_pg, operador, servicio, materiales):
    _recibir(db_pg, operador, servicio, materiales[0], 2)
    registrar_avance(db_pg, operador, _avance(2, (materiales[0], 2)))
    with pytest.raises(ErrorDeAvance):
        registrar_avance(db_pg, operador, _avance(2, (materiales[0], 2)))


def test_solo_desinfeccion_guarda_marca_y_observacion(db_pg, operador, servicio, materiales):
    ids = _recibir(db_pg, operador, servicio, materiales[0], 1)
    registrar_avance(
        db_pg,
        operador,
        _avance(2, (materiales[0], 1), solo_desinfeccion=True, observacion="Ortopedia: llegó lavada"),
    )
    evento = _eventos(db_pg, ids, 2)[0]
    assert evento.solo_desinfeccion is True
    assert evento.observacion == "Ortopedia: llegó lavada"


def test_avance_comun_no_marca_excepcion(db_pg, operador, servicio, materiales):
    ids = _recibir(db_pg, operador, servicio, materiales[0], 1)
    registrar_avance(db_pg, operador, _avance(2, (materiales[0], 1)))
    evento = _eventos(db_pg, ids, 2)[0]
    assert evento.solo_desinfeccion is False
    assert evento.observacion is None


def test_choque_con_otro_operador_se_traduce_a_error_de_avance(
    db_pg, operador, servicio, materiales, monkeypatch
):
    ids = _recibir(db_pg, operador, servicio, materiales[0], 1)
    registrar_avance(db_pg, operador, _avance(2, (materiales[0], 1)))
    # Simula que otro operador ganó la carrera: se vuelve a elegir un ítem que ya está en Lavado.
    monkeypatch.setattr(servicio_avance, "_elegir_items", lambda db, datos: ids)
    monkeypatch.setattr(servicio_avance, "validar_avance_varios", lambda db, item_ids, orden: None)
    with pytest.raises(ErrorDeAvance, match="otro operador"):
        registrar_avance(db_pg, operador, _avance(2, (materiales[0], 1)))
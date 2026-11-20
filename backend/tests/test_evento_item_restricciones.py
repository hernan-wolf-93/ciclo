"""Restricciones de evento_item contra PostgreSQL (ciclo_test)."""

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models import Etapa, EventoItem, Item, Recepcion

CHECK = "ck_evento_item_excepcion_requiere_observacion"


@pytest.fixture
def item(db_pg, servicio, materiales):
    recepcion = Recepcion(servicio_id=servicio.id, completo=True)
    db_pg.add(recepcion)
    db_pg.flush()
    nuevo = Item(recepcion_id=recepcion.id, material_id=materiales[0].id)
    db_pg.add(nuevo)
    db_pg.flush()
    return nuevo


@pytest.fixture
def etapa_lavado(db_pg):
    return db_pg.scalar(select(Etapa).where(Etapa.orden == 2))


def _evento(item, etapa, operador, **campos):
    return EventoItem(item_id=item.id, etapa_id=etapa.id, operador_id=operador.id, **campos)


@pytest.mark.parametrize("observacion", [None, "", "   "])
def test_excepcion_sin_observacion_se_rechaza(db_pg, item, etapa_lavado, operador, observacion):
    with pytest.raises(IntegrityError) as error:
        with db_pg.begin_nested():
            db_pg.add(_evento(item, etapa_lavado, operador, solo_desinfeccion=True, observacion=observacion))
            db_pg.flush()
    assert CHECK in str(error.value)


def test_excepcion_con_observacion_se_acepta(db_pg, item, etapa_lavado, operador):
    evento = _evento(item, etapa_lavado, operador, solo_desinfeccion=True, observacion="Ortopedia: llegó lavada")
    db_pg.add(evento)
    db_pg.flush()
    assert evento.id is not None


def test_evento_comun_no_es_excepcion_por_defecto(db_pg, item, etapa_lavado, operador):
    evento = _evento(item, etapa_lavado, operador)
    db_pg.add(evento)
    db_pg.flush()
    db_pg.refresh(evento)
    assert evento.solo_desinfeccion is False
    assert evento.observacion is None


def test_observacion_libre_sin_excepcion_se_acepta(db_pg, item, etapa_lavado, operador):
    evento = _evento(item, etapa_lavado, operador, observacion="Material con restos visibles")
    db_pg.add(evento)
    db_pg.flush()
    assert evento.id is not None
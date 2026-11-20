"""Numeración de lotes: consulta contra PostgreSQL (ciclo_test)."""

import pytest
from sqlalchemy import select

from app.models import Equipo, Lote, Programa
from app.services.numeracion_lote import EquipoInexistente, proponer_numero


@pytest.fixture
def equipos(db_pg):
    """Dos equipos del mismo método (a y b) y uno de otro método (otro)."""
    activos = list(db_pg.scalars(select(Equipo).where(Equipo.activo.is_(True)).order_by(Equipo.id)))
    por_metodo: dict[int, list[Equipo]] = {}
    for equipo in activos:
        por_metodo.setdefault(equipo.metodo_id, []).append(equipo)

    gemelos = next((lista for lista in por_metodo.values() if len(lista) >= 2), None)
    otros = next((lista for metodo, lista in por_metodo.items() if gemelos and metodo != gemelos[0].metodo_id), None)
    if gemelos is None or otros is None:
        pytest.skip("Hacen falta dos equipos de un método y uno de otro (migración 0002)")
    return {"a": gemelos[0], "b": gemelos[1], "otro": otros[0]}


def _crear_lote(db, equipo, operador, numero):
    programa = db.scalar(select(Programa).where(Programa.metodo_id == equipo.metodo_id).limit(1))
    if programa is None:
        programa = Programa(nombre="Programa de prueba", metodo_id=equipo.metodo_id)
        db.add(programa)
        db.flush()
    lote = Lote(numero=numero, equipo_id=equipo.id, programa_id=programa.id, operador_id=operador.id)
    db.add(lote)
    db.flush()
    return lote


def test_sin_lotes_del_equipo_propone_1(db_pg, equipos):
    assert proponer_numero(db_pg, equipos["a"].id) == 1


def test_propone_el_siguiente_al_ultimo(db_pg, equipos, operador):
    _crear_lote(db_pg, equipos["a"], operador, 5)
    assert proponer_numero(db_pg, equipos["a"].id) == 6


def test_tras_999_reinicia_en_1(db_pg, equipos, operador):
    _crear_lote(db_pg, equipos["a"], operador, 999)
    assert proponer_numero(db_pg, equipos["a"].id) == 1


def test_el_ultimo_es_el_de_mayor_id_y_no_el_de_mayor_numero(db_pg, equipos, operador):
    """Después de 999 viene un 3: el siguiente es 4, no 1."""
    _crear_lote(db_pg, equipos["a"], operador, 999)
    _crear_lote(db_pg, equipos["a"], operador, 3)
    assert proponer_numero(db_pg, equipos["a"].id) == 4


def test_equipos_del_mismo_metodo_tienen_numeracion_propia(db_pg, equipos, operador):
    _crear_lote(db_pg, equipos["a"], operador, 7)
    assert proponer_numero(db_pg, equipos["a"].id) == 8
    assert proponer_numero(db_pg, equipos["b"].id) == 1


def test_equipo_de_otro_metodo_tiene_su_propia_numeracion(db_pg, equipos, operador):
    _crear_lote(db_pg, equipos["a"], operador, 7)
    assert proponer_numero(db_pg, equipos["otro"].id) == 1


def test_equipo_inexistente(db_pg):
    with pytest.raises(EquipoInexistente):
        proponer_numero(db_pg, 999999)
"""Código de recuperación: reglas puras (sin base de datos)."""

from app.core.codigo_recuperacion import ALFABETO, LARGO_CODIGO, generar_codigo


def test_el_codigo_tiene_el_largo_definido():
    assert len(generar_codigo()) == LARGO_CODIGO


def test_el_codigo_usa_solo_el_alfabeto():
    assert set(generar_codigo()) <= set(ALFABETO)


def test_el_alfabeto_no_tiene_caracteres_ambiguos():
    assert not set("0O1I") & set(ALFABETO)


def test_dos_codigos_consecutivos_son_distintos():
    assert generar_codigo() != generar_codigo()
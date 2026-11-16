"""Reglas puras del historial de lotes: no necesitan base de datos."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.services.lote import _lotes_vecinos, fin_aireacion

FIN = datetime(2026, 11, 12, 13, 30, tzinfo=timezone.utc)
ESTERILIZACION = 4


def test_aireacion_es_fin_mas_dias_en_oxido_de_etileno():
    assert fin_aireacion("Óxido de etileno", FIN, 7) == FIN + timedelta(days=7)


def test_aireacion_nula_en_otros_metodos():
    assert fin_aireacion("Calor húmedo", FIN, 7) is None


def test_aireacion_nula_si_no_termino_o_no_tiene_items():
    assert fin_aireacion("Óxido de etileno", None, 7) is None
    assert fin_aireacion("Óxido de etileno", FIN, None) is None


def _ev(etapa_id, lote_id=None):
    return SimpleNamespace(etapa_id=etapa_id, lote_id=lote_id)


def test_vecinos_de_un_item_reesterilizado():
    eventos = {1: [_ev(1), _ev(2), _ev(3), _ev(ESTERILIZACION, 10), _ev(ESTERILIZACION, 20), _ev(5)]}
    assert _lotes_vecinos(eventos, ESTERILIZACION, 10) == (set(), {20})
    assert _lotes_vecinos(eventos, ESTERILIZACION, 20) == ({10}, set())


def test_vecinos_ignora_lote_id_fuera_de_esterilizacion():
    eventos = {1: [_ev(ESTERILIZACION, 10), _ev(5, 99)]}
    assert _lotes_vecinos(eventos, ESTERILIZACION, 10) == (set(), set())


def test_vecinos_de_un_lote_sin_reesterilizar():
    eventos = {1: [_ev(1), _ev(ESTERILIZACION, 10)], 2: [_ev(1), _ev(ESTERILIZACION, 10)]}
    assert _lotes_vecinos(eventos, ESTERILIZACION, 10) == (set(), set())

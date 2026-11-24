"""Reglas puras de los avisos: no necesitan base de datos."""

from datetime import datetime, timedelta, timezone

from app.services import reglas_avisos as reglas

AHORA = datetime(2026, 11, 20, 15, 0, tzinfo=timezone.utc)


def test_supera_justo_en_el_umbral():
    assert reglas.supera(AHORA - timedelta(minutes=120), AHORA, 120)
    assert not reglas.supera(AHORA - timedelta(minutes=119, seconds=59), AHORA, 120)


def test_minutos_entre_fechas_de_distinta_zona():
    # La base devuelve fechas en hora de Buenos Aires (-03:00); "ahora" está en UTC
    buenos_aires = timezone(timedelta(hours=-3))
    desde = datetime(2026, 11, 20, 10, 0, tzinfo=buenos_aires)  # = 13:00 UTC
    assert reglas.minutos_entre(desde, AHORA) == 120


def test_umbral_esterilizacion_por_metodo_y_por_defecto():
    assert reglas.umbral_esterilizacion("Calor húmedo") == reglas.UMBRAL_ESTERILIZACION_POR_METODO_MIN["Calor húmedo"]
    assert reglas.umbral_esterilizacion("Método nuevo") == reglas.UMBRAL_ESTERILIZACION_POR_DEFECTO_MIN


def test_duracion_legible():
    assert reglas.duracion(45) == "45 min"
    assert reglas.duracion(120) == "2 h"
    assert reglas.duracion(200) == "3 h 20 min"
    assert reglas.duracion(24 * 60) == "1 d"
    assert reglas.duracion(51 * 60 + 10) == "2 d 3 h"


# --- Gravedad (tarjeta "Panel Requieren atención") ----------------------------


def test_gravedad_alta_justo_al_llegar_al_doble_del_umbral():
    umbral = 120
    assert reglas.gravedad(1, reglas.FACTOR_GRAVE * umbral - 1, umbral) == "media"
    assert reglas.gravedad(1, reglas.FACTOR_GRAVE * umbral, umbral) == "alta"


def test_gravedad_se_mide_contra_el_umbral_de_cada_etapa():
    # 3 h de exceso es grave en Recepción (umbral 2 h) pero no en óxido de etileno (15 h)
    assert reglas.gravedad(1, 120 + 180, 120) == "alta"
    assert reglas.gravedad("lote_sin_cerrar", 900 + 180, 900) == "media"


def test_lote_fallido_es_grave_aunque_recien_pase_el_umbral():
    assert reglas.gravedad("lote_fallido", reglas.UMBRAL_TRAS_CIERRE_MIN, reglas.UMBRAL_TRAS_CIERRE_MIN) == "alta"


def test_proporcion_del_umbral():
    assert reglas.proporcion(240, 120) == 2.0
    assert reglas.proporcion(120, 120) == 1.0

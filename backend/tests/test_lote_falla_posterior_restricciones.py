"""Restricciones de lote para la falla posterior al cierre (migración 0011)."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from app.models.catalogos import Equipo, MetodoEsterilizacion


@pytest.fixture
def equipo(db_pg):
    metodo = db_pg.scalar(
        select(MetodoEsterilizacion).where(MetodoEsterilizacion.nombre == "Calor seco")
    )
    return db_pg.scalar(
        select(Equipo)
        .where(Equipo.metodo_id == metodo.id, Equipo.activo.is_(True))
        .order_by(Equipo.id)
        .limit(1)
    )


def test_la_marca_sin_operador_se_rechaza(db_pg, cargar_lote, equipo):
    lote = cargar_lote(equipo, [], resultado="fallido")
    lote.falla_posterior_en = lote.fin + timedelta(minutes=1)

    with pytest.raises(IntegrityError, match="ck_lote_falla_posterior_completa"):
        db_pg.commit()


def test_el_operador_sin_marca_de_tiempo_se_rechaza(db_pg, operador, cargar_lote, equipo):
    lote = cargar_lote(equipo, [], resultado="fallido")
    lote.falla_posterior_por = operador.id

    with pytest.raises(IntegrityError, match="ck_lote_falla_posterior_completa"):
        db_pg.commit()


def test_la_falla_posterior_de_un_lote_aprobado_se_rechaza(db_pg, operador, cargar_lote, equipo):
    lote = cargar_lote(equipo, [], resultado="aprobado")
    lote.falla_posterior_en = lote.fin + timedelta(minutes=1)
    lote.falla_posterior_por = operador.id

    with pytest.raises(IntegrityError, match="ck_lote_falla_posterior_es_fallido"):
        db_pg.commit()


def test_la_falla_posterior_de_un_lote_sin_resultado_se_rechaza(
    db_pg, operador, cargar_lote, equipo
):
    # resultado NULL: un CHECK escrito como "resultado = 'fallido'" lo dejaría pasar
    # (NULL no es falso). Por eso la regla usa IS NOT DISTINCT FROM.
    lote = cargar_lote(equipo, [], resultado=None)
    lote.fin = datetime.now(timezone.utc)
    lote.falla_posterior_en = lote.fin + timedelta(minutes=1)
    lote.falla_posterior_por = operador.id

    with pytest.raises(IntegrityError, match="ck_lote_falla_posterior_es_fallido"):
        db_pg.commit()


def test_la_marca_anterior_al_cierre_se_rechaza(db_pg, operador, cargar_lote, equipo):
    lote = cargar_lote(equipo, [], resultado="fallido")
    lote.falla_posterior_en = lote.fin - timedelta(minutes=1)
    lote.falla_posterior_por = operador.id

    with pytest.raises(IntegrityError, match="ck_lote_falla_posterior_despues_del_cierre"):
        db_pg.commit()


def test_una_marca_valida_se_guarda(db_pg, operador, cargar_lote, equipo):
    lote = cargar_lote(equipo, [], resultado="fallido")
    lote.falla_posterior_en = lote.fin + timedelta(minutes=1)
    lote.falla_posterior_por = operador.id
    db_pg.commit()

    fila = db_pg.execute(
        text("SELECT falla_posterior_en, falla_posterior_por FROM lote WHERE id = :id"),
        {"id": lote.id},
    ).one()
    assert fila.falla_posterior_por == operador.id
    assert fila.falla_posterior_en is not None
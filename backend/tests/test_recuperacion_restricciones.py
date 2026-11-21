"""Restricciones de recuperacion_contrasena contra PostgreSQL (ciclo_test)."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import Operador, RecuperacionContrasena


@pytest.fixture
def otro_operador(db_pg, operador):
    """Segundo operador, que hace de administrador que genera el código."""
    nuevo = Operador(numero_operador="T-0002", contrasena_hash="hash-de-prueba", rol_id=operador.rol_id)
    db_pg.add(nuevo)
    db_pg.flush()
    return nuevo


def _codigo(operador, generado_por, **campos):
    ahora = datetime.now(timezone.utc)
    base = {
        "operador_id": operador.id,
        "generado_por_id": generado_por.id,
        "codigo_hash": "hash-de-prueba",
        "creado": ahora,
        "vence": ahora + timedelta(minutes=30),
    }
    base.update(campos)
    return RecuperacionContrasena(**base)


def _rechaza(db, codigo, nombre_restriccion):
    with pytest.raises(IntegrityError) as error:
        with db.begin_nested():
            db.add(codigo)
            db.flush()
    assert nombre_restriccion in str(error.value)


@pytest.mark.parametrize("desfase", [timedelta(0), timedelta(minutes=-1)], ids=["igual a creado", "anterior a creado"])
def test_vencimiento_no_posterior_se_rechaza(db_pg, operador, otro_operador, desfase):
    ahora = datetime.now(timezone.utc)
    codigo = _codigo(operador, otro_operador, creado=ahora, vence=ahora + desfase)
    _rechaza(db_pg, codigo, "ck_recuperacion_vence_posterior")


def test_uso_anterior_a_la_creacion_se_rechaza(db_pg, operador, otro_operador):
    ahora = datetime.now(timezone.utc)
    codigo = _codigo(operador, otro_operador, creado=ahora, usado=ahora - timedelta(hours=1))
    _rechaza(db_pg, codigo, "ck_recuperacion_uso_posterior")


def test_codigo_sin_usar_se_acepta(db_pg, operador, otro_operador):
    codigo = _codigo(operador, otro_operador)
    db_pg.add(codigo)
    db_pg.flush()
    assert codigo.id is not None
    assert codigo.usado is None


def test_uso_posterior_a_la_creacion_se_acepta(db_pg, operador, otro_operador):
    ahora = datetime.now(timezone.utc)
    codigo = _codigo(operador, otro_operador, creado=ahora, usado=ahora + timedelta(minutes=5))
    db_pg.add(codigo)
    db_pg.flush()
    assert codigo.id is not None


def test_creado_tiene_valor_por_defecto(db_pg, operador, otro_operador):
    ahora = datetime.now(timezone.utc)
    codigo = RecuperacionContrasena(
        operador_id=operador.id,
        generado_por_id=otro_operador.id,
        codigo_hash="hash-de-prueba",
        vence=ahora + timedelta(minutes=30),
    )
    db_pg.add(codigo)
    db_pg.flush()
    db_pg.refresh(codigo)
    assert codigo.creado is not None


def test_operador_inexistente_se_rechaza(db_pg, operador, otro_operador):
    codigo = _codigo(operador, otro_operador, operador_id=999999)
    _rechaza(db_pg, codigo, "recuperacion_contrasena_operador_id_fkey")


def test_generador_inexistente_se_rechaza(db_pg, operador, otro_operador):
    codigo = _codigo(operador, otro_operador, generado_por_id=999999)
    _rechaza(db_pg, codigo, "recuperacion_contrasena_generado_por_id_fkey")
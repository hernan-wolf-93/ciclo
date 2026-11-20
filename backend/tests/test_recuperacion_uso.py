"""Uso del código de recuperación: servicio contra PostgreSQL (ciclo_test)."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.core.roles import ROL_ADMIN_PRINCIPAL, ROL_OPERADOR
from app.core.seguridad import verificar_contrasena
from app.models import Operador, RecuperacionContrasena, Rol
from app.schemas.recuperacion import RecuperarContrasenaIn
from app.services.recuperacion import (
    MENSAJE_CODIGO_INVALIDO,
    CodigoInvalido,
    generar_codigo_recuperacion,
    restablecer_contrasena,
)

CLAVE_NUEVA = "clave-nueva-1"


def _operador(db, numero, nombre_rol, activo=True):
    rol = db.scalar(select(Rol).where(Rol.nombre == nombre_rol))
    nuevo = Operador(numero_operador=numero, contrasena_hash="hash-de-prueba", rol_id=rol.id, activo=activo)
    db.add(nuevo)
    db.flush()
    return nuevo


def _pedido(numero, codigo, clave=CLAVE_NUEVA):
    return RecuperarContrasenaIn(numero_operador=numero, codigo=codigo, contrasena_nueva=clave)


@pytest.fixture
def caso(db_pg):
    """Un administrador, un operador y un código recién generado para ese operador."""
    principal = _operador(db_pg, "T-P1", ROL_ADMIN_PRINCIPAL)
    destino = _operador(db_pg, "T-O1", ROL_OPERADOR)
    codigo, _ = generar_codigo_recuperacion(db_pg, principal, destino.id)
    return principal, destino, codigo


def _ultimo_registro(db, operador):
    return db.scalar(
        select(RecuperacionContrasena)
        .where(RecuperacionContrasena.operador_id == operador.id)
        .order_by(RecuperacionContrasena.id.desc())
    )


def test_restablece_la_contrasena_y_marca_el_codigo(db_pg, caso):
    _, destino, codigo = caso
    restablecer_contrasena(db_pg, _pedido(destino.numero_operador, codigo))
    db_pg.refresh(destino)
    assert verificar_contrasena(CLAVE_NUEVA, destino.contrasena_hash)
    assert _ultimo_registro(db_pg, destino).usado is not None


def test_el_codigo_no_se_puede_usar_dos_veces(db_pg, caso):
    _, destino, codigo = caso
    restablecer_contrasena(db_pg, _pedido(destino.numero_operador, codigo))
    with pytest.raises(CodigoInvalido):
        restablecer_contrasena(db_pg, _pedido(destino.numero_operador, codigo, "otra-clave-2"))
    db_pg.refresh(destino)
    assert verificar_contrasena(CLAVE_NUEVA, destino.contrasena_hash)


def test_codigo_incorrecto_no_cambia_nada(db_pg, caso):
    _, destino, _ = caso
    with pytest.raises(CodigoInvalido):
        restablecer_contrasena(db_pg, _pedido(destino.numero_operador, "ZZZZZZZZ"))
    db_pg.refresh(destino)
    assert destino.contrasena_hash == "hash-de-prueba"
    assert _ultimo_registro(db_pg, destino).usado is None


def test_codigo_vencido_se_rechaza(db_pg, caso):
    _, destino, codigo = caso
    registro = _ultimo_registro(db_pg, destino)
    ahora = datetime.now(timezone.utc)
    registro.creado = ahora - timedelta(hours=1)
    registro.vence = ahora - timedelta(minutes=30)
    db_pg.flush()
    with pytest.raises(CodigoInvalido):
        restablecer_contrasena(db_pg, _pedido(destino.numero_operador, codigo))
    db_pg.refresh(destino)
    assert destino.contrasena_hash == "hash-de-prueba"


def test_operador_dado_de_baja_se_rechaza(db_pg, caso):
    _, destino, codigo = caso
    destino.activo = False
    db_pg.flush()
    with pytest.raises(CodigoInvalido):
        restablecer_contrasena(db_pg, _pedido(destino.numero_operador, codigo))


def test_un_codigo_nuevo_invalida_el_anterior(db_pg, caso):
    principal, destino, viejo = caso
    nuevo, _ = generar_codigo_recuperacion(db_pg, principal, destino.id)
    with pytest.raises(CodigoInvalido):
        restablecer_contrasena(db_pg, _pedido(destino.numero_operador, viejo))
    restablecer_contrasena(db_pg, _pedido(destino.numero_operador, nuevo))  # no debe lanzar nada


def test_el_codigo_se_acepta_en_minusculas(db_pg, caso):
    _, destino, codigo = caso
    restablecer_contrasena(db_pg, _pedido(destino.numero_operador, codigo.lower()))
    db_pg.refresh(destino)
    assert verificar_contrasena(CLAVE_NUEVA, destino.contrasena_hash)


def test_todos_los_motivos_dan_el_mismo_mensaje(db_pg, caso):
    _, destino, codigo = caso
    mensajes = set()
    for numero, cod in [("NO-EXISTE", codigo), (destino.numero_operador, "ZZZZZZZZ")]:
        with pytest.raises(CodigoInvalido) as error:
            restablecer_contrasena(db_pg, _pedido(numero, cod))
        mensajes.add(str(error.value))
    assert mensajes == {MENSAJE_CODIGO_INVALIDO}
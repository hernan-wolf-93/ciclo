"""Generación del código de recuperación: servicio contra PostgreSQL (ciclo_test)."""

from datetime import timedelta

import pytest
from sqlalchemy import func, select

from app.core.codigo_recuperacion import LARGO_CODIGO, MINUTOS_VIGENCIA
from app.core.roles import ROL_ADMIN_PRINCIPAL, ROL_ADMIN_SECUNDARIO, ROL_OPERADOR
from app.core.seguridad import verificar_contrasena
from app.models import Operador, RecuperacionContrasena, Rol
from app.services.operadores import ErrorDeOperadores, OperadorInexistente, SinPermiso
from app.services.recuperacion import generar_codigo_recuperacion


def _operador(db, numero, nombre_rol, activo=True):
    rol = db.scalar(select(Rol).where(Rol.nombre == nombre_rol))
    nuevo = Operador(numero_operador=numero, contrasena_hash="hash-de-prueba", rol_id=rol.id, activo=activo)
    db.add(nuevo)
    db.flush()
    return nuevo


def _contar(db):
    return db.scalar(select(func.count()).select_from(RecuperacionContrasena))


def test_principal_genera_codigo_para_un_operador(db_pg):
    principal = _operador(db_pg, "T-P1", ROL_ADMIN_PRINCIPAL)
    destino = _operador(db_pg, "T-O1", ROL_OPERADOR)

    codigo, vence = generar_codigo_recuperacion(db_pg, principal, destino.id)

    assert len(codigo) == LARGO_CODIGO
    registro = db_pg.scalar(select(RecuperacionContrasena).where(RecuperacionContrasena.operador_id == destino.id))
    assert registro.generado_por_id == principal.id
    assert registro.usado is None
    assert registro.vence == vence
    assert registro.vence - registro.creado == timedelta(minutes=MINUTOS_VIGENCIA)
    # Solo se guarda el hash: el código en claro no está en la base.
    assert registro.codigo_hash != codigo
    assert verificar_contrasena(codigo, registro.codigo_hash)


def test_secundario_genera_codigo_para_un_operador(db_pg):
    secundario = _operador(db_pg, "T-S1", ROL_ADMIN_SECUNDARIO)
    destino = _operador(db_pg, "T-O1", ROL_OPERADOR)
    codigo, _ = generar_codigo_recuperacion(db_pg, secundario, destino.id)
    assert len(codigo) == LARGO_CODIGO


def test_principal_genera_codigo_para_otro_principal(db_pg):
    uno = _operador(db_pg, "T-P1", ROL_ADMIN_PRINCIPAL)
    otro = _operador(db_pg, "T-P2", ROL_ADMIN_PRINCIPAL)
    codigo, _ = generar_codigo_recuperacion(db_pg, uno, otro.id)
    assert len(codigo) == LARGO_CODIGO


def test_secundario_no_genera_codigo_para_un_administrador(db_pg):
    secundario = _operador(db_pg, "T-S1", ROL_ADMIN_SECUNDARIO)
    principal = _operador(db_pg, "T-P1", ROL_ADMIN_PRINCIPAL)
    antes = _contar(db_pg)
    with pytest.raises(SinPermiso):
        generar_codigo_recuperacion(db_pg, secundario, principal.id)
    assert _contar(db_pg) == antes


def test_no_puede_generarse_un_codigo_a_si_mismo(db_pg):
    principal = _operador(db_pg, "T-P1", ROL_ADMIN_PRINCIPAL)
    antes = _contar(db_pg)
    with pytest.raises(ErrorDeOperadores, match="sí mismo"):
        generar_codigo_recuperacion(db_pg, principal, principal.id)
    assert _contar(db_pg) == antes


def test_operador_inexistente(db_pg):
    principal = _operador(db_pg, "T-P1", ROL_ADMIN_PRINCIPAL)
    with pytest.raises(OperadorInexistente):
        generar_codigo_recuperacion(db_pg, principal, 999999)


def test_operador_dado_de_baja_no_recibe_codigo(db_pg):
    principal = _operador(db_pg, "T-P1", ROL_ADMIN_PRINCIPAL)
    de_baja = _operador(db_pg, "T-O1", ROL_OPERADOR, activo=False)
    antes = _contar(db_pg)
    with pytest.raises(ErrorDeOperadores, match="baja"):
        generar_codigo_recuperacion(db_pg, principal, de_baja.id)
    assert _contar(db_pg) == antes


def test_un_codigo_nuevo_no_borra_el_anterior(db_pg):
    principal = _operador(db_pg, "T-P1", ROL_ADMIN_PRINCIPAL)
    destino = _operador(db_pg, "T-O1", ROL_OPERADOR)
    generar_codigo_recuperacion(db_pg, principal, destino.id)
    generar_codigo_recuperacion(db_pg, principal, destino.id)
    cantidad = db_pg.scalar(
        select(func.count()).select_from(RecuperacionContrasena).where(RecuperacionContrasena.operador_id == destino.id)
    )
    assert cantidad == 2
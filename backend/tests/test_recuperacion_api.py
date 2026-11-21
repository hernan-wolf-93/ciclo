"""Recuperación de contraseña: API contra PostgreSQL (ciclo_test)."""

from sqlalchemy import select

from app.core.codigo_recuperacion import LARGO_CODIGO
from app.core.roles import ROL_ADMIN_PRINCIPAL, ROL_ADMIN_SECUNDARIO, ROL_OPERADOR
from app.core.seguridad import crear_token, verificar_contrasena
from app.models import Operador, Rol
from app.services.recuperacion import MENSAJE_CODIGO_INVALIDO

CLAVE_NUEVA = "clave-nueva-1"


def _auth(operador):
    return {"Authorization": f"Bearer {crear_token(operador.id)}"}


def _operador(db, numero, nombre_rol, activo=True):
    rol = db.scalar(select(Rol).where(Rol.nombre == nombre_rol))
    nuevo = Operador(numero_operador=numero, contrasena_hash="hash-de-prueba", rol_id=rol.id, activo=activo)
    db.add(nuevo)
    db.flush()
    return nuevo


def _generar(cliente, actor, destino_id):
    return cliente.post(f"/operadores/{destino_id}/codigo-recuperacion", headers=_auth(actor))


def _recuperar(cliente, numero, codigo, clave=CLAVE_NUEVA):
    return cliente.post(
        "/auth/recuperar-contrasena",
        json={"numero_operador": numero, "codigo": codigo, "contrasena_nueva": clave},
    )


# --- Generar el código (administradores) -----------------------------------

def test_generar_sin_token_responde_401(cliente_pg, db_pg):
    destino = _operador(db_pg, "T-O1", ROL_OPERADOR)
    r = cliente_pg.post(f"/operadores/{destino.id}/codigo-recuperacion")
    assert r.status_code == 401


def test_un_operador_comun_no_puede_generar_codigos(cliente_pg, db_pg):
    comun = _operador(db_pg, "T-O1", ROL_OPERADOR)
    otro = _operador(db_pg, "T-O2", ROL_OPERADOR)
    assert _generar(cliente_pg, comun, otro.id).status_code == 403


def test_principal_genera_el_codigo_y_responde_201(cliente_pg, db_pg):
    principal = _operador(db_pg, "T-P1", ROL_ADMIN_PRINCIPAL)
    destino = _operador(db_pg, "T-O1", ROL_OPERADOR)
    r = _generar(cliente_pg, principal, destino.id)
    assert r.status_code == 201
    assert len(r.json()["codigo"]) == LARGO_CODIGO
    assert r.json()["vence"]
    assert r.headers["cache-control"] == "no-store"


def test_secundario_no_genera_codigo_para_un_administrador(cliente_pg, db_pg):
    secundario = _operador(db_pg, "T-S1", ROL_ADMIN_SECUNDARIO)
    principal = _operador(db_pg, "T-P1", ROL_ADMIN_PRINCIPAL)
    assert _generar(cliente_pg, secundario, principal.id).status_code == 403


def test_no_puede_generarse_un_codigo_a_si_mismo(cliente_pg, db_pg):
    principal = _operador(db_pg, "T-P1", ROL_ADMIN_PRINCIPAL)
    r = _generar(cliente_pg, principal, principal.id)
    assert r.status_code == 422
    assert "sí mismo" in r.json()["detail"]


def test_generar_para_un_operador_inexistente_responde_404(cliente_pg, db_pg):
    principal = _operador(db_pg, "T-P1", ROL_ADMIN_PRINCIPAL)
    assert _generar(cliente_pg, principal, 999999).status_code == 404


def test_generar_para_un_operador_de_baja_responde_422(cliente_pg, db_pg):
    principal = _operador(db_pg, "T-P1", ROL_ADMIN_PRINCIPAL)
    de_baja = _operador(db_pg, "T-O1", ROL_OPERADOR, activo=False)
    assert _generar(cliente_pg, principal, de_baja.id).status_code == 422


# --- Restablecer la contraseña (público) -----------------------------------

def test_circuito_completo_y_login_con_la_clave_nueva(cliente_pg, db_pg):
    principal = _operador(db_pg, "T-P1", ROL_ADMIN_PRINCIPAL)
    destino = _operador(db_pg, "T-O1", ROL_OPERADOR)
    codigo = _generar(cliente_pg, principal, destino.id).json()["codigo"]

    r = _recuperar(cliente_pg, destino.numero_operador, codigo)
    assert r.status_code == 204
    assert r.content == b""

    login = cliente_pg.post(
        "/auth/login", json={"numero_operador": destino.numero_operador, "contrasena": CLAVE_NUEVA}
    )
    assert login.status_code == 200
    assert login.json()["access_token"]


def test_codigo_incorrecto_responde_400_con_mensaje_unico(cliente_pg, db_pg):
    principal = _operador(db_pg, "T-P1", ROL_ADMIN_PRINCIPAL)
    destino = _operador(db_pg, "T-O1", ROL_OPERADOR)
    _generar(cliente_pg, principal, destino.id)
    r = _recuperar(cliente_pg, destino.numero_operador, "ZZZZZZZZ")
    assert r.status_code == 400
    assert r.json()["detail"] == MENSAJE_CODIGO_INVALIDO


def test_el_codigo_no_se_puede_usar_dos_veces(cliente_pg, db_pg):
    principal = _operador(db_pg, "T-P1", ROL_ADMIN_PRINCIPAL)
    destino = _operador(db_pg, "T-O1", ROL_OPERADOR)
    codigo = _generar(cliente_pg, principal, destino.id).json()["codigo"]
    assert _recuperar(cliente_pg, destino.numero_operador, codigo).status_code == 204
    assert _recuperar(cliente_pg, destino.numero_operador, codigo, "otra-clave-2").status_code == 400


def test_numero_inexistente_da_el_mismo_mensaje(cliente_pg, db_pg):
    r = _recuperar(cliente_pg, "NO-EXISTE", "ABCD2345")
    assert r.status_code == 400
    assert r.json()["detail"] == MENSAJE_CODIGO_INVALIDO


def test_contrasena_corta_responde_422_y_no_gasta_el_codigo(cliente_pg, db_pg):
    principal = _operador(db_pg, "T-P1", ROL_ADMIN_PRINCIPAL)
    destino = _operador(db_pg, "T-O1", ROL_OPERADOR)
    codigo = _generar(cliente_pg, principal, destino.id).json()["codigo"]

    assert _recuperar(cliente_pg, destino.numero_operador, codigo, "corta").status_code == 422
    db_pg.refresh(destino)
    assert destino.contrasena_hash == "hash-de-prueba"
    # El pedido inválido no consumió el código: sigue sirviendo.
    assert _recuperar(cliente_pg, destino.numero_operador, codigo).status_code == 204
    db_pg.refresh(destino)
    assert verificar_contrasena(CLAVE_NUEVA, destino.contrasena_hash)
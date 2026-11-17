import pytest
from sqlalchemy import func, select

from app.core.roles import ROL_ADMIN_PRINCIPAL, ROL_ADMIN_SECUNDARIO, ROL_OPERADOR
from app.core.seguridad import crear_token, verificar_contrasena
from app.models import Operador
from app.schemas.operador import OperadorAltaIn
from app.services.operadores import (
    NumeroDuplicado,
    dar_de_alta_operador,
    roles_que_puede_asignar,
)

PRINCIPAL, SECUNDARIO, OPERADOR = 1, 2, 3
NOMBRE_DE_ROL = {PRINCIPAL: ROL_ADMIN_PRINCIPAL, SECUNDARIO: ROL_ADMIN_SECUNDARIO, OPERADOR: ROL_OPERADOR}
CONTRASENA = "clave-segura-1"


def _auth(operador):
    return {"Authorization": f"Bearer {crear_token(operador.id)}"}


def _cuerpo(**cambios):
    base = {"numero_operador": "1001", "contrasena": CONTRASENA, "rol_id": OPERADOR}
    base.update(cambios)
    return base


def _contar(db):
    return db.scalar(select(func.count()).select_from(Operador))


def test_sin_token_responde_401(cliente):
    assert cliente.post("/operadores", json=_cuerpo()).status_code == 401


def test_un_operador_no_puede_dar_altas(cliente, crear_operador):
    agente = crear_operador(rol_id=OPERADOR)
    assert cliente.post("/operadores", json=_cuerpo(), headers=_auth(agente)).status_code == 403


@pytest.mark.parametrize("rol_id", [PRINCIPAL, SECUNDARIO, OPERADOR], ids=["principal", "secundario", "operador"])
def test_el_principal_puede_crear_cualquier_rol(cliente, crear_operador, rol_id):
    admin = crear_operador(rol_id=PRINCIPAL)
    r = cliente.post("/operadores", json=_cuerpo(rol_id=rol_id), headers=_auth(admin))
    assert r.status_code == 201
    cuerpo = r.json()
    assert cuerpo["numero_operador"] == "1001"
    assert cuerpo["rol"] == NOMBRE_DE_ROL[rol_id]
    assert cuerpo["activo"] is True


def test_el_secundario_puede_crear_operadores(cliente, crear_operador):
    admin = crear_operador(rol_id=SECUNDARIO)
    r = cliente.post("/operadores", json=_cuerpo(), headers=_auth(admin))
    assert r.status_code == 201
    assert r.json()["rol"] == ROL_OPERADOR


@pytest.mark.parametrize("rol_id", [PRINCIPAL, SECUNDARIO], ids=["principal", "secundario"])
def test_el_secundario_no_puede_crear_administradores(cliente, db, crear_operador, rol_id):
    admin = crear_operador(rol_id=SECUNDARIO)
    antes = _contar(db)
    r = cliente.post("/operadores", json=_cuerpo(rol_id=rol_id), headers=_auth(admin))
    assert r.status_code == 403
    assert _contar(db) == antes


def test_numero_duplicado_responde_409_y_no_guarda(cliente, db, crear_operador):
    admin = crear_operador(numero="9001", rol_id=PRINCIPAL)
    crear_operador(numero="1001", rol_id=OPERADOR)
    antes = _contar(db)
    r = cliente.post("/operadores", json=_cuerpo(numero_operador="1001"), headers=_auth(admin))
    assert r.status_code == 409
    assert _contar(db) == antes


def test_rol_inexistente_responde_422(cliente, db, crear_operador):
    admin = crear_operador(rol_id=PRINCIPAL)
    antes = _contar(db)
    r = cliente.post("/operadores", json=_cuerpo(rol_id=999), headers=_auth(admin))
    assert r.status_code == 422
    assert "rol" in r.json()["detail"]
    assert _contar(db) == antes


@pytest.mark.parametrize(
    "cambios",
    [
        {"contrasena": "corta12"},
        {"numero_operador": "10 01"},
        {"numero_operador": ""},
        {"numero_operador": "1" * 21},
        {"rol_id": "no-es-numero"},
    ],
    ids=["contraseña corta", "número con espacio", "número vacío", "número de 21 caracteres", "rol que no es número"],
)
def test_cuerpo_invalido_responde_422_y_no_guarda(cliente, db, crear_operador, cambios):
    admin = crear_operador(rol_id=PRINCIPAL)
    antes = _contar(db)
    r = cliente.post("/operadores", json=_cuerpo(**cambios), headers=_auth(admin))
    assert r.status_code == 422
    assert _contar(db) == antes


def test_contrasena_de_8_caracteres_es_valida(cliente, crear_operador):
    admin = crear_operador(rol_id=PRINCIPAL)
    r = cliente.post("/operadores", json=_cuerpo(contrasena="12345678"), headers=_auth(admin))
    assert r.status_code == 201


def test_la_contrasena_se_guarda_hasheada_y_no_se_devuelve(cliente, db, crear_operador):
    admin = crear_operador(rol_id=PRINCIPAL)
    r = cliente.post("/operadores", json=_cuerpo(), headers=_auth(admin))
    guardado = db.scalar(select(Operador).where(Operador.numero_operador == "1001"))
    assert guardado.contrasena_hash != CONTRASENA
    assert verificar_contrasena(CONTRASENA, guardado.contrasena_hash)
    assert "contrasena" not in r.json()
    assert "contrasena_hash" not in r.json()


def test_el_operador_creado_puede_ingresar(cliente, crear_operador):
    admin = crear_operador(rol_id=PRINCIPAL)
    cliente.post("/operadores", json=_cuerpo(), headers=_auth(admin))
    r = cliente.post("/auth/login", json={"numero_operador": "1001", "contrasena": CONTRASENA})
    assert r.status_code == 200
    assert "access_token" in r.json()


def test_alta_simultanea_se_resuelve_como_duplicado(db, crear_operador, monkeypatch):
    actor = crear_operador(numero="9001", rol_id=PRINCIPAL)
    crear_operador(numero="500", rol_id=OPERADOR)
    # La consulta previa "no ve" el duplicado; la segunda, tras el error, sí.
    respuestas = iter([False, True])
    monkeypatch.setattr("app.services.operadores._numero_existe", lambda _db, _numero: next(respuestas))
    datos = OperadorAltaIn(numero_operador="500", contrasena=CONTRASENA, rol_id=OPERADOR)
    with pytest.raises(NumeroDuplicado):
        dar_de_alta_operador(db, actor, datos)

@pytest.mark.parametrize(
    "rol_id, esperados",
    [
        (PRINCIPAL, {ROL_ADMIN_PRINCIPAL, ROL_ADMIN_SECUNDARIO, ROL_OPERADOR}),
        (SECUNDARIO, {ROL_OPERADOR}),
        (OPERADOR, set()),
    ],
    ids=["principal", "secundario", "operador"],
)
def test_roles_que_puede_asignar(crear_operador, rol_id, esperados):
    assert set(roles_que_puede_asignar(crear_operador(rol_id=rol_id))) == esperados
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.api.deps import exigir_administrador, obtener_db, requerir_roles
from app.core.roles import ROL_ADMIN_PRINCIPAL
from app.core.seguridad import crear_token

# Ids de rol en la base de prueba de SQLite (el 2 lo agrega el fixture de abajo).
PRINCIPAL, SECUNDARIO, OPERADOR = 1, 2, 3

@pytest.fixture
def cliente_roles(db):
    """App mínima con dos rutas protegidas, para probar la dependencia sola."""
    app = FastAPI()

    @app.get("/administradores")
    def administradores(_=Depends(exigir_administrador)):
        return {"ok": True}

    @app.get("/solo-principal")
    def solo_principal(_=Depends(requerir_roles(ROL_ADMIN_PRINCIPAL))):
        return {"ok": True}

    def _db_de_prueba():
        yield db

    app.dependency_overrides[obtener_db] = _db_de_prueba
    with TestClient(app) as c:
        yield c


def _auth(operador):
    return {"Authorization": f"Bearer {crear_token(operador.id)}"}


@pytest.mark.parametrize(
    "rol_id, ruta, esperado",
    [
        (PRINCIPAL, "/solo-principal", 200),
        (PRINCIPAL, "/administradores", 200),
        (SECUNDARIO, "/solo-principal", 403),
        (SECUNDARIO, "/administradores", 200),
        (OPERADOR, "/solo-principal", 403),
        (OPERADOR, "/administradores", 403),
    ],
    ids=[
        "principal en solo-principal",
        "principal en administradores",
        "secundario en solo-principal",
        "secundario en administradores",
        "operador en solo-principal",
        "operador en administradores",
    ],
)
def test_permisos_por_rol(cliente_roles, crear_operador, rol_id, ruta, esperado):
    operador = crear_operador(rol_id=rol_id)
    assert cliente_roles.get(ruta, headers=_auth(operador)).status_code == esperado


def test_sin_token_responde_401_y_no_403(cliente_roles):
    assert cliente_roles.get("/administradores").status_code == 401


def test_403_trae_un_mensaje_claro(cliente_roles, crear_operador):
    r = cliente_roles.get("/administradores", headers=_auth(crear_operador(rol_id=OPERADOR)))
    assert r.status_code == 403
    assert "permiso" in r.json()["detail"]


def test_operador_dado_de_baja_responde_401(cliente_roles, crear_operador, db):
    operador = crear_operador(rol_id=PRINCIPAL)
    headers = _auth(operador)
    operador.activo = False
    db.commit()
    assert cliente_roles.get("/administradores", headers=headers).status_code == 401


def test_el_cambio_de_rol_vale_de_inmediato(cliente_roles, crear_operador, db):
    operador = crear_operador(rol_id=SECUNDARIO)
    headers = _auth(operador)
    assert cliente_roles.get("/administradores", headers=headers).status_code == 200
    operador.rol_id = OPERADOR
    db.commit()
    assert cliente_roles.get("/administradores", headers=headers).status_code == 403
    
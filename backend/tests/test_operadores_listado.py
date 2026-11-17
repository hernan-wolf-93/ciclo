import pytest

from app.core.roles import ROL_ADMIN_PRINCIPAL, ROL_ADMIN_SECUNDARIO, ROL_OPERADOR
from app.core.seguridad import crear_token
from app.models import Rol

PRINCIPAL, SECUNDARIO, OPERADOR = 1, 2, 3


@pytest.fixture(autouse=True)
def _rol_secundario(db):
    """La base de prueba trae los roles 1 y 3: se agrega el 2 para todo este archivo."""
    db.add(Rol(id=SECUNDARIO, nombre=ROL_ADMIN_SECUNDARIO))
    db.commit()


def _auth(operador):
    return {"Authorization": f"Bearer {crear_token(operador.id)}"}


@pytest.fixture
def operadores_de_prueba(crear_operador):
    """Un principal, un operador activo y un operador dado de baja."""
    return (
        crear_operador(numero="9001", rol_id=PRINCIPAL),
        crear_operador(numero="9002", rol_id=OPERADOR),
        crear_operador(numero="9003", rol_id=OPERADOR, activo=False),
    )


def test_listado_sin_token_responde_401(cliente):
    assert cliente.get("/operadores").status_code == 401


def test_un_operador_no_puede_ver_el_listado(cliente, crear_operador):
    agente = crear_operador(rol_id=OPERADOR)
    assert cliente.get("/operadores", headers=_auth(agente)).status_code == 403


def test_el_principal_ve_a_todos_ordenados_por_id(cliente, operadores_de_prueba):
    r = cliente.get("/operadores", headers=_auth(operadores_de_prueba[0]))
    assert r.status_code == 200
    assert [o["numero_operador"] for o in r.json()] == ["9001", "9002", "9003"]
    assert [o["rol"] for o in r.json()] == [ROL_ADMIN_PRINCIPAL, ROL_OPERADOR, ROL_OPERADOR]
    assert [o["activo"] for o in r.json()] == [True, True, False]


def test_el_secundario_tambien_ve_el_listado(cliente, crear_operador, operadores_de_prueba):
    secundario = crear_operador(numero="9004", rol_id=SECUNDARIO)
    r = cliente.get("/operadores", headers=_auth(secundario))
    assert r.status_code == 200
    assert "9001" in [o["numero_operador"] for o in r.json()]  # ve también a los administradores


@pytest.mark.parametrize(
    "valor, esperados",
    [("true", ["9001", "9002"]), ("false", ["9003"])],
    ids=["solo activos", "solo dados de baja"],
)
def test_filtro_por_estado(cliente, operadores_de_prueba, valor, esperados):
    r = cliente.get(f"/operadores?activo={valor}", headers=_auth(operadores_de_prueba[0]))
    assert [o["numero_operador"] for o in r.json()] == esperados


def test_el_listado_no_expone_contrasenas(cliente, operadores_de_prueba):
    r = cliente.get("/operadores", headers=_auth(operadores_de_prueba[0]))
    assert all(set(o) == {"id", "numero_operador", "rol", "activo"} for o in r.json())


def test_roles_sin_token_responde_401(cliente):
    assert cliente.get("/roles").status_code == 401


def test_un_operador_no_puede_pedir_roles_asignables(cliente, crear_operador):
    agente = crear_operador(rol_id=OPERADOR)
    assert cliente.get("/roles", headers=_auth(agente)).status_code == 403


def test_el_principal_puede_asignar_los_tres_roles(cliente, crear_operador):
    principal = crear_operador(rol_id=PRINCIPAL)
    r = cliente.get("/roles", headers=_auth(principal))
    assert r.status_code == 200
    assert [x["nombre"] for x in r.json()] == [ROL_ADMIN_PRINCIPAL, ROL_ADMIN_SECUNDARIO, ROL_OPERADOR]


def test_el_secundario_solo_puede_asignar_operador(cliente, crear_operador):
    secundario = crear_operador(rol_id=SECUNDARIO)
    r = cliente.get("/roles", headers=_auth(secundario))
    assert r.status_code == 200
    assert r.json() == [{"id": OPERADOR, "nombre": ROL_OPERADOR}]
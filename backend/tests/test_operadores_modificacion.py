import pytest

from app.core.roles import ROL_ADMIN_SECUNDARIO
from app.core.seguridad import crear_token

PRINCIPAL, SECUNDARIO, OPERADOR = 1, 2, 3


def _auth(operador):
    return {"Authorization": f"Bearer {crear_token(operador.id)}"}


def _patch(cliente, actor, operador_id, cuerpo):
    return cliente.patch(f"/operadores/{operador_id}", json=cuerpo, headers=_auth(actor))


def test_sin_token_responde_401(cliente):
    assert cliente.patch("/operadores/1", json={"activo": False}).status_code == 401


def test_un_operador_no_puede_modificar(cliente, crear_operador):
    agente = crear_operador(numero="9001", rol_id=OPERADOR)
    assert _patch(cliente, agente, agente.id, {"activo": False}).status_code == 403


def test_sin_cambios_responde_422(cliente, crear_operador):
    principal = crear_operador(numero="9001", rol_id=PRINCIPAL)
    assert _patch(cliente, principal, principal.id, {}).status_code == 422


def test_el_numero_de_operador_no_se_puede_modificar(cliente, db, crear_operador):
    principal = crear_operador(numero="9001", rol_id=PRINCIPAL)
    objetivo = crear_operador(numero="9002", rol_id=OPERADOR)
    r = _patch(cliente, principal, objetivo.id, {"activo": True, "numero_operador": "5555"})
    assert r.status_code == 422
    db.refresh(objetivo)
    assert objetivo.numero_operador == "9002"


def test_operador_inexistente_responde_404(cliente, crear_operador):
    principal = crear_operador(numero="9001", rol_id=PRINCIPAL)
    assert _patch(cliente, principal, 999999, {"activo": False}).status_code == 404


def test_el_secundario_puede_dar_de_baja_a_un_operador(cliente, db, crear_operador):
    secundario = crear_operador(numero="9001", rol_id=SECUNDARIO)
    agente = crear_operador(numero="9002", rol_id=OPERADOR)
    r = _patch(cliente, secundario, agente.id, {"activo": False})
    assert r.status_code == 200
    assert r.json()["activo"] is False
    db.refresh(agente)
    assert agente.activo is False


def test_la_baja_vale_de_inmediato(cliente, crear_operador):
    secundario = crear_operador(numero="9001", rol_id=SECUNDARIO)
    agente = crear_operador(numero="9002", rol_id=OPERADOR)
    headers = _auth(agente)
    assert cliente.get("/auth/me", headers=headers).status_code == 200
    _patch(cliente, secundario, agente.id, {"activo": False})
    assert cliente.get("/auth/me", headers=headers).status_code == 401


def test_se_puede_reactivar_un_operador(cliente, crear_operador):
    principal = crear_operador(numero="9001", rol_id=PRINCIPAL)
    agente = crear_operador(numero="9002", rol_id=OPERADOR, activo=False)
    r = _patch(cliente, principal, agente.id, {"activo": True})
    assert r.status_code == 200
    assert r.json()["activo"] is True


def test_el_principal_puede_cambiar_el_rol_de_un_operador(cliente, crear_operador):
    principal = crear_operador(numero="9001", rol_id=PRINCIPAL)
    agente = crear_operador(numero="9002", rol_id=OPERADOR)
    r = _patch(cliente, principal, agente.id, {"rol_id": SECUNDARIO})
    assert r.status_code == 200
    assert r.json()["rol"] == ROL_ADMIN_SECUNDARIO


@pytest.mark.parametrize("rol_id", [PRINCIPAL, SECUNDARIO], ids=["principal", "secundario"])
def test_el_secundario_no_puede_asignar_roles_de_administrador(cliente, db, crear_operador, rol_id):
    secundario = crear_operador(numero="9001", rol_id=SECUNDARIO)
    agente = crear_operador(numero="9002", rol_id=OPERADOR)
    assert _patch(cliente, secundario, agente.id, {"rol_id": rol_id}).status_code == 403
    db.refresh(agente)
    assert agente.rol_id == OPERADOR


@pytest.mark.parametrize("rol_id", [PRINCIPAL, SECUNDARIO], ids=["principal", "secundario"])
def test_el_secundario_no_puede_modificar_administradores(cliente, db, crear_operador, rol_id):
    secundario = crear_operador(numero="9001", rol_id=SECUNDARIO)
    administrador = crear_operador(numero="9002", rol_id=rol_id)
    assert _patch(cliente, secundario, administrador.id, {"activo": False}).status_code == 403
    db.refresh(administrador)
    assert administrador.activo is True


@pytest.mark.parametrize("rol_id", [SECUNDARIO, OPERADOR], ids=["secundario", "operador"])
def test_el_principal_puede_modificar_a_cualquiera(cliente, crear_operador, rol_id):
    principal = crear_operador(numero="9001", rol_id=PRINCIPAL)
    objetivo = crear_operador(numero="9002", rol_id=rol_id)
    assert _patch(cliente, principal, objetivo.id, {"activo": False}).status_code == 200


def test_rol_inexistente_responde_422(cliente, crear_operador):
    principal = crear_operador(numero="9001", rol_id=PRINCIPAL)
    agente = crear_operador(numero="9002", rol_id=OPERADOR)
    r = _patch(cliente, principal, agente.id, {"rol_id": 999})
    assert r.status_code == 422
    assert "rol" in r.json()["detail"]


def test_nadie_puede_darse_de_baja_a_si_mismo(cliente, db, crear_operador):
    principal = crear_operador(numero="9001", rol_id=PRINCIPAL)
    crear_operador(numero="9002", rol_id=PRINCIPAL)  # hay otro: la regla que frena es la de baja propia
    r = _patch(cliente, principal, principal.id, {"activo": False})
    assert r.status_code == 422
    assert "sí mismo" in r.json()["detail"]
    db.refresh(principal)
    assert principal.activo is True


def test_el_unico_principal_no_puede_degradarse(cliente, db, crear_operador):
    principal = crear_operador(numero="9001", rol_id=PRINCIPAL)
    r = _patch(cliente, principal, principal.id, {"rol_id": SECUNDARIO})
    assert r.status_code == 422
    assert "administrador principal" in r.json()["detail"]
    db.refresh(principal)
    assert principal.rol_id == PRINCIPAL


def test_un_principal_puede_degradarse_si_hay_otro(cliente, crear_operador):
    principal = crear_operador(numero="9001", rol_id=PRINCIPAL)
    crear_operador(numero="9002", rol_id=PRINCIPAL)
    r = _patch(cliente, principal, principal.id, {"rol_id": SECUNDARIO})
    assert r.status_code == 200
    assert r.json()["rol"] == ROL_ADMIN_SECUNDARIO


def test_un_principal_puede_dar_de_baja_a_otro_principal(cliente, crear_operador):
    principal = crear_operador(numero="9001", rol_id=PRINCIPAL)
    otro = crear_operador(numero="9002", rol_id=PRINCIPAL)
    assert _patch(cliente, principal, otro.id, {"activo": False}).status_code == 200
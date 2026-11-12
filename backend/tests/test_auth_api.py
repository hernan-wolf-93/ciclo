from app.core import seguridad
from app.core.config import settings


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _login(cliente, numero, contrasena):
    return cliente.post(
        "/auth/login", json={"numero_operador": numero, "contrasena": contrasena}
    )


# --- POST /auth/login ---


def test_login_correcto_devuelve_un_token_del_operador(cliente, crear_operador, contrasena):
    operador = crear_operador()
    r = _login(cliente, "9001", contrasena)
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["token_type"] == "bearer"
    assert seguridad.leer_token(cuerpo["access_token"]) == operador.id


def test_login_con_contrasena_incorrecta_da_401(cliente, crear_operador):
    crear_operador()
    assert _login(cliente, "9001", "otra-clave").status_code == 401


def test_login_no_revela_si_el_numero_existe(cliente, crear_operador, contrasena):
    crear_operador()
    contrasena_mala = _login(cliente, "9001", "otra-clave")
    numero_inexistente = _login(cliente, "9999", contrasena)
    assert contrasena_mala.status_code == numero_inexistente.status_code == 401
    assert contrasena_mala.json() == numero_inexistente.json()


def test_login_de_operador_dado_de_baja_da_el_mismo_401(cliente, crear_operador, contrasena):
    crear_operador(activo=False)
    esperado = _login(cliente, "9999", contrasena)
    r = _login(cliente, "9001", contrasena)
    assert r.status_code == 401
    assert r.json() == esperado.json()


def test_login_con_cuerpo_incompleto_da_422(cliente):
    r = cliente.post("/auth/login", json={"numero_operador": "9001"})
    assert r.status_code == 422


# --- GET /auth/me ---


def test_me_sin_token_da_401(cliente):
    assert cliente.get("/auth/me").status_code == 401


def test_me_con_token_valido_devuelve_el_operador_sin_datos_sensibles(cliente, crear_operador):
    operador = crear_operador()
    r = cliente.get("/auth/me", headers=_auth(seguridad.crear_token(operador.id)))
    assert r.status_code == 200
    # La comparación exacta también comprueba que no se devuelve el hash.
    assert r.json() == {
        "id": operador.id,
        "numero_operador": "9001",
        "rol": "Administrador principal",
    }


def test_me_con_token_alterado_da_401(cliente, crear_operador):
    operador = crear_operador()
    token = seguridad.crear_token(operador.id)
    assert cliente.get("/auth/me", headers=_auth(token + "x")).status_code == 401


def test_me_con_token_vencido_da_401(cliente, crear_operador, monkeypatch):
    operador = crear_operador()
    monkeypatch.setattr(settings, "access_token_expire_minutes", -1)
    token = seguridad.crear_token(operador.id)
    assert cliente.get("/auth/me", headers=_auth(token)).status_code == 401


def test_me_con_esquema_distinto_de_bearer_da_401(cliente):
    r = cliente.get("/auth/me", headers={"Authorization": "Basic abc"})
    assert r.status_code == 401


def test_me_con_token_de_un_operador_que_no_existe_da_401(cliente):
    token = seguridad.crear_token(999)
    assert cliente.get("/auth/me", headers=_auth(token)).status_code == 401


def test_la_baja_vale_de_inmediato_con_el_mismo_token(cliente, db, crear_operador):
    operador = crear_operador()
    token = seguridad.crear_token(operador.id)
    assert cliente.get("/auth/me", headers=_auth(token)).status_code == 200

    operador.activo = False
    db.commit()

    assert cliente.get("/auth/me", headers=_auth(token)).status_code == 401


def test_flujo_completo_login_y_me(cliente, crear_operador, contrasena):
    crear_operador(numero="9003", rol_id=3)
    token = _login(cliente, "9003", contrasena).json()["access_token"]
    r = cliente.get("/auth/me", headers=_auth(token))
    assert r.status_code == 200
    assert r.json()["numero_operador"] == "9003"
    assert r.json()["rol"] == "Operador"
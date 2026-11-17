"""Pruebas de CORS: el navegador solo puede usar la API desde los orígenes permitidos."""

from app.core.config import Settings

ORIGEN_PERMITIDO = "http://localhost:5173"
ORIGEN_AJENO = "http://sitio-ajeno.example"


def _preflight(cliente, origen, cabeceras="authorization,content-type"):
    return cliente.options(
        "/auth/login",
        headers={
            "Origin": origen,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": cabeceras,
        },
    )


def test_preflight_de_origen_permitido(cliente):
    r = _preflight(cliente, ORIGEN_PERMITIDO)
    assert r.status_code == 200
    assert r.headers["access-control-allow-origin"] == ORIGEN_PERMITIDO


def test_preflight_de_origen_ajeno_se_rechaza(cliente):
    r = _preflight(cliente, ORIGEN_AJENO)
    assert r.status_code == 400
    assert "access-control-allow-origin" not in r.headers


def test_patch_esta_permitido(cliente):
    """PATCH lo usa el ABM de operadores y dispara el preflight."""
    r = cliente.options(
        "/operadores/1",
        headers={
            "Origin": ORIGEN_PERMITIDO,
            "Access-Control-Request-Method": "PATCH",
        },
    )
    assert r.status_code == 200


def test_delete_no_esta_permitido(cliente):
    """La API no usa DELETE (las bajas son lógicas): el preflight debe fallar."""
    r = cliente.options(
        "/operadores/1",
        headers={
            "Origin": ORIGEN_PERMITIDO,
            "Access-Control-Request-Method": "DELETE",
        },
    )
    assert r.status_code == 400


def test_respuesta_normal_lleva_la_cabecera(cliente):
    r = cliente.get("/salud", headers={"Origin": ORIGEN_PERMITIDO})
    assert r.status_code == 200
    assert r.headers["access-control-allow-origin"] == ORIGEN_PERMITIDO


def test_origenes_se_leen_separados_por_coma():
    s = Settings(
        database_url="postgresql+psycopg://x:y@localhost/x",
        secret_key="a" * 32,
        cors_origins=" http://a:1 , http://b:2 ,, ",
    )
    assert s.origenes_cors == ["http://a:1", "http://b:2"]
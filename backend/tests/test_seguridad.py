from datetime import datetime, timedelta, timezone

import jwt

from app.core import seguridad
from app.core.config import settings


def test_contrasena_correcta_verifica_e_incorrecta_no():
    hash_ = seguridad.hashear_contrasena("clave-de-prueba-1")
    assert seguridad.verificar_contrasena("clave-de-prueba-1", hash_)
    assert not seguridad.verificar_contrasena("otra-clave", hash_)


def test_el_hash_no_contiene_la_contrasena():
    hash_ = seguridad.hashear_contrasena("clave-de-prueba-1")
    assert hash_.startswith("$argon2id$")
    assert "clave-de-prueba-1" not in hash_


def test_la_misma_contrasena_da_hashes_distintos():
    # Cada hash lleva una sal aleatoria propia.
    assert seguridad.hashear_contrasena("x") != seguridad.hashear_contrasena("x")


def test_token_valido_devuelve_el_id_del_operador():
    assert seguridad.leer_token(seguridad.crear_token(7)) == 7


def test_token_alterado_se_rechaza():
    token = seguridad.crear_token(7)
    assert seguridad.leer_token(token + "x") is None
    assert seguridad.leer_token("no-es-un-token") is None


def test_token_firmado_con_otra_clave_se_rechaza():
    ahora = datetime.now(timezone.utc)
    falso = jwt.encode(
        {"sub": "7", "exp": ahora + timedelta(minutes=5)},
        "una-clave-distinta-de-mas-de-32-caracteres",
        algorithm=seguridad.ALGORITMO,
    )
    assert seguridad.leer_token(falso) is None


def test_token_vencido_se_rechaza(monkeypatch):
    # monkeypatch cambia el valor solo durante esta prueba.
    monkeypatch.setattr(settings, "access_token_expire_minutes", -1)
    assert seguridad.leer_token(seguridad.crear_token(7)) is None


def test_token_sin_vencimiento_se_rechaza():
    sin_exp = jwt.encode({"sub": "7"}, settings.secret_key, algorithm=seguridad.ALGORITMO)
    assert seguridad.leer_token(sin_exp) is None
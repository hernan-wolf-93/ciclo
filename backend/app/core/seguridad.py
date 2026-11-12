from datetime import datetime, timedelta, timezone

import jwt
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash

from app.core.config import settings

ALGORITMO = "HS256"

# Argon2 con los parámetros recomendados por la librería.
_hasher = PasswordHash.recommended()


def hashear_contrasena(contrasena: str) -> str:
    """Devuelve el hash de la contraseña. La contraseña original no se guarda."""
    return _hasher.hash(contrasena)


def verificar_contrasena(contrasena: str, contrasena_hash: str) -> bool:
    """Indica si la contraseña corresponde al hash guardado."""
    return _hasher.verify(contrasena, contrasena_hash)


def crear_token(operador_id: int) -> str:
    """Crea un token firmado que identifica al operador y vence a los N minutos."""
    ahora = datetime.now(timezone.utc)
    payload = {
        "sub": str(operador_id),
        "iat": ahora,
        "exp": ahora + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITMO)


def leer_token(token: str) -> int | None:
    """Devuelve el id del operador si el token es válido y no venció; si no, None."""
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[ALGORITMO],
            options={"require": ["exp", "sub"]},
        )
        return int(payload["sub"])
    except (InvalidTokenError, ValueError):
        return None
from collections.abc import Callable, Iterator
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.seguridad import leer_token
from app.core.roles import ROLES_ADMINISTRADORES
from app.models import Operador

# auto_error=False: el error 401 lo armamos nosotros, con un mensaje único.
_esquema_bearer = HTTPBearer(auto_error=False)


def obtener_db() -> Iterator[Session]:
    """Entrega una sesión de base de datos por pedido y la cierra al terminar."""
    with SessionLocal() as db:
        yield db


def obtener_operador_actual(
    credenciales: Annotated[HTTPAuthorizationCredentials | None, Depends(_esquema_bearer)],
    db: Annotated[Session, Depends(obtener_db)],
) -> Operador:
    """Devuelve el operador que hace el pedido, a partir del token.

    Responde 401 si falta el token, es inválido, venció, el operador ya no
    existe o está dado de baja. El mensaje es el mismo en todos los casos.
    """
    no_autorizado = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No autenticado",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credenciales is None:
        raise no_autorizado
    operador_id = leer_token(credenciales.credentials)
    if operador_id is None:
        raise no_autorizado
    operador = db.get(Operador, operador_id)
    if operador is None or not operador.activo:
        raise no_autorizado
    return operador

def requerir_roles(*roles_permitidos: str) -> Callable[..., Operador]:
    """Crea una dependencia que deja pasar solo a los operadores con alguno de esos roles.

    Responde 401 si no hay sesión válida (lo resuelve obtener_operador_actual) y
    403 si hay sesión pero el rol no alcanza. El rol se lee de la base en cada
    pedido, así que un cambio de rol o una baja valen de inmediato.
    """

    def dependencia(
        operador: Annotated[Operador, Depends(obtener_operador_actual)],
    ) -> Operador:
        if operador.rol.nombre not in roles_permitidos:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene permiso para realizar esta acción",
            )
        return operador

    return dependencia


exigir_administrador = requerir_roles(*ROLES_ADMINISTRADORES)
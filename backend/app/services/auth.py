from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.seguridad import hashear_contrasena, verificar_contrasena
from app.models import Operador

# Hash de una contraseña que nadie usa: se verifica cuando el número no existe,
# para que la respuesta tarde lo mismo y no delate qué números están cargados.
_HASH_FALSO = hashear_contrasena("contrasena-que-no-corresponde-a-nadie")


def autenticar(db: Session, numero_operador: str, contrasena: str) -> Operador | None:
    """Devuelve el operador si las credenciales son válidas y está activo; si no, None."""
    operador = db.scalar(
        select(Operador).where(Operador.numero_operador == numero_operador)
    )
    hash_a_comparar = operador.contrasena_hash if operador else _HASH_FALSO
    contrasena_correcta = verificar_contrasena(contrasena, hash_a_comparar)

    if operador is None or not contrasena_correcta or not operador.activo:
        return None
    return operador
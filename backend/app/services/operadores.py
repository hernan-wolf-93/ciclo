"""Gestión de operadores (ABM): reglas de negocio."""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.roles import ROL_ADMIN_PRINCIPAL, ROL_ADMIN_SECUNDARIO, ROL_OPERADOR
from app.core.seguridad import hashear_contrasena
from app.models import Operador, Rol
from app.schemas.operador import OperadorAltaIn


class ErrorDeOperadores(Exception):
    """Una regla de negocio no se cumple. El router la responde como 422."""


class SinPermiso(ErrorDeOperadores):
    """El rol del operador no alcanza para esta acción. El router la responde como 403."""


class NumeroDuplicado(ErrorDeOperadores):
    """Ya existe un operador con ese número. El router la responde como 409."""


def roles_que_puede_asignar(actor: Operador) -> tuple[str, ...]:
    """Tabla de permisos: qué roles puede dar a otros un operador, según el suyo."""
    if actor.rol.nombre == ROL_ADMIN_PRINCIPAL:
        return (ROL_ADMIN_PRINCIPAL, ROL_ADMIN_SECUNDARIO, ROL_OPERADOR)
    if actor.rol.nombre == ROL_ADMIN_SECUNDARIO:
        return (ROL_OPERADOR,)
    return ()


def _numero_existe(db: Session, numero: str) -> bool:
    return db.scalar(select(Operador.id).where(Operador.numero_operador == numero)) is not None


def dar_de_alta_operador(db: Session, actor: Operador, datos: OperadorAltaIn) -> Operador:
    """Crea un operador. Solo guarda el hash de la contraseña."""
    rol = db.get(Rol, datos.rol_id)
    if rol is None:
        raise ErrorDeOperadores("El rol no existe")
    if rol.nombre not in roles_que_puede_asignar(actor):
        raise SinPermiso("No tiene permiso para asignar ese rol")
    if _numero_existe(db, datos.numero_operador):
        raise NumeroDuplicado("Ya existe un operador con ese número")

    nuevo = Operador(
        numero_operador=datos.numero_operador,
        contrasena_hash=hashear_contrasena(datos.contrasena),
        rol_id=rol.id,
    )
    try:
        db.add(nuevo)
        db.commit()
    except IntegrityError as error:
        db.rollback()
        # Dos altas simultáneas pasaron la consulta de arriba: frena la restricción única.
        if _numero_existe(db, datos.numero_operador):
            raise NumeroDuplicado("Ya existe un operador con ese número") from error
        raise
    except Exception:
        db.rollback()
        raise
    return nuevo
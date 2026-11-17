"""Gestión de operadores (ABM): reglas de negocio."""

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.roles import ROL_ADMIN_PRINCIPAL, ROL_ADMIN_SECUNDARIO, ROL_OPERADOR
from app.core.seguridad import hashear_contrasena
from app.models import Operador, Rol
from app.schemas.operador import OperadorAltaIn, OperadorModificarIn


class ErrorDeOperadores(Exception):
    """Una regla de negocio no se cumple. El router la responde como 422."""


class SinPermiso(ErrorDeOperadores):
    """El rol del operador no alcanza para esta acción. El router la responde como 403."""


class NumeroDuplicado(ErrorDeOperadores):
    """Ya existe un operador con ese número. El router la responde como 409."""
    
class OperadorInexistente(ErrorDeOperadores):
    """El operador pedido no existe. El router la responde como 404."""


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

def listar_operadores(db: Session, activo: bool | None = None) -> list[Operador]:
    """Operadores ordenados por id. Con activo se filtra por estado (baja lógica)."""
    consulta = select(Operador).options(selectinload(Operador.rol)).order_by(Operador.id)
    if activo is not None:
        consulta = consulta.where(Operador.activo.is_(activo))
    return list(db.scalars(consulta))


def listar_roles_asignables(db: Session, actor: Operador) -> list[Rol]:
    """Roles que el actor puede dar a otros, ordenados por id."""
    nombres = roles_que_puede_asignar(actor)
    return list(db.scalars(select(Rol).where(Rol.nombre.in_(nombres)).order_by(Rol.id)))

def _deja_sin_principal(db: Session, objetivo: Operador, nuevo_rol: Rol, nuevo_activo: bool) -> bool:
    """True si el cambio dejaría al sistema sin ningún administrador principal activo."""
    era_principal_activo = objetivo.activo and objetivo.rol.nombre == ROL_ADMIN_PRINCIPAL
    seguira_siendolo = nuevo_activo and nuevo_rol.nombre == ROL_ADMIN_PRINCIPAL
    if not era_principal_activo or seguira_siendolo:
        return False
    otros = db.scalar(
        select(func.count())
        .select_from(Operador)
        .join(Rol, Rol.id == Operador.rol_id)
        .where(
            Rol.nombre == ROL_ADMIN_PRINCIPAL,
            Operador.activo.is_(True),
            Operador.id != objetivo.id,
        )
    )
    return otros == 0


def modificar_operador(
    db: Session, actor: Operador, operador_id: int, datos: OperadorModificarIn
) -> Operador:
    """Cambia el rol y/o el estado de un operador, respetando la matriz de permisos."""
    objetivo = db.get(Operador, operador_id)
    if objetivo is None:
        raise OperadorInexistente("El operador no existe")

    asignables = roles_que_puede_asignar(actor)
    if objetivo.rol.nombre not in asignables:
        raise SinPermiso("No tiene permiso para modificar a este operador")

    nuevo_rol = objetivo.rol
    if datos.rol_id is not None:
        nuevo_rol = db.get(Rol, datos.rol_id)
        if nuevo_rol is None:
            raise ErrorDeOperadores("El rol no existe")
        if nuevo_rol.nombre not in asignables:
            raise SinPermiso("No tiene permiso para asignar ese rol")
    nuevo_activo = objetivo.activo if datos.activo is None else datos.activo

    if objetivo.id == actor.id and not nuevo_activo:
        raise ErrorDeOperadores("No puede darse de baja a sí mismo")
    if _deja_sin_principal(db, objetivo, nuevo_rol, nuevo_activo):
        raise ErrorDeOperadores("Debe quedar al menos un administrador principal activo")

    objetivo.rol_id = nuevo_rol.id
    objetivo.activo = nuevo_activo
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    return objetivo
"""Recuperación de contraseña: generación del código por un administrador."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.codigo_recuperacion import MINUTOS_VIGENCIA, generar_codigo
from app.core.seguridad import hashear_contrasena, verificar_contrasena
from app.models import Operador, RecuperacionContrasena
from app.schemas.recuperacion import RecuperarContrasenaIn
from app.services.operadores import (
    ErrorDeOperadores,
    OperadorInexistente,
    SinPermiso,
    roles_que_puede_asignar,
)


def generar_codigo_recuperacion(
    db: Session, actor: Operador, operador_id: int
) -> tuple[str, datetime]:
    """Genera un código de un solo uso para el operador y devuelve (código, vencimiento).

    Solo se guarda el hash: el código en claro se devuelve una única vez y no se
    puede recuperar. Un código nuevo invalida los anteriores porque, al validar,
    solo cuenta el de mayor id del operador.
    """
    objetivo = db.get(Operador, operador_id)
    if objetivo is None:
        raise OperadorInexistente("El operador no existe")
    if objetivo.rol.nombre not in roles_que_puede_asignar(actor):
        raise SinPermiso("No tiene permiso para generar un código a este operador")
    if objetivo.id == actor.id:
        raise ErrorDeOperadores("No puede generarse un código a sí mismo")
    if not objetivo.activo:
        raise ErrorDeOperadores("El operador está dado de baja")

    codigo = generar_codigo()
    ahora = datetime.now(timezone.utc)
    registro = RecuperacionContrasena(
        operador_id=objetivo.id,
        generado_por_id=actor.id,
        codigo_hash=hashear_contrasena(codigo),
        creado=ahora,
        vence=ahora + timedelta(minutes=MINUTOS_VIGENCIA),
    )
    try:
        db.add(registro)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return codigo, registro.vence


MENSAJE_CODIGO_INVALIDO = "Número de operador o código incorrecto, vencido o ya usado"

# Hash de un código que nadie tiene: se verifica cuando no hay registro, para que
# la respuesta tarde lo mismo y no delate qué números existen.
_HASH_FALSO = hashear_contrasena("codigo-que-no-corresponde-a-nadie")


class CodigoInvalido(Exception):
    """El código no sirve. Un único mensaje para todos los motivos."""


def restablecer_contrasena(db: Session, datos: RecuperarContrasenaIn) -> None:
    """Cambia la contraseña del operador si el código es válido, y lo marca como usado.

    Vale solo el código de mayor id del operador. Es inválido si el número no existe,
    el operador está dado de baja, el código es incorrecto, venció o ya se usó.
    La fila del código se bloquea para que dos usos simultáneos no pasen ambos.
    """
    operador = db.scalar(select(Operador).where(Operador.numero_operador == datos.numero_operador))
    registro = None
    if operador is not None:
        registro = db.scalar(
            select(RecuperacionContrasena)
            .where(RecuperacionContrasena.operador_id == operador.id)
            .order_by(RecuperacionContrasena.id.desc())
            .limit(1)
            .with_for_update()
        )

    hash_a_comparar = registro.codigo_hash if registro else _HASH_FALSO
    codigo_correcto = verificar_contrasena(datos.codigo, hash_a_comparar)
    ahora = datetime.now(timezone.utc)

    if (
        operador is None
        or registro is None
        or not codigo_correcto
        or not operador.activo
        or registro.usado is not None
        or registro.vence <= ahora
    ):
        raise CodigoInvalido(MENSAJE_CODIGO_INVALIDO)

    operador.contrasena_hash = hashear_contrasena(datos.contrasena_nueva)
    registro.usado = ahora
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
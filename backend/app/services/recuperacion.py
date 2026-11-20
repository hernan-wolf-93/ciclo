"""Recuperación de contraseña: generación del código por un administrador."""

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.codigo_recuperacion import MINUTOS_VIGENCIA, generar_codigo
from app.core.seguridad import hashear_contrasena
from app.models import Operador, RecuperacionContrasena
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
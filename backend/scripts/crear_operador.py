"""Crea un operador desde la terminal.

La contraseña se pide por teclado y solo se guarda su hash. Uso, desde backend
y con el entorno virtual activo:

    python -m scripts.crear_operador
"""

import sys
from getpass import getpass

from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.seguridad import hashear_contrasena
from app.models import Operador, Rol

LARGO_MINIMO_CONTRASENA = 8  # provisorio, a validar con el servicio


def main() -> int:
    with SessionLocal() as db:
        roles = db.scalars(select(Rol).order_by(Rol.id)).all()
        if not roles:
            print("No hay roles cargados. Ejecutar antes: alembic upgrade head")
            return 1

        numero = input("Número de operador: ").strip()
        if not numero or " " in numero or len(numero) > 20:
            print("El número debe tener entre 1 y 20 caracteres, sin espacios.")
            return 1
        if db.scalar(select(Operador).where(Operador.numero_operador == numero)):
            print("Ya existe un operador con ese número.")
            return 1

        print("Roles disponibles:")
        for rol in roles:
            print(f"  {rol.id}. {rol.nombre}")
        try:
            rol_elegido = next(r for r in roles if r.id == int(input("Rol (número): ")))
        except (ValueError, StopIteration):
            print("Rol inválido.")
            return 1

        contrasena = getpass("Contraseña: ")
        if len(contrasena) < LARGO_MINIMO_CONTRASENA:
            print(f"La contraseña debe tener al menos {LARGO_MINIMO_CONTRASENA} caracteres.")
            return 1
        if contrasena != getpass("Repetir contraseña: "):
            print("Las contraseñas no coinciden.")
            return 1

        db.add(
            Operador(
                numero_operador=numero,
                contrasena_hash=hashear_contrasena(contrasena),
                rol_id=rol_elegido.id,
            )
        )
        db.commit()
        print(f"Operador {numero} creado con el rol «{rol_elegido.nombre}».")
    return 0


if __name__ == "__main__":
    sys.exit(main())
from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Rol(Base):
    __tablename__ = "rol"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(50), unique=True)

    operadores: Mapped[list["Operador"]] = relationship(back_populates="rol")


class Operador(Base):
    """Persona que opera el sistema. Es también el usuario (se identifica por número)."""

    __tablename__ = "operador"

    id: Mapped[int] = mapped_column(primary_key=True)
    numero_operador: Mapped[str] = mapped_column(String(20), unique=True)
    contrasena_hash: Mapped[str] = mapped_column(String(255))
    rol_id: Mapped[int] = mapped_column(ForeignKey("rol.id"))
    activo: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    rol: Mapped["Rol"] = relationship(back_populates="operadores")
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, String, func
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
    
class RecuperacionContrasena(Base):
    """Código de un solo uso para restablecer la contraseña de un operador.

    Lo genera un administrador y se entrega en persona. Solo se guarda el hash
    del código. Vale el de mayor id del operador: uno nuevo invalida los anteriores.
    """

    __tablename__ = "recuperacion_contrasena"
    __table_args__ = (
        CheckConstraint("vence > creado", name="ck_recuperacion_vence_posterior"),
        CheckConstraint(
            "usado IS NULL OR usado >= creado", name="ck_recuperacion_uso_posterior"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    operador_id: Mapped[int] = mapped_column(ForeignKey("operador.id"), index=True)
    generado_por_id: Mapped[int] = mapped_column(ForeignKey("operador.id"))
    codigo_hash: Mapped[str] = mapped_column(String(255))
    creado: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    vence: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    usado: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
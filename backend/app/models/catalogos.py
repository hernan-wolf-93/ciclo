from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Servicio(Base):
    __tablename__ = "servicio"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100), unique=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")


class ServicioIncompatible(Base):
    """Par de servicios que no pueden compartir lote (ej.: NEO y UTI).

    Se guarda siempre con servicio_a_id < servicio_b_id, de modo que el
    mismo par no pueda cargarse dos veces en orden inverso.
    """

    __tablename__ = "servicio_incompatible"
    __table_args__ = (
        CheckConstraint("servicio_a_id < servicio_b_id", name="ck_servicio_incompatible_orden"),
    )

    servicio_a_id: Mapped[int] = mapped_column(ForeignKey("servicio.id"), primary_key=True)
    servicio_b_id: Mapped[int] = mapped_column(ForeignKey("servicio.id"), primary_key=True)


class Material(Base):
    __tablename__ = "material"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100), unique=True)
    codigo: Mapped[str | None] = mapped_column(String(10), unique=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")


class Etapa(Base):
    __tablename__ = "etapa"

    id: Mapped[int] = mapped_column(primary_key=True)
    orden: Mapped[int] = mapped_column(Integer, unique=True)
    nombre: Mapped[str] = mapped_column(String(50))
    area: Mapped[str] = mapped_column(String(50))
    color: Mapped[str] = mapped_column(String(30))


class MetodoEsterilizacion(Base):
    __tablename__ = "metodo_esterilizacion"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(50), unique=True)

    equipos: Mapped[list["Equipo"]] = relationship(back_populates="metodo")
    programas: Mapped[list["Programa"]] = relationship(back_populates="metodo")


class Equipo(Base):
    __tablename__ = "equipo"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(50), unique=True)
    metodo_id: Mapped[int] = mapped_column(ForeignKey("metodo_esterilizacion.id"))
    activo: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    metodo: Mapped["MetodoEsterilizacion"] = relationship(back_populates="equipos")


class Programa(Base):
    """Provisorio: la relación con el método está pendiente de validar con el servicio."""

    __tablename__ = "programa"
    __table_args__ = (UniqueConstraint("metodo_id", "nombre", name="uq_programa_metodo_nombre"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100))
    metodo_id: Mapped[int] = mapped_column(ForeignKey("metodo_esterilizacion.id"))

    metodo: Mapped["MetodoEsterilizacion"] = relationship(back_populates="programas")
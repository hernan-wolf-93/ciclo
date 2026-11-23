from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Servicio(Base):
    __tablename__ = "servicio"
    __table_args__ = (
        CheckConstraint("dias_aireacion >= 0", name="ck_servicio_dias_aireacion"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100), unique=True)
    dias_aireacion: Mapped[int] = mapped_column(
        Integer, default=3, server_default=text("3")
    )
    # Centro externo (otro hospital, área programática o sanatorio). Migración 0010.
    externo: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
    activo: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")


class ServicioIncompatible(Base):
    """Par de servicios que no pueden compartir lote con un método (ej.: NEO y UTI
    solo en óxido de etileno; en autoclave y estufa sí pueden ir juntos).

    Se guarda siempre con servicio_a_id < servicio_b_id, de modo que el
    mismo par no pueda cargarse dos veces en orden inverso.
    """

    __tablename__ = "servicio_incompatible"
    __table_args__ = (
        CheckConstraint("servicio_a_id < servicio_b_id", name="ck_servicio_incompatible_orden"),
    )

    servicio_a_id: Mapped[int] = mapped_column(ForeignKey("servicio.id"), primary_key=True)
    servicio_b_id: Mapped[int] = mapped_column(ForeignKey("servicio.id"), primary_key=True)
    metodo_id: Mapped[int] = mapped_column(ForeignKey("metodo_esterilizacion.id"), primary_key=True)


class Material(Base):
    __tablename__ = "material"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100), unique=True)
    codigo: Mapped[str | None] = mapped_column(String(10), unique=True)
    nombre_alternativo: Mapped[str | None] = mapped_column(String(100))
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
    __table_args__ = (
        CheckConstraint(
            "vencimiento_dias IS NULL OR vencimiento_dias > 0", name="ck_metodo_vencimiento_positivo"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(50), unique=True)
    # True solo en óxido de etileno: el material espera la aireación antes de entregarse
    requiere_aireacion: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )
    # TODO: provisorio, el más conservador de lo que dijo el servicio (90, 90 y 365 días)
    vencimiento_dias: Mapped[int | None] = mapped_column(Integer)

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
    """Programa de un equipo, asociado a su método. Los parámetros son los del panel
    del equipo (docs/RESPUESTAS-SERVICIO.md) y todos son opcionales: el programa P
    de la estufa no tiene valores fijos. La desgasificación del óxido de etileno
    ocurre dentro del equipo y no es la aireación."""

    __tablename__ = "programa"
    __table_args__ = (
        UniqueConstraint("metodo_id", "nombre", name="uq_programa_metodo_nombre"),
        CheckConstraint(
            "(tiempo_esterilizacion_min IS NULL OR tiempo_esterilizacion_min >= 0) AND "
            "(tiempo_secado_min IS NULL OR tiempo_secado_min >= 0) AND "
            "(tiempo_desgasificacion_min IS NULL OR tiempo_desgasificacion_min >= 0) AND "
            "(pulsos IS NULL OR pulsos >= 0)",
            name="ck_programa_valores_no_negativos",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100))
    metodo_id: Mapped[int] = mapped_column(ForeignKey("metodo_esterilizacion.id"))
    temperatura_c: Mapped[Decimal | None] = mapped_column(Numeric(5, 1))
    tiempo_esterilizacion_min: Mapped[int | None] = mapped_column(Integer)
    tiempo_secado_min: Mapped[int | None] = mapped_column(Integer)
    tiempo_desgasificacion_min: Mapped[int | None] = mapped_column(Integer)
    vacio_bar: Mapped[Decimal | None] = mapped_column(Numeric(4, 2))  # presión negativa, ej.: -0.75
    vapor_bar: Mapped[Decimal | None] = mapped_column(Numeric(4, 2))
    pulsos: Mapped[int | None] = mapped_column(Integer)

    metodo: Mapped["MetodoEsterilizacion"] = relationship(back_populates="programas")
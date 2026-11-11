from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Recepcion(Base):
    """Acto de recibir material de un servicio. El operador de cada ítem
    queda en su evento (decisión D4-A), no en la cabecera."""

    __tablename__ = "recepcion"

    id: Mapped[int] = mapped_column(primary_key=True)
    servicio_id: Mapped[int] = mapped_column(ForeignKey("servicio.id"))
    fecha_hora: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    items: Mapped[list["Item"]] = relationship(back_populates="recepcion")


class Entrega(Base):
    """Acto de entregar material a un servicio (puede ser parcial)."""

    __tablename__ = "entrega"

    id: Mapped[int] = mapped_column(primary_key=True)
    servicio_id: Mapped[int] = mapped_column(ForeignKey("servicio.id"))
    fecha_hora: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    items: Mapped[list["Item"]] = relationship(back_populates="entrega")


class Lote(Base):
    """Paquete que entra a un equipo de esterilización. El método se obtiene
    del equipo, no se guarda acá. Provisorio: la regla de numeración."""

    __tablename__ = "lote"
    __table_args__ = (
        CheckConstraint("fin IS NULL OR fin >= inicio", name="ck_lote_fin_posterior"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    numero: Mapped[int] = mapped_column(Integer, unique=True)
    equipo_id: Mapped[int] = mapped_column(ForeignKey("equipo.id"))
    programa_id: Mapped[int] = mapped_column(ForeignKey("programa.id"))
    operador_id: Mapped[int] = mapped_column(ForeignKey("operador.id"))
    inicio: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    fin: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    items: Mapped[list["Item"]] = relationship(back_populates="lote")


class Item(Base):
    """Una unidad física de material. Es lo que recorre el circuito.
    La etapa actual no se guarda: se deduce del último evento (D2-A)."""

    __tablename__ = "item"
    __table_args__ = (
        CheckConstraint(
            "lote_id IS NULL OR metodo_id IS NOT NULL",
            name="ck_item_lote_requiere_metodo",
        ),
        CheckConstraint(
            "entrega_id IS NULL OR lote_id IS NOT NULL",
            name="ck_item_entrega_requiere_lote",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    recepcion_id: Mapped[int] = mapped_column(ForeignKey("recepcion.id"), index=True)
    material_id: Mapped[int] = mapped_column(ForeignKey("material.id"))
    metodo_id: Mapped[int | None] = mapped_column(ForeignKey("metodo_esterilizacion.id"))
    lote_id: Mapped[int | None] = mapped_column(ForeignKey("lote.id"), index=True)
    entrega_id: Mapped[int | None] = mapped_column(ForeignKey("entrega.id"))

    recepcion: Mapped["Recepcion"] = relationship(back_populates="items")
    lote: Mapped["Lote | None"] = relationship(back_populates="items")
    entrega: Mapped["Entrega | None"] = relationship(back_populates="items")
    eventos: Mapped[list["EventoItem"]] = relationship(back_populates="item")


class EventoItem(Base):
    """Historial del ítem. Solo de agregado: la API no edita ni borra."""

    __tablename__ = "evento_item"
    __table_args__ = (
        UniqueConstraint("item_id", "etapa_id", name="uq_evento_item_etapa"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("item.id"), index=True)
    etapa_id: Mapped[int] = mapped_column(ForeignKey("etapa.id"))
    operador_id: Mapped[int] = mapped_column(ForeignKey("operador.id"))
    fecha_hora: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    item: Mapped["Item"] = relationship(back_populates="eventos")
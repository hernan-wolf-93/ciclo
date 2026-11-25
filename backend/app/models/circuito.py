from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Recepcion(Base):
    """Acto de recibir material de un servicio. El operador de cada ítem
    queda en su evento (decisión D4-A), no en la cabecera."""

    __tablename__ = "recepcion"
    __table_args__ = (
        CheckConstraint(
            "completo OR (servicio_avisado AND observacion IS NOT NULL "
            "AND length(btrim(observacion)) > 0)",
            name="ck_recepcion_incompleta_requiere_aviso",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    servicio_id: Mapped[int] = mapped_column(ForeignKey("servicio.id"))
    fecha_hora: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    completo: Mapped[bool] = mapped_column(Boolean)
    servicio_avisado: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )
    observacion: Mapped[str | None] = mapped_column(Text)
    urgente: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false")
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
    observacion: Mapped[str | None] = mapped_column(Text)

    items: Mapped[list["Item"]] = relationship(back_populates="entrega")


class Lote(Base):
    """Paquete que entra a un equipo de esterilización. El método se obtiene
    del equipo, no se guarda acá. El número va de 1 a 999 y se repite (reinicia
    y es por equipo): la propuesta del siguiente está en
    services/numeracion_lote.py."""

    __tablename__ = "lote"
    __table_args__ = (
        CheckConstraint("fin IS NULL OR fin >= inicio", name="ck_lote_fin_posterior"),
        CheckConstraint("numero BETWEEN 1 AND 999", name="ck_lote_numero_rango"),
        CheckConstraint(
            "resultado IN ('aprobado', 'fallido')", name="ck_lote_resultado_valido"
        ),
        CheckConstraint(
            "resultado IS DISTINCT FROM 'fallido' OR "
            "(observacion IS NOT NULL AND length(btrim(observacion)) > 0)",
            name="ck_lote_fallido_requiere_motivo",
        ),
        CheckConstraint(
            "(falla_posterior_en IS NULL) = (falla_posterior_por IS NULL)",
            name="ck_lote_falla_posterior_completa",
        ),
        CheckConstraint(
            "falla_posterior_en IS NULL OR resultado IS NOT DISTINCT FROM 'fallido'",
            name="ck_lote_falla_posterior_es_fallido",
        ),
        CheckConstraint(
            "falla_posterior_en IS NULL OR (fin IS NOT NULL AND falla_posterior_en >= fin)",
            name="ck_lote_falla_posterior_despues_del_cierre",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    numero: Mapped[int] = mapped_column(Integer, index=True)
    equipo_id: Mapped[int] = mapped_column(ForeignKey("equipo.id"))
    programa_id: Mapped[int] = mapped_column(ForeignKey("programa.id"))
    operador_id: Mapped[int] = mapped_column(ForeignKey("operador.id"))
    inicio: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    fin: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resultado: Mapped[str | None] = mapped_column(String(10))
    observacion: Mapped[str | None] = mapped_column(Text)
    numero_ciclo: Mapped[str | None] = mapped_column(String(20))  # contador del equipo (ticket)
    # Falla detectada después del cierre (indicador biológico o externo): cuándo y quién
    # la marcó. Un lote que falló en el cierre las deja en NULL.
    falla_posterior_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    falla_posterior_por: Mapped[int | None] = mapped_column(
        ForeignKey("operador.id", name="lote_falla_posterior_por_fkey")
    )

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
        CheckConstraint(
            "cantidad_piezas IS NULL OR cantidad_piezas > 0",
            name="ck_item_cantidad_piezas_positiva",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    recepcion_id: Mapped[int] = mapped_column(ForeignKey("recepcion.id"), index=True)
    material_id: Mapped[int] = mapped_column(ForeignKey("material.id"))
    metodo_id: Mapped[int | None] = mapped_column(ForeignKey("metodo_esterilizacion.id"))
    lote_id: Mapped[int | None] = mapped_column(ForeignKey("lote.id"), index=True)
    entrega_id: Mapped[int | None] = mapped_column(ForeignKey("entrega.id"), index=True)
    # Cajas: se anota la caja y su número de piezas, sin detallar cuáles
    cantidad_piezas: Mapped[int | None] = mapped_column(Integer)
    # Texto libre del material genérico "Otros" (renglón "Otros" de las planillas)
    descripcion: Mapped[str | None] = mapped_column(Text)

    recepcion: Mapped["Recepcion"] = relationship(back_populates="items")
    lote: Mapped["Lote | None"] = relationship(back_populates="items")
    entrega: Mapped["Entrega | None"] = relationship(back_populates="items")
    eventos: Mapped[list["EventoItem"]] = relationship(back_populates="item")


class EventoItem(Base):
    """Historial del ítem. Solo de agregado: la API no edita ni borra.

    intento: 1 en el primer recorrido. El reempaque por falla del indicador
    interno usará intento 2 o más (services/flujo.siguiente_intento). La
    reesterilización actual sigue con intento 1: la distingue el lote_id.
    """

    __tablename__ = "evento_item"
    __table_args__ = (
        UniqueConstraint(
            "item_id",
            "etapa_id",
            "lote_id",
            "intento",
            name="uq_evento_item_etapa_lote_intento",
            postgresql_nulls_not_distinct=True,
        ),
        CheckConstraint("intento >= 1", name="ck_evento_item_intento_positivo"),
        CheckConstraint(
            "NOT solo_desinfeccion OR "
            "(observacion IS NOT NULL AND length(btrim(observacion)) > 0)",
            name="ck_evento_item_excepcion_requiere_observacion",
        ),
    )
    observacion: Mapped[str | None] = mapped_column(Text)
    solo_desinfeccion: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false")
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("item.id"))
    etapa_id: Mapped[int] = mapped_column(ForeignKey("etapa.id"))
    lote_id: Mapped[int | None] = mapped_column(ForeignKey("lote.id"), index=True)
    intento: Mapped[int] = mapped_column(Integer, default=1, server_default=text("1"))
    operador_id: Mapped[int] = mapped_column(ForeignKey("operador.id"))
    fecha_hora: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    item: Mapped["Item"] = relationship(back_populates="eventos")


class ControlBowieDick(Base):
    """Prueba Bowie-Dick: obligatoria todos los días antes de usar el autoclave.

    La validación "no esterilizar sin un Bowie-Dick aprobado hoy" va en la API de
    esterilización (todavía no existe); la consulta está en services/bowie_dick.py.
    """

    __tablename__ = "control_bowie_dick"
    __table_args__ = (
        CheckConstraint("resultado IN ('aprobado', 'fallido')", name="ck_bowie_dick_resultado_valido"),
        CheckConstraint(
            "resultado <> 'fallido' OR (observacion IS NOT NULL AND length(btrim(observacion)) > 0)",
            name="ck_bowie_dick_fallido_requiere_motivo",
        ),
        Index("ix_control_bowie_dick_equipo_fecha", "equipo_id", "fecha_hora"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    equipo_id: Mapped[int] = mapped_column(ForeignKey("equipo.id"))
    fecha_hora: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    operador_id: Mapped[int] = mapped_column(ForeignKey("operador.id"))
    resultado: Mapped[str] = mapped_column(String(10))
    observacion: Mapped[str | None] = mapped_column(Text)
    numero_ciclo: Mapped[str | None] = mapped_column(String(20))
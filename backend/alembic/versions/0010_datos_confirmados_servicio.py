"""datos confirmados por el servicio

Carga lo que el servicio ya confirmó (docs/RESPUESTAS-SERVICIO.md): servicios del
hospital y centros externos, días de aireación, métodos (aireación y vencimiento),
programas con sus parámetros, número de ciclo del lote, incompatibilidad por
método, piezas y descripción del ítem, intento en el historial y control
Bowie-Dick. El catálogo completo de materiales va en la 0011.

Ninguna operación de datos usa ids fijos: todo se busca por nombre (o por una clave
natural, como método + nombre del programa), porque los ids cambian entre máquinas.
Las operaciones son idempotentes:
- Un renombre solo se aplica si el nombre nuevo todavía no existe. Si ya existen
  los dos (por ejemplo, "Guardia" y "Guardia Mayor"), no se toca la fila vieja y se
  avisa en la salida de Alembic: los datos se cargan sobre la fila con el nombre nuevo.
- Los INSERT no duplican: si el registro ya existe, se conserva y se le actualizan
  los valores confirmados.

Revision ID: 0010
Revises: 0009
"""
import logging
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0010"
down_revision: Union[str, Sequence[str], None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

log = logging.getLogger("alembic.runtime.migration")

# Servicios del hospital que faltaban (planillas). Guardia y Consultorios se renombran.
SERVICIOS_NUEVOS = [
    "Guardia Pediátrica", "Enfermería", "SIA", "U.T.P.R.", "Ala 2", "Ala 3",
    "Ala 4 Ginecología", "Sala 1", "Sala 2", "Sala 5", "Sala 6", "Sala 7",
]
# Centros externos: Aguilares y Monteros ya existían; el resto se agrega.
# El repositorio es público: los sanatorios privados van con un nombre genérico.
# Los nombres reales se cargan desde el ABM de servicios al instalar el sistema.
EXTERNOS_EXISTENTES = ["Aguilares", "Monteros"]
EXTERNOS_NUEVOS = [
    "Alberdi", "Área Programática", "Sanatorio privado A", "Sanatorio privado B", "Sanatorio privado C",
]
RENOMBRES_SERVICIO = [("Guardia", "Guardia Mayor"), ("Consultorios", "Consultorios Externos")]

# Programas: (nombre, método, temperatura, esterilización, secado, desgasificación, vacío, vapor, pulsos)
PROGRAMAS_EXISTENTES = [
    ("Instrumental 134 °C", "Calor húmedo", 134, 20, 30, None, -0.75, 1.00, 1),
    ("Textil 134 °C", "Calor húmedo", 134, 10, 10, None, -0.75, 1.00, 2),
    ("Termolábil 121 °C", "Calor húmedo", 121, 20, 20, None, -0.75, 0.80, 2),  # antes "Gomas 121 °C"
]
PROGRAMAS_NUEVOS = [
    ("Líquidos 121 °C", "Calor húmedo", 121, 20, 0, None, -0.40, 0.00, 0),
    ("Priones 134 °C", "Calor húmedo", 134, 60, 20, None, -0.75, 1.00, 2),
    ("A 160 °C", "Calor seco", 160, 120, None, None, None, None, None),
    ("B 170 °C", "Calor seco", 170, 90, None, None, None, None, None),
    ("C 180 °C", "Calor seco", 180, 60, None, None, None, None, None),
    ("P programable", "Calor seco", None, None, None, None, None, None, None),
    ("Ciclo caliente 55 °C", "Óxido de etileno", 55, 180, None, 720, None, None, None),
]
RENOMBRE_PROGRAMA = ("Gomas 121 °C", "Termolábil 121 °C", "Calor húmedo")


def _texto(valor: str) -> str:
    return "'" + valor.replace("'", "''") + "'"


def _lista(nombres: list[str]) -> str:
    return ", ".join(_texto(n) for n in nombres)


def _valor(v) -> str:
    return "NULL" if v is None else str(v)


def _metodo(nombre: str) -> str:
    """Subconsulta del id de un método, buscado por nombre."""
    return f"(SELECT id FROM metodo_esterilizacion WHERE nombre = {_texto(nombre)})"


def _renombrar_servicio(viejo: str, nuevo: str) -> None:
    """Renombra en la misma fila (conserva el id y las referencias), solo si el nombre
    nuevo no existe. Si existen los dos, no toca la fila vieja y lo avisa."""
    conexion = op.get_bind()
    existe_viejo = conexion.scalar(sa.text("SELECT count(*) FROM servicio WHERE nombre = :n"), {"n": viejo})
    existe_nuevo = conexion.scalar(sa.text("SELECT count(*) FROM servicio WHERE nombre = :n"), {"n": nuevo})
    if existe_viejo and existe_nuevo:
        log.warning("0010: ya existen '%s' y '%s'; no se renombra y se usa '%s'", viejo, nuevo, nuevo)
    op.execute(
        f"UPDATE servicio SET nombre = {_texto(nuevo)} WHERE nombre = {_texto(viejo)} "
        f"AND NOT EXISTS (SELECT 1 FROM servicio WHERE nombre = {_texto(nuevo)})"
    )


def _agregar_servicios(nombres: list[str], externo: bool) -> None:
    """Agrega los que falten; si ya existen, se conservan."""
    valores = ", ".join(f"({_texto(n)}, {str(externo).lower()})" for n in nombres)
    op.execute(f"INSERT INTO servicio (nombre, externo) VALUES {valores} ON CONFLICT (nombre) DO NOTHING")


def _cargar_programa(nombre, metodo, temp, est, sec, desg, vacio, vapor, pulsos) -> None:
    """Agrega el programa si falta (clave natural: método + nombre) y le carga los valores."""
    op.execute(
        f"INSERT INTO programa (nombre, metodo_id) SELECT {_texto(nombre)}, {_metodo(metodo)} "
        "ON CONFLICT (metodo_id, nombre) DO NOTHING"
    )
    op.execute(
        f"UPDATE programa SET temperatura_c = {_valor(temp)}, tiempo_esterilizacion_min = {_valor(est)}, "
        f"tiempo_secado_min = {_valor(sec)}, tiempo_desgasificacion_min = {_valor(desg)}, "
        f"vacio_bar = {_valor(vacio)}, vapor_bar = {_valor(vapor)}, pulsos = {_valor(pulsos)} "
        f"WHERE nombre = {_texto(nombre)} AND metodo_id = {_metodo(metodo)}"
    )


# Par NEO-UTI en el orden en que se guarda (servicio_a_id < servicio_b_id), buscado por nombre
PAR_NEO_UTI = (
    "si.servicio_a_id = LEAST(a.id, b.id) AND si.servicio_b_id = GREATEST(a.id, b.id) "
    "AND a.nombre = 'Neonatología' AND b.nombre = 'Unidad de Terapia Intensiva'"
)


def upgrade() -> None:
    # --- servicio --------------------------------------------------------------
    op.add_column("servicio", sa.Column("externo", sa.Boolean(), server_default=sa.text("false"), nullable=False))
    for viejo, nuevo in RENOMBRES_SERVICIO:
        _renombrar_servicio(viejo, nuevo)
    _agregar_servicios(SERVICIOS_NUEVOS, externo=False)
    _agregar_servicios(EXTERNOS_NUEVOS, externo=True)
    op.execute(f"UPDATE servicio SET externo = true WHERE nombre IN ({_lista(EXTERNOS_EXISTENTES + EXTERNOS_NUEVOS)})")
    op.execute("UPDATE servicio SET activo = false WHERE nombre = 'Otro'")
    # TODO: "Pediatría" queda activo; falta confirmar a qué planilla corresponde.
    op.execute("UPDATE servicio SET dias_aireacion = 3")
    op.execute("UPDATE servicio SET dias_aireacion = 10 WHERE nombre = 'Neonatología'")
    op.execute("UPDATE servicio SET dias_aireacion = 7 WHERE nombre IN ('Pediatría', 'Guardia Pediátrica')")

    # --- metodo_esterilizacion ---------------------------------------------------
    op.add_column(
        "metodo_esterilizacion",
        sa.Column("requiere_aireacion", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.add_column("metodo_esterilizacion", sa.Column("vencimiento_dias", sa.Integer(), nullable=True))
    op.create_check_constraint(
        "ck_metodo_vencimiento_positivo", "metodo_esterilizacion", "vencimiento_dias IS NULL OR vencimiento_dias > 0"
    )
    op.execute("UPDATE metodo_esterilizacion SET requiere_aireacion = true WHERE nombre = 'Óxido de etileno'")
    # TODO: vencimiento provisorio, el más conservador de lo que dijo el servicio
    op.execute("UPDATE metodo_esterilizacion SET vencimiento_dias = 90 WHERE nombre IN ('Calor húmedo', 'Calor seco')")
    op.execute("UPDATE metodo_esterilizacion SET vencimiento_dias = 365 WHERE nombre = 'Óxido de etileno'")

    # --- programa ----------------------------------------------------------------
    op.add_column("programa", sa.Column("temperatura_c", sa.Numeric(5, 1), nullable=True))
    op.add_column("programa", sa.Column("tiempo_esterilizacion_min", sa.Integer(), nullable=True))
    op.add_column("programa", sa.Column("tiempo_secado_min", sa.Integer(), nullable=True))
    op.add_column("programa", sa.Column("tiempo_desgasificacion_min", sa.Integer(), nullable=True))
    op.add_column("programa", sa.Column("vacio_bar", sa.Numeric(4, 2), nullable=True))
    op.add_column("programa", sa.Column("vapor_bar", sa.Numeric(4, 2), nullable=True))
    op.add_column("programa", sa.Column("pulsos", sa.Integer(), nullable=True))
    op.create_check_constraint(
        "ck_programa_valores_no_negativos",
        "programa",
        "(tiempo_esterilizacion_min IS NULL OR tiempo_esterilizacion_min >= 0) AND "
        "(tiempo_secado_min IS NULL OR tiempo_secado_min >= 0) AND "
        "(tiempo_desgasificacion_min IS NULL OR tiempo_desgasificacion_min >= 0) AND "
        "(pulsos IS NULL OR pulsos >= 0)",
    )
    # "Gomas" pasa a "Termolábil" en la misma fila, solo si "Termolábil" no existe en ese método
    viejo, nuevo, metodo = RENOMBRE_PROGRAMA
    op.execute(
        f"UPDATE programa SET nombre = {_texto(nuevo)} WHERE nombre = {_texto(viejo)} "
        f"AND metodo_id = {_metodo(metodo)} AND NOT EXISTS "
        f"(SELECT 1 FROM programa q WHERE q.nombre = {_texto(nuevo)} AND q.metodo_id = {_metodo(metodo)})"
    )
    for programa in PROGRAMAS_EXISTENTES + PROGRAMAS_NUEVOS:
        _cargar_programa(*programa)

    # --- lote ------------------------------------------------------------------
    op.add_column("lote", sa.Column("numero_ciclo", sa.String(length=20), nullable=True))

    # --- servicio_incompatible: la incompatibilidad es por método -----------------
    op.add_column("servicio_incompatible", sa.Column("metodo_id", sa.Integer(), nullable=True))
    op.drop_constraint("servicio_incompatible_pkey", "servicio_incompatible", type_="primary")
    # NEO-UTI (buscado por nombre) aplica solo a óxido de etileno
    op.execute(
        f"UPDATE servicio_incompatible si SET metodo_id = {_metodo('Óxido de etileno')} "
        f"FROM servicio a, servicio b WHERE {PAR_NEO_UTI}"
    )
    # Cualquier otro par que hubiera se mantiene incompatible con todos los métodos, como antes
    op.execute(
        "INSERT INTO servicio_incompatible (servicio_a_id, servicio_b_id, metodo_id) "
        "SELECT si.servicio_a_id, si.servicio_b_id, m.id "
        "FROM servicio_incompatible si CROSS JOIN metodo_esterilizacion m WHERE si.metodo_id IS NULL"
    )
    op.execute("DELETE FROM servicio_incompatible WHERE metodo_id IS NULL")
    op.alter_column("servicio_incompatible", "metodo_id", nullable=False)
    op.create_foreign_key(
        "servicio_incompatible_metodo_id_fkey", "servicio_incompatible", "metodo_esterilizacion", ["metodo_id"], ["id"]
    )
    op.create_primary_key(
        "servicio_incompatible_pkey", "servicio_incompatible", ["servicio_a_id", "servicio_b_id", "metodo_id"]
    )

    # --- item y material "Otros" -----------------------------------------------
    op.add_column("item", sa.Column("cantidad_piezas", sa.Integer(), nullable=True))
    op.add_column("item", sa.Column("descripcion", sa.Text(), nullable=True))
    op.create_check_constraint(
        "ck_item_cantidad_piezas_positiva", "item", "cantidad_piezas IS NULL OR cantidad_piezas > 0"
    )
    op.execute("INSERT INTO material (nombre) VALUES ('Otros') ON CONFLICT (nombre) DO NOTHING")
    op.execute("UPDATE material SET activo = true WHERE nombre = 'Otros'")

    # --- evento_item: intento (reempaque futuro) --------------------------------
    # Los eventos existentes ya cumplían (ítem, etapa, lote) únicos: todos quedan en intento 1.
    op.add_column("evento_item", sa.Column("intento", sa.Integer(), server_default=sa.text("1"), nullable=False))
    op.create_check_constraint("ck_evento_item_intento_positivo", "evento_item", "intento >= 1")
    op.drop_constraint("uq_evento_item_etapa_lote", "evento_item", type_="unique")
    op.create_unique_constraint(
        "uq_evento_item_etapa_lote_intento",
        "evento_item",
        ["item_id", "etapa_id", "lote_id", "intento"],
        postgresql_nulls_not_distinct=True,
    )

    # --- control_bowie_dick ------------------------------------------------------
    op.create_table(
        "control_bowie_dick",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("equipo_id", sa.Integer(), nullable=False),
        sa.Column("fecha_hora", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("operador_id", sa.Integer(), nullable=False),
        sa.Column("resultado", sa.String(length=10), nullable=False),
        sa.Column("observacion", sa.Text(), nullable=True),
        sa.Column("numero_ciclo", sa.String(length=20), nullable=True),
        sa.CheckConstraint("resultado IN ('aprobado', 'fallido')", name="ck_bowie_dick_resultado_valido"),
        sa.CheckConstraint(
            "resultado <> 'fallido' OR (observacion IS NOT NULL AND length(btrim(observacion)) > 0)",
            name="ck_bowie_dick_fallido_requiere_motivo",
        ),
        sa.ForeignKeyConstraint(["equipo_id"], ["equipo.id"]),
        sa.ForeignKeyConstraint(["operador_id"], ["operador.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_control_bowie_dick_equipo_fecha", "control_bowie_dick", ["equipo_id", "fecha_hora"])


def downgrade() -> None:
    # ATENCION: los DELETE de datos agregados fallan si ya hay registros que los usan
    # (protección deseada, igual que en las migraciones anteriores). Todo se busca por
    # nombre; los renombres se deshacen solo si el nombre viejo no existe.

    # --- control_bowie_dick ------------------------------------------------------
    op.drop_index("ix_control_bowie_dick_equipo_fecha", table_name="control_bowie_dick")
    op.drop_table("control_bowie_dick")

    # --- evento_item ---------------------------------------------------------------
    op.drop_constraint("uq_evento_item_etapa_lote_intento", "evento_item", type_="unique")
    # Falla si ya hay eventos repetidos con intento 2 o más (reempaques)
    op.create_unique_constraint(
        "uq_evento_item_etapa_lote",
        "evento_item",
        ["item_id", "etapa_id", "lote_id"],
        postgresql_nulls_not_distinct=True,
    )
    op.drop_constraint("ck_evento_item_intento_positivo", "evento_item", type_="check")
    op.drop_column("evento_item", "intento")

    # --- item y material "Otros" ---------------------------------------------------
    op.execute("DELETE FROM material WHERE nombre = 'Otros'")
    op.drop_constraint("ck_item_cantidad_piezas_positiva", "item", type_="check")
    op.drop_column("item", "descripcion")
    op.drop_column("item", "cantidad_piezas")

    # --- servicio_incompatible ---------------------------------------------------
    # Antes no había método: se conserva solo una fila por par (la de menor método)
    op.execute(
        "DELETE FROM servicio_incompatible s USING servicio_incompatible t "
        "WHERE s.servicio_a_id = t.servicio_a_id AND s.servicio_b_id = t.servicio_b_id "
        "AND s.metodo_id > t.metodo_id"
    )
    op.drop_constraint("servicio_incompatible_pkey", "servicio_incompatible", type_="primary")
    op.create_primary_key("servicio_incompatible_pkey", "servicio_incompatible", ["servicio_a_id", "servicio_b_id"])
    op.drop_constraint("servicio_incompatible_metodo_id_fkey", "servicio_incompatible", type_="foreignkey")
    op.drop_column("servicio_incompatible", "metodo_id")

    # --- lote ------------------------------------------------------------------
    op.drop_column("lote", "numero_ciclo")

    # --- programa ----------------------------------------------------------------
    for nombre, metodo, *_ in PROGRAMAS_NUEVOS:
        op.execute(f"DELETE FROM programa WHERE nombre = {_texto(nombre)} AND metodo_id = {_metodo(metodo)}")
    nuevo, viejo, metodo = RENOMBRE_PROGRAMA[1], RENOMBRE_PROGRAMA[0], RENOMBRE_PROGRAMA[2]
    op.execute(
        f"UPDATE programa SET nombre = {_texto(viejo)} WHERE nombre = {_texto(nuevo)} "
        f"AND metodo_id = {_metodo(metodo)} AND NOT EXISTS "
        f"(SELECT 1 FROM programa q WHERE q.nombre = {_texto(viejo)} AND q.metodo_id = {_metodo(metodo)})"
    )
    op.drop_constraint("ck_programa_valores_no_negativos", "programa", type_="check")
    for columna in ("pulsos", "vapor_bar", "vacio_bar", "tiempo_desgasificacion_min", "tiempo_secado_min",
                    "tiempo_esterilizacion_min", "temperatura_c"):
        op.drop_column("programa", columna)

    # --- metodo_esterilizacion ---------------------------------------------------
    op.drop_constraint("ck_metodo_vencimiento_positivo", "metodo_esterilizacion", type_="check")
    op.drop_column("metodo_esterilizacion", "vencimiento_dias")
    op.drop_column("metodo_esterilizacion", "requiere_aireacion")

    # --- servicio --------------------------------------------------------------
    op.execute(f"DELETE FROM servicio WHERE nombre IN ({_lista(SERVICIOS_NUEVOS + EXTERNOS_NUEVOS)})")
    op.execute("UPDATE servicio SET dias_aireacion = 3")
    op.execute("UPDATE servicio SET activo = true WHERE nombre = 'Otro'")
    for viejo, nuevo in RENOMBRES_SERVICIO:
        op.execute(
            f"UPDATE servicio SET nombre = {_texto(viejo)} WHERE nombre = {_texto(nuevo)} "
            f"AND NOT EXISTS (SELECT 1 FROM servicio WHERE nombre = {_texto(viejo)})"
        )
    op.drop_column("servicio", "externo")

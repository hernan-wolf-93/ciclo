"""datos fijos

Revision ID: 0002
Revises: 9afab0f20aec
"""
from alembic import op

revision = "0002"
down_revision = "9afab0f20aec"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        INSERT INTO rol (nombre) VALUES
            ('Administrador principal'),
            ('Administrador secundario'),
            ('Operador')
    """)

    # Etapas del circuito (sección 6.4 del documento)
    op.execute("""
        INSERT INTO etapa (orden, nombre, area, color) VALUES
            (1, 'Recepción', 'Sucia', 'Rojo'),
            (2, 'Lavado y secado', 'Sucia', 'Rojo'),
            (3, 'Empaque y rotulación', 'Limpia', 'Azul'),
            (4, 'Esterilización', 'Esterilización', 'Gris'),
            (5, 'Almacén estéril', 'Limpia', 'Verde'),
            (6, 'Entrega', 'Limpia', 'Verde')
    """)

    op.execute("""
        INSERT INTO metodo_esterilizacion (nombre) VALUES
            ('Calor húmedo'),
            ('Calor seco'),
            ('Óxido de etileno')
    """)

    # Equipos físicos del servicio (nombres provisorios)
    op.execute("""
        INSERT INTO equipo (nombre, metodo_id)
        SELECT e.nombre, m.id
        FROM (VALUES
            ('Autoclave 1', 'Calor húmedo'),
            ('Autoclave 2', 'Calor húmedo'),
            ('Estufa 1', 'Calor seco'),
            ('Estufa 2', 'Calor seco'),
            ('Óxido de etileno 1', 'Óxido de etileno')
        ) AS e(nombre, metodo)
        JOIN metodo_esterilizacion m ON m.nombre = e.metodo
    """)


def downgrade() -> None:
    # Orden inverso: primero lo que depende de otras tablas.
    op.execute("""
        DELETE FROM equipo WHERE nombre IN
            ('Autoclave 1', 'Autoclave 2', 'Estufa 1', 'Estufa 2', 'Óxido de etileno 1')
    """)
    op.execute("""
        DELETE FROM metodo_esterilizacion WHERE nombre IN
            ('Calor húmedo', 'Calor seco', 'Óxido de etileno')
    """)
    op.execute("DELETE FROM etapa WHERE orden BETWEEN 1 AND 6")
    op.execute("""
        DELETE FROM rol WHERE nombre IN
            ('Administrador principal', 'Administrador secundario', 'Operador')
    """)
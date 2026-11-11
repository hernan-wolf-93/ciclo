"""catalogos iniciales

Revision ID: 0004
Revises: 0003
"""
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        INSERT INTO servicio (nombre) VALUES
            ('Quirófano'), ('Neonatología'), ('Guardia'), ('Pediatría'),
            ('Consultorios'), ('Aguilares'), ('Monteros'), ('Otro'),
            ('Unidad de Terapia Intensiva')
    """)

    # Neonatología y UTI no se mezclan en un mismo lote.
    # El par se guarda ordenado (a < b) para no cargarlo dos veces.
    op.execute("""
        INSERT INTO servicio_incompatible (servicio_a_id, servicio_b_id)
        SELECT LEAST(a.id, b.id), GREATEST(a.id, b.id)
        FROM servicio a, servicio b
        WHERE a.nombre = 'Neonatología'
          AND b.nombre = 'Unidad de Terapia Intensiva'
    """)

    # Programas provisorios, pendientes de validar con el servicio
    op.execute("""
        INSERT INTO programa (nombre, metodo_id)
        SELECT p.nombre, m.id
        FROM (VALUES
            ('Textil 134 °C', 'Calor húmedo'),
            ('Instrumental 134 °C', 'Calor húmedo'),
            ('Gomas 121 °C', 'Calor húmedo')
        ) AS p(nombre, metodo)
        JOIN metodo_esterilizacion m ON m.nombre = p.metodo
    """)


def downgrade() -> None:
    # ATENCION: si ya hay lotes o recepciones que usan estas filas,
    # los DELETE fallan por las claves foraneas (proteccion deseada).
    op.execute("DELETE FROM servicio_incompatible")
    op.execute("""
        DELETE FROM programa WHERE nombre IN
            ('Textil 134 °C', 'Instrumental 134 °C', 'Gomas 121 °C')
    """)
    op.execute("""
        DELETE FROM servicio WHERE nombre IN
            ('Quirófano', 'Neonatología', 'Guardia', 'Pediatría', 'Consultorios',
             'Aguilares', 'Monteros', 'Otro', 'Unidad de Terapia Intensiva')
    """)
"""materiales iniciales

Revision ID: 0006
Revises: 0005
"""
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


# Códigos del cartel del depósito. Los últimos cuatro no tienen código.
MATERIALES = [
    ("Gasa simple", "G"),
    ("Gasa doble", "GD"),
    ("Ponchito", "P"),
    ("Venda pediátrica", "VP"),
    ("Venda traumatológica", "VT"),
    ("Paño marino quirúrgico", "PMQ"),
    ("Venda quirófano", "VQ"),
    ("Apósito quirúrgico", "AQ"),
    ("Apósito", "A"),
    ("Paño marino", "PM"),
    ("Gasa x10 quirófano", "G10"),
    ("Caja cesárea", None),
    ("Equipo de ropa", None),
    ("Bolsa hidrófilo", None),
    ("Caja histerectomía", None),
]


def upgrade() -> None:
    material = op.get_bind()
    for nombre, codigo in MATERIALES:
        material.exec_driver_sql(
            "INSERT INTO material (nombre, codigo) VALUES (%s, %s)",
            (nombre, codigo),
        )


def downgrade() -> None:
    # ATENCION: si ya hay ítems que usan estos materiales,
    # el DELETE falla por la clave foránea (protección deseada).
    material = op.get_bind()
    for nombre, _ in MATERIALES:
        material.exec_driver_sql("DELETE FROM material WHERE nombre = %s", (nombre,))
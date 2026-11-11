"""ajusta indices

Revision ID: 0003
Revises: 0002
"""
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Redundante: uq_evento_item_etapa (item_id, etapa_id) ya empieza por item_id.
    op.drop_index("ix_evento_item_item_id", table_name="evento_item")
    # Para consultar qué se entregó en cada entrega.
    op.create_index("ix_item_entrega_id", "item", ["entrega_id"])


def downgrade() -> None:
    op.drop_index("ix_item_entrega_id", table_name="item")
    op.create_index("ix_evento_item_item_id", "evento_item", ["item_id"])
"""falla posterior al cierre del lote: auditoría

Revision ID: 0011
Revises: 0010
Create Date: 2026-11-25

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0011'
down_revision: Union[str, Sequence[str], None] = '0010'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # lote: cuándo y quién marcó la falla detectada después del cierre
    op.add_column('lote', sa.Column('falla_posterior_en', sa.DateTime(timezone=True), nullable=True))
    op.add_column('lote', sa.Column('falla_posterior_por', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'lote_falla_posterior_por_fkey', 'lote', 'operador', ['falla_posterior_por'], ['id']
    )
    op.create_check_constraint(
        'ck_lote_falla_posterior_completa',
        'lote',
        '(falla_posterior_en IS NULL) = (falla_posterior_por IS NULL)',
    )
    # IS NOT DISTINCT FROM: con resultado NULL, "= 'fallido'" daría NULL y el CHECK pasaría
    op.create_check_constraint(
        'ck_lote_falla_posterior_es_fallido',
        'lote',
        "falla_posterior_en IS NULL OR resultado IS NOT DISTINCT FROM 'fallido'",
    )
    op.create_check_constraint(
        'ck_lote_falla_posterior_despues_del_cierre',
        'lote',
        'falla_posterior_en IS NULL OR (fin IS NOT NULL AND falla_posterior_en >= fin)',
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Advertencia: borra los datos de auditoría de la falla posterior ya guardados.
    # Los lotes marcados quedan como fallidos, con el motivo en su observación.
    op.drop_constraint('ck_lote_falla_posterior_despues_del_cierre', 'lote', type_='check')
    op.drop_constraint('ck_lote_falla_posterior_es_fallido', 'lote', type_='check')
    op.drop_constraint('ck_lote_falla_posterior_completa', 'lote', type_='check')
    op.drop_constraint('lote_falla_posterior_por_fkey', 'lote', type_='foreignkey')
    op.drop_column('lote', 'falla_posterior_por')
    op.drop_column('lote', 'falla_posterior_en')
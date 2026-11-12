"""reesterilizacion, recepcion completa, aireacion y urgencia

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-12 01:34:28.727481

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0007'
down_revision: Union[str, Sequence[str], None] = '0006'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # servicio: días de aireación de óxido de etileno según el origen
    op.add_column('servicio', sa.Column('dias_aireacion', sa.Integer(), server_default=sa.text('3'), nullable=False))
    op.create_check_constraint('ck_servicio_dias_aireacion', 'servicio', 'dias_aireacion >= 0')

    # material: segundo nombre (técnico o de cirugía)
    op.add_column('material', sa.Column('nombre_alternativo', sa.String(length=100), nullable=True))

    # entrega: observaciones
    op.add_column('entrega', sa.Column('observacion', sa.Text(), nullable=True))

    # recepcion: control de piezas, aviso al servicio y urgencia
    op.add_column('recepcion', sa.Column('completo', sa.Boolean(), nullable=False))
    op.add_column('recepcion', sa.Column('servicio_avisado', sa.Boolean(), server_default=sa.text('false'), nullable=False))
    op.add_column('recepcion', sa.Column('observacion', sa.Text(), nullable=True))
    op.add_column('recepcion', sa.Column('urgente', sa.Boolean(), server_default=sa.text('false'), nullable=False))
    op.create_check_constraint(
        'ck_recepcion_incompleta_requiere_aviso',
        'recepcion',
        'completo OR (servicio_avisado AND observacion IS NOT NULL AND length(btrim(observacion)) > 0)',
    )

    # lote: la numeración 01-999 se reinicia, por eso deja de ser única
    op.drop_constraint('lote_numero_key', 'lote', type_='unique')
    op.create_index('ix_lote_numero', 'lote', ['numero'], unique=False)
    op.create_check_constraint('ck_lote_numero_rango', 'lote', 'numero BETWEEN 1 AND 999')

    # lote: resultado final y motivo (reesterilización)
    op.add_column('lote', sa.Column('resultado', sa.String(length=10), nullable=True))
    op.add_column('lote', sa.Column('observacion', sa.Text(), nullable=True))
    op.create_check_constraint('ck_lote_resultado_valido', 'lote', "resultado IN ('aprobado', 'fallido')")
    op.create_check_constraint(
        'ck_lote_fallido_requiere_motivo',
        'lote',
        "resultado IS DISTINCT FROM 'fallido' OR (observacion IS NOT NULL AND length(btrim(observacion)) > 0)",
    )

    # evento_item: lote del evento de Esterilización y nueva unicidad
    op.add_column('evento_item', sa.Column('lote_id', sa.Integer(), nullable=True))
    op.create_foreign_key('evento_item_lote_id_fkey', 'evento_item', 'lote', ['lote_id'], ['id'])
    op.create_index('ix_evento_item_lote_id', 'evento_item', ['lote_id'], unique=False)
    op.drop_constraint('uq_evento_item_etapa', 'evento_item', type_='unique')
    op.create_unique_constraint(
        'uq_evento_item_etapa_lote',
        'evento_item',
        ['item_id', 'etapa_id', 'lote_id'],
        postgresql_nulls_not_distinct=True,
    )


def downgrade() -> None:
    """Downgrade schema."""
    # evento_item
    op.drop_constraint('uq_evento_item_etapa_lote', 'evento_item', type_='unique')
    # Falla si ya hay dos eventos del mismo ítem y etapa (reesterilización)
    op.create_unique_constraint('uq_evento_item_etapa', 'evento_item', ['item_id', 'etapa_id'])
    op.drop_index('ix_evento_item_lote_id', table_name='evento_item')
    op.drop_constraint('evento_item_lote_id_fkey', 'evento_item', type_='foreignkey')
    op.drop_column('evento_item', 'lote_id')

    # lote
    op.drop_constraint('ck_lote_fallido_requiere_motivo', 'lote', type_='check')
    op.drop_constraint('ck_lote_resultado_valido', 'lote', type_='check')
    op.drop_column('lote', 'observacion')
    op.drop_column('lote', 'resultado')
    op.drop_constraint('ck_lote_numero_rango', 'lote', type_='check')
    op.drop_index('ix_lote_numero', table_name='lote')
    # Falla si ya hay números repetidos (después de un reinicio de la numeración)
    op.create_unique_constraint('lote_numero_key', 'lote', ['numero'])

    # recepcion
    op.drop_constraint('ck_recepcion_incompleta_requiere_aviso', 'recepcion', type_='check')
    op.drop_column('recepcion', 'urgente')
    op.drop_column('recepcion', 'observacion')
    op.drop_column('recepcion', 'servicio_avisado')
    op.drop_column('recepcion', 'completo')

    # entrega, material, servicio
    op.drop_column('entrega', 'observacion')
    op.drop_column('material', 'nombre_alternativo')
    op.drop_constraint('ck_servicio_dias_aireacion', 'servicio', type_='check')
    op.drop_column('servicio', 'dias_aireacion')
    
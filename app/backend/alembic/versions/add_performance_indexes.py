"""add performance indexes

Revision ID: new_perf_indexes
Revises: 55c181562e1e
Create Date: 2026-04-02 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'new_perf_indexes'
down_revision: Union[str, None] = '55c181562e1e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index('idx_ordres_travail_utilisateur_id', 'ordres_travail', ['utilisateur_id'])
    op.create_index('idx_ordres_travail_machine_id', 'ordres_travail', ['machine_id'])
    op.create_index('idx_ordres_travail_statut', 'ordres_travail', ['statut'])
    op.create_index('idx_interventions_machine_id', 'ordres_intervention', ['machine_id'])
    op.create_index('idx_interventions_created_at', 'ordres_intervention', ['created_at'])
    op.create_index('idx_notifications_utilisateur_id', 'notifications', ['utilisateur_id'])
    op.create_index('idx_notifications_lu', 'notifications', ['lu'])


def downgrade() -> None:
    op.drop_index('idx_notifications_lu', table_name='notifications')
    op.drop_index('idx_notifications_utilisateur_id', table_name='notifications')
    op.drop_index('idx_interventions_created_at', table_name='ordres_intervention')
    op.drop_index('idx_interventions_machine_id', table_name='ordres_intervention')
    op.drop_index('idx_ordres_travail_statut', table_name='ordres_travail')
    op.drop_index('idx_ordres_travail_machine_id', table_name='ordres_travail')
    op.drop_index('idx_ordres_travail_utilisateur_id', table_name='ordres_travail')

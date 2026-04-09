"""add more performance indexes for machines and related tables

Revision ID: more_perf_indexes_v2
Revises: be6721db2847
Create Date: 2026-04-03 18:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'more_perf_indexes_v2'
down_revision: Union[str, None] = 'add_plannings_idx'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    
    indexes_to_create = [
        ('idx_machines_zone', 'machines', ['zone']),
        ('idx_machines_sous_zone', 'machines', ['sous_zone']),
        ('idx_machines_ordre', 'machines', ['ordre']),
        ('idx_machines_statut', 'machines', ['statut']),
        ('idx_machines_created_at', 'machines', ['created_at']),
        ('idx_machines_zone_sous_zone', 'machines', ['zone', 'sous_zone']),
        ('idx_machines_zone_statut', 'machines', ['zone', 'statut']),
        ('idx_plannings_date_debut', 'plannings', ['date_debut']),
        ('idx_plannings_date_fin', 'plannings', ['date_fin']),
        ('idx_plannings_statut', 'plannings', ['statut']),
        ('idx_interventions_statut', 'ordres_intervention', ['statut']),
        ('idx_interventions_utilisateur_id', 'ordres_intervention', ['utilisateur_id']),
        ('idx_planning_ot_planning_id', 'planning_ordres_travail', ['planning_id']),
        ('idx_planning_ot_ordre_id', 'planning_ordres_travail', ['ordre_travail_id']),
        ('idx_planning_users_planning_id', 'planning_utilisateurs', ['planning_id']),
        ('idx_planning_users_utilisateur_id', 'planning_utilisateurs', ['utilisateur_id']),
    ]
    
    for idx_name, table_name, columns in indexes_to_create:
        result = conn.execute(
            sa.text(
                "SELECT 1 FROM pg_indexes WHERE schemaname = 'public' AND indexname = :idx_name"
            ),
            {"idx_name": idx_name},
        )
        if result.first():
            continue
        
        columns_exist = True
        for col in columns:
            col_check = conn.execute(
                sa.text(
                    "SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = :table_name AND column_name = :col_name"
                ),
                {"table_name": table_name, "col_name": col},
            )
            if not col_check.first():
                columns_exist = False
                break
        
        if columns_exist:
            op.create_index(idx_name, table_name, columns)


def downgrade() -> None:
    op.drop_index('idx_planning_users_utilisateur_id', table_name='planning_utilisateurs')
    op.drop_index('idx_planning_users_planning_id', table_name='planning_utilisateurs')
    op.drop_index('idx_planning_ot_ordre_id', table_name='planning_ordres_travail')
    op.drop_index('idx_planning_ot_planning_id', table_name='planning_ordres_travail')
    op.drop_index('idx_interventions_utilisateur_id', table_name='ordres_intervention')
    op.drop_index('idx_interventions_statut', table_name='ordres_intervention')
    op.drop_index('idx_plannings_statut', table_name='plannings')
    op.drop_index('idx_plannings_date_fin', table_name='plannings')
    op.drop_index('idx_plannings_date_debut', table_name='plannings')
    op.drop_index('idx_machines_zone_statut', table_name='machines')
    op.drop_index('idx_machines_zone_sous_zone', table_name='machines')
    op.drop_index('idx_machines_created_at', table_name='machines')
    op.drop_index('idx_machines_statut', table_name='machines')
    op.drop_index('idx_machines_ordre', table_name='machines')
    op.drop_index('idx_machines_sous_zone', table_name='machines')
    op.drop_index('idx_machines_zone', table_name='machines')

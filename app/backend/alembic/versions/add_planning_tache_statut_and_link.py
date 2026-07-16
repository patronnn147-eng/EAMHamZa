"""Add statut to PlanningTaches and planning_tache_id to OrdresIntervention

Revision ID: add_planning_tache_statut
Revises: merge_all_heads_final
Branch Labels: None
Depends On: None
"""

from alembic import op
import sqlalchemy as sa

revision = "add_planning_tache_statut"
down_revision = "add_PlanningTaches"
branch_labels = None
depends_on = None


def _column_exists(table, column):
    from alembic import op as _op
    from sqlalchemy import inspect

    bind = _op.get_bind()
    insp = inspect(bind)
    return column in [c["name"] for c in insp.get_columns(table)]


def upgrade():
    if not _column_exists("PlanningTaches", "statut"):
        op.add_column(
            "PlanningTaches",
            sa.Column("statut", sa.String(20), nullable=False, server_default="DRAFT"),
        )

    if not _column_exists("OrdresIntervention", "planning_tache_id"):
        op.add_column(
            "OrdresIntervention",
            sa.Column("planning_tache_id", sa.Integer(), nullable=True),
        )


def downgrade():
    op.drop_column("OrdresIntervention", "planning_tache_id")
    op.drop_column("PlanningTaches", "statut")

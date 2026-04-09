"""Phase 1: Work Orders & Interventions workflow

Revision ID: phase1_work_orders_interventions
Revises: update_ordres_travail_chetop
Create Date: 2026-02-09

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


def _column_exists(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    result = bind.execute(
        sa.text(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = :table_name AND column_name = :column_name
            """
        ),
        {"table_name": table_name, "column_name": column_name},
    )
    return result.first() is not None


def _index_exists(index_name: str) -> bool:
    bind = op.get_bind()
    result = bind.execute(
        sa.text(
            """
            SELECT 1
            FROM pg_indexes
            WHERE indexname = :index_name
            """
        ),
        {"index_name": index_name},
    )
    return result.first() is not None


# revision identifiers, used by Alembic.
revision: str = "phase1_work_orders_interventions"
down_revision: Union[str, Sequence[str], None] = "fix_enhance_work_orders"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- ordres_travail (work orders) ---
    if not _column_exists("ordres_travail", "created_by_id"):
        op.add_column("ordres_travail", sa.Column("created_by_id", sa.Integer(), nullable=True))
    if not _column_exists("ordres_travail", "validated_by_id"):
        op.add_column("ordres_travail", sa.Column("validated_by_id", sa.Integer(), nullable=True))
    if not _column_exists("ordres_travail", "validated_at"):
        op.add_column("ordres_travail", sa.Column("validated_at", sa.DateTime(timezone=True), nullable=True))
    if not _column_exists("ordres_travail", "assigned_at"):
        op.add_column("ordres_travail", sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=True))
    if not _column_exists("ordres_travail", "completed_at"):
        op.add_column("ordres_travail", sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))
    if not _column_exists("ordres_travail", "estimated_duration_minutes"):
        op.add_column(
            "ordres_travail",
            sa.Column("estimated_duration_minutes", sa.Integer(), nullable=True),
        )

    # --- ordres_intervention (interventions) ---
    if not _column_exists("ordres_intervention", "technicien_id"):
        op.add_column("ordres_intervention", sa.Column("technicien_id", sa.Integer(), nullable=True))
    if not _column_exists("ordres_intervention", "statut"):
        op.add_column(
            "ordres_intervention",
            sa.Column("statut", sa.String(length=20), nullable=False, server_default="EN_ATTENTE"),
        )
    if not _column_exists("ordres_intervention", "date_debut"):
        op.add_column("ordres_intervention", sa.Column("date_debut", sa.DateTime(timezone=True), nullable=True))
    if not _column_exists("ordres_intervention", "date_fin"):
        op.add_column("ordres_intervention", sa.Column("date_fin", sa.DateTime(timezone=True), nullable=True))
    if not _column_exists("ordres_intervention", "updated_at"):
        op.add_column("ordres_intervention", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True))

    idx_name = op.f("ix_ordres_intervention_technicien_id")
    if not _index_exists(idx_name):
        op.create_index(
            idx_name,
            "ordres_intervention",
            ["technicien_id"],
            unique=False,
        )


def downgrade() -> None:
    op.drop_index(op.f("ix_ordres_intervention_technicien_id"), table_name="ordres_intervention")

    op.drop_column("ordres_intervention", "updated_at")
    op.drop_column("ordres_intervention", "date_fin")
    op.drop_column("ordres_intervention", "date_debut")
    op.drop_column("ordres_intervention", "statut")
    op.drop_column("ordres_intervention", "technicien_id")

    op.drop_column("ordres_travail", "estimated_duration_minutes")
    op.drop_column("ordres_travail", "completed_at")
    op.drop_column("ordres_travail", "assigned_at")
    op.drop_column("ordres_travail", "validated_at")
    op.drop_column("ordres_travail", "validated_by_id")
    op.drop_column("ordres_travail", "created_by_id")

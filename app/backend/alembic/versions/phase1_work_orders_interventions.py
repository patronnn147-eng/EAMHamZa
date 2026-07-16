"""Phase 1: Work Orders & Interventions workflow

Revision ID: phase1_work_orders_interventions
Revises: update_OrdresTravail_chetop
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
    # --- OrdresTravail (work orders) ---
    if not _column_exists("OrdresTravail", "created_by_id"):
        op.add_column(
            "OrdresTravail", sa.Column("created_by_id", sa.Integer(), nullable=True)
        )
    if not _column_exists("OrdresTravail", "validated_by_id"):
        op.add_column(
            "OrdresTravail", sa.Column("validated_by_id", sa.Integer(), nullable=True)
        )
    if not _column_exists("OrdresTravail", "validated_at"):
        op.add_column(
            "OrdresTravail",
            sa.Column("validated_at", sa.DateTime(timezone=True), nullable=True),
        )
    if not _column_exists("OrdresTravail", "assigned_at"):
        op.add_column(
            "OrdresTravail",
            sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=True),
        )
    if not _column_exists("OrdresTravail", "completed_at"):
        op.add_column(
            "OrdresTravail",
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        )
    if not _column_exists("OrdresTravail", "estimated_duration_minutes"):
        op.add_column(
            "OrdresTravail",
            sa.Column("estimated_duration_minutes", sa.Integer(), nullable=True),
        )

    # --- OrdresIntervention (interventions) ---
    if not _column_exists("OrdresIntervention", "technicien_id"):
        op.add_column(
            "OrdresIntervention",
            sa.Column("technicien_id", sa.Integer(), nullable=True),
        )
    if not _column_exists("OrdresIntervention", "statut"):
        op.add_column(
            "OrdresIntervention",
            sa.Column(
                "statut",
                sa.String(length=20),
                nullable=False,
                server_default="EN_ATTENTE",
            ),
        )
    if not _column_exists("OrdresIntervention", "date_debut"):
        op.add_column(
            "OrdresIntervention",
            sa.Column("date_debut", sa.DateTime(timezone=True), nullable=True),
        )
    if not _column_exists("OrdresIntervention", "date_fin"):
        op.add_column(
            "OrdresIntervention",
            sa.Column("date_fin", sa.DateTime(timezone=True), nullable=True),
        )
    if not _column_exists("OrdresIntervention", "updated_at"):
        op.add_column(
            "OrdresIntervention",
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )

    idx_name = op.f("ix_OrdresIntervention_technicien_id")
    if not _index_exists(idx_name):
        op.create_index(
            idx_name,
            "OrdresIntervention",
            ["technicien_id"],
            unique=False,
        )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_OrdresIntervention_technicien_id"), table_name="OrdresIntervention"
    )

    op.drop_column("OrdresIntervention", "updated_at")
    op.drop_column("OrdresIntervention", "date_fin")
    op.drop_column("OrdresIntervention", "date_debut")
    op.drop_column("OrdresIntervention", "statut")
    op.drop_column("OrdresIntervention", "technicien_id")

    op.drop_column("OrdresTravail", "estimated_duration_minutes")
    op.drop_column("OrdresTravail", "completed_at")
    op.drop_column("OrdresTravail", "assigned_at")
    op.drop_column("OrdresTravail", "validated_at")
    op.drop_column("OrdresTravail", "validated_by_id")
    op.drop_column("OrdresTravail", "created_by_id")

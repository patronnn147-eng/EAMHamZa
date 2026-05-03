"""Add planning_taches table for CHEFTECH execution tasks

Revision ID: add_planning_taches
Revises: 3d8edf736d26
Create Date: 2026-04-29
"""

from alembic import op
import sqlalchemy as sa


revision = "add_planning_taches"
down_revision = "3d8edf736d26"
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    result = bind.execute(
        sa.text(
            "SELECT 1 FROM information_schema.tables WHERE table_name = :t"
        ),
        {"t": table_name},
    )
    return result.first() is not None


def _index_exists(index_name: str) -> bool:
    bind = op.get_bind()
    result = bind.execute(
        sa.text("SELECT 1 FROM pg_indexes WHERE indexname = :i"),
        {"i": index_name},
    )
    return result.first() is not None


def upgrade() -> None:
    if not _table_exists("planning_taches"):
        op.create_table(
            "planning_taches",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
            sa.Column("planning_id", sa.Integer(), nullable=False),
            sa.Column("titre", sa.String(length=255), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("technicien_id", sa.Integer(), nullable=False),
            sa.Column("machine_id", sa.Integer(), nullable=False),
            sa.Column(
                "task_type",
                sa.Enum("DIAGNOSTIC", "CORRECTION", name="tasktype"),
                nullable=False,
            ),
            sa.Column("date_debut", sa.DateTime(timezone=True), nullable=False),
            sa.Column("date_fin", sa.DateTime(timezone=True), nullable=False),
            sa.Column("created_by", sa.Integer(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
        )

    if not _index_exists("ix_planning_taches_planning_id"):
        op.create_index(
            "ix_planning_taches_planning_id",
            "planning_taches",
            ["planning_id"],
            unique=False,
        )


def downgrade() -> None:
    if _index_exists("ix_planning_taches_planning_id"):
        op.drop_index("ix_planning_taches_planning_id", table_name="planning_taches")
    if _table_exists("planning_taches"):
        op.drop_table("planning_taches")
    bind = op.get_bind()
    bind.execute(sa.text("DROP TYPE IF EXISTS tasktype"))

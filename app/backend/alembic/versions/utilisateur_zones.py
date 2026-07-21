"""add utilisateur_zones table for multi-zone CHEFTECH/TECHNICIEN assignment

Revision ID: utilisateur_zones
Revises: machine_status_change_requests
Create Date: 2026-07-21
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "utilisateur_zones"
down_revision: Union[str, Sequence[str], None] = "machine_status_change_requests"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    result = bind.execute(
        sa.text(
            "SELECT 1 FROM information_schema.tables WHERE table_name = :t"
        ),
        {"t": table_name},
    )
    return result.first() is not None


def upgrade() -> None:
    if _table_exists("utilisateur_zones"):
        return
    op.create_table(
        "utilisateur_zones",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "utilisateur_id",
            sa.Integer(),
            sa.ForeignKey("utilisateurs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("zone", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index(
        "ix_utilisateur_zones_utilisateur_id",
        "utilisateur_zones",
        ["utilisateur_id"],
    )
    op.create_index(
        "ix_utilisateur_zones_zone", "utilisateur_zones", ["zone"]
    )
    op.create_unique_constraint(
        "uq_utilisateur_zones_user_zone",
        "utilisateur_zones",
        ["utilisateur_id", "zone"],
    )


def downgrade() -> None:
    op.drop_table("utilisateur_zones")

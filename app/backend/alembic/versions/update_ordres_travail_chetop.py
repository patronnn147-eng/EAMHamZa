"""Update ordres_travail table for CHETOP functionality

Revision ID: update_ordres_travail_chetop
Revises: standardize_utilisateurs_schema
Create Date: 2026-01-28 18:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "update_ordres_travail_chetop"
down_revision = "standardize_utilisateurs"
branch_labels = None
depends_on = None


def upgrade():
    """Update ordres_travail table to match CHETOP requirements"""

    # Add new columns for CHETOP functionality
    op.add_column("ordres_travail", sa.Column("titre", sa.String(255), nullable=False))
    op.add_column("ordres_travail", sa.Column("description", sa.Text(), nullable=False))
    op.add_column(
        "ordres_travail",
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Drop old ordre_id column if it exists
    op.drop_column("ordres_travail", "ordre_id", nullable=True)

    # Update default values
    op.alter_column(
        "ordres_travail",
        "priorite",
        existing_type=sa.String(),
        server_default="MOYENNE",
        nullable=False,
    )

    op.alter_column(
        "ordres_travail",
        "statut",
        existing_type=sa.String(),
        server_default="EN_ATTENTE",
        nullable=False,
    )

    op.alter_column(
        "ordres_travail",
        "date_echeance",
        existing_type=sa.DateTime(timezone=True),
        nullable=True,
    )

    op.alter_column(
        "ordres_travail", "utilisateur_id", existing_type=sa.Integer(), nullable=True
    )

    # Make created_at not nullable with default
    op.alter_column(
        "ordres_travail",
        "created_at",
        existing_type=sa.DateTime(timezone=True),
        server_default=sa.text("now()"),
        nullable=False,
    )


def downgrade():
    """Revert changes to ordres_travail table"""

    # Add back old ordre_id column
    op.add_column("ordres_travail", sa.Column("ordre_id", sa.Integer(), nullable=True))

    # Drop new columns
    op.drop_column("ordres_travail", "titre")
    op.drop_column("ordres_travail", "description")
    op.drop_column("ordres_travail", "updated_at")

    # Revert old column constraints
    op.alter_column(
        "ordres_travail",
        "date_echeance",
        existing_type=sa.DateTime(timezone=True),
        nullable=False,
    )

    op.alter_column(
        "ordres_travail", "utilisateur_id", existing_type=sa.Integer(), nullable=False
    )

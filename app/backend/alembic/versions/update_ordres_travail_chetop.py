"""Update OrdresTravail table for CHETOP functionality

Revision ID: update_OrdresTravail_chetop
Revises: standardize_utilisateurs_schema
Create Date: 2026-01-28 18:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "update_OrdresTravail_chetop"
down_revision = "standardize_utilisateurs"
branch_labels = None
depends_on = None


def upgrade():
    """Update OrdresTravail table to match CHETOP requirements"""

    # Add new columns for CHETOP functionality
    op.add_column("OrdresTravail", sa.Column("titre", sa.String(255), nullable=False))
    op.add_column("OrdresTravail", sa.Column("description", sa.Text(), nullable=False))
    op.add_column(
        "OrdresTravail",
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Drop old ordre_id column if it exists
    op.drop_column("OrdresTravail", "ordre_id", nullable=True)

    # Update default values
    op.alter_column(
        "OrdresTravail",
        "priorite",
        existing_type=sa.String(),
        server_default="MOYENNE",
        nullable=False,
    )

    op.alter_column(
        "OrdresTravail",
        "statut",
        existing_type=sa.String(),
        server_default="EN_ATTENTE",
        nullable=False,
    )

    op.alter_column(
        "OrdresTravail",
        "date_echeance",
        existing_type=sa.DateTime(timezone=True),
        nullable=True,
    )

    op.alter_column(
        "OrdresTravail", "utilisateur_id", existing_type=sa.Integer(), nullable=True
    )

    # Make created_at not nullable with default
    op.alter_column(
        "OrdresTravail",
        "created_at",
        existing_type=sa.DateTime(timezone=True),
        server_default=sa.text("now()"),
        nullable=False,
    )


def downgrade():
    """Revert changes to OrdresTravail table"""

    # Add back old ordre_id column
    op.add_column("OrdresTravail", sa.Column("ordre_id", sa.Integer(), nullable=True))

    # Drop new columns
    op.drop_column("OrdresTravail", "titre")
    op.drop_column("OrdresTravail", "description")
    op.drop_column("OrdresTravail", "updated_at")

    # Revert old column constraints
    op.alter_column(
        "OrdresTravail",
        "date_echeance",
        existing_type=sa.DateTime(timezone=True),
        nullable=False,
    )

    op.alter_column(
        "OrdresTravail", "utilisateur_id", existing_type=sa.Integer(), nullable=False
    )

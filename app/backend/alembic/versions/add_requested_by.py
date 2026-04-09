"""Add requested_by column to Ordres_intervention

Revision ID: add_requested_by
Revises: more_perf_indexes_v2
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_requested_by'
down_revision = 'more_perf_indexes_v2'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Use IF NOT EXISTS to avoid errors if column already added in a previous run.
    op.execute("ALTER TABLE ordres_intervention ADD COLUMN IF NOT EXISTS requested_by INTEGER")

def downgrade() -> None:
    # Drop the column if it exists.
    op.execute("ALTER TABLE ordres_intervention DROP COLUMN IF EXISTS requested_by")
"""Standardize utilisateurs schema to use id, nom, email, mot_de_passe, role

Revision ID: standardize_utilisateurs
Revises: db0b16342160
Create Date: 2026-01-28 15:19:24.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'standardize_utilisateurs'
down_revision: Union[str, Sequence[str], None] = 'db0b16342160'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: standardize utilisateurs table."""
    conn = op.get_bind()

    # Add columns only if they don't already exist (idempotent)
    for col_name, col_type in [('nom', 'VARCHAR(255)'), ('email', 'VARCHAR(255)'), ('mot_de_passe', 'VARCHAR(255)')]:
        exists = conn.execute(
            sa.text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_name='utilisateurs' AND column_name=:col"
            ),
            {"col": col_name}
        ).fetchone()
        if not exists:
            op.add_column('utilisateurs', sa.Column(col_name, sa.String(255), nullable=True))

    # Ensure values are not null
    op.execute(sa.text('''
        UPDATE utilisateurs
        SET nom = COALESCE(nom, ''),
            email = COALESCE(email, ''),
            mot_de_passe = COALESCE(mot_de_passe, '')
    '''))

    # Make columns NOT NULL
    op.alter_column('utilisateurs', 'nom', nullable=False)
    op.alter_column('utilisateurs', 'email', nullable=False)
    op.alter_column('utilisateurs', 'mot_de_passe', nullable=False)

    # Add unique constraint on email if it doesn't exist
    constraint_exists = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.table_constraints "
            "WHERE constraint_name='uq_utilisateurs_email' AND table_name='utilisateurs'"
        )
    ).fetchone()
    if not constraint_exists:
        op.create_unique_constraint('uq_utilisateurs_email', 'utilisateurs', ['email'])

    # Add index on email if it doesn't exist
    index_exists = conn.execute(
        sa.text(
            "SELECT 1 FROM pg_indexes "
            "WHERE tablename='utilisateurs' AND indexname='ix_utilisateurs_email'"
        )
    ).fetchone()
    if not index_exists:
        op.create_index('ix_utilisateurs_email', 'utilisateurs', ['email'], unique=False)


def downgrade() -> None:
    """Downgrade schema: restore old utilisateurs columns."""
    # Add back old columns
    op.add_column('utilisateurs', sa.Column('id', sa.String(), nullable=False, server_default=''))
    op.add_column('utilisateurs', sa.Column('nom', sa.String(), nullable=False, server_default=''))
    op.add_column('utilisateurs', sa.Column('mot_de_passe', sa.String(), nullable=False, server_default=''))
    op.add_column('utilisateurs', sa.Column('email', sa.String(), nullable=False, server_default=''))
    op.add_column('utilisateurs', sa.Column('created_at', sa.DateTime(timezone=True), nullable=True))
    
    # Copy data back from new columns to old ones
    op.execute('''
        UPDATE utilisateurs 
        SET nom = COALESCE(nom, ''),
            email = COALESCE(email, ''),
            mot_de_passe = COALESCE(mot_de_passe, '')
    ''')
    
    # Drop new columns
    op.drop_constraint('uq_utilisateurs_email', 'utilisateurs', type_='unique')
    op.drop_index('ix_utilisateurs_email', table_name='utilisateurs')
    op.drop_column('utilisateurs', 'nom')
    op.drop_column('utilisateurs', 'email')
    op.drop_column('utilisateurs', 'mot_de_passe')

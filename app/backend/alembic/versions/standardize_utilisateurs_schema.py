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
    # Add new columns
    op.add_column('utilisateurs', sa.Column('nom', sa.String(255), nullable=True))
    op.add_column('utilisateurs', sa.Column('email', sa.String(255), nullable=True))
    op.add_column('utilisateurs', sa.Column('mot_de_passe', sa.String(255), nullable=True))
    
    # Copy data from old columns to new ones
    op.execute('''
        UPDATE utilisateurs 
        SET nom = COALESCE(nom, ''),
            email = COALESCE(email, ''),
            mot_de_passe = COALESCE(mot_de_passe, '')
    ''')
    
    # Make new columns NOT NULL
    op.alter_column('utilisateurs', 'nom', nullable=False)
    op.alter_column('utilisateurs', 'email', nullable=False)
    op.alter_column('utilisateurs', 'mot_de_passe', nullable=False)
    
    # Add unique constraint on email
    op.create_unique_constraint('uq_utilisateurs_email', 'utilisateurs', ['email'])
    
    # Add index on email
    op.create_index('ix_utilisateurs_email', 'utilisateurs', ['email'], unique=False)
    
    # Drop old columns
    op.drop_column('utilisateurs', 'id')
    op.drop_column('utilisateurs', 'nom')
    op.drop_column('utilisateurs', 'mot_de_passe')
    op.drop_column('utilisateurs', 'email')
    op.drop_column('utilisateurs', 'created_at')


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
            mot_de_passe = COALESCE(mot_de_passe, ''),
    ''')
    
    # Drop new columns
    op.drop_constraint('uq_utilisateurs_email', 'utilisateurs', type_='unique')
    op.drop_index('ix_utilisateurs_email', table_name='utilisateurs')
    op.drop_column('utilisateurs', 'nom')
    op.drop_column('utilisateurs', 'email')
    op.drop_column('utilisateurs', 'mot_de_passe')

"""add status and shift type to utilisateurs

Revision ID: b9e76d0812f5
Revises: b7c8d9e0f1a3
Create Date: 2026-03-28 14:28:15.123456

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b9e76d0812f5'
down_revision: Union[str, Sequence[str], None] = 'b7c8d9e0f1a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create ENUM types first
    userstatus = postgresql.ENUM('PENDING', 'APPROVED', 'REJECTED', name='userstatus')
    userstatus.create(op.get_bind(), checkfirst=True)
    
    usershifttype = postgresql.ENUM('MORNING', 'NIGHT', name='usershifttype')
    usershifttype.create(op.get_bind(), checkfirst=True)

    # Use raw SQL to make it idempotent
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='utilisateurs' AND column_name='status') THEN
                ALTER TABLE utilisateurs ADD COLUMN status userstatus NOT NULL DEFAULT 'PENDING';
            END IF;
            
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='utilisateurs' AND column_name='shift_type') THEN
                ALTER TABLE utilisateurs ADD COLUMN shift_type usershifttype NOT NULL DEFAULT 'MORNING';
            END IF;
            
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='utilisateurs' AND column_name='updated_at') THEN
                ALTER TABLE utilisateurs ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();
            END IF;
        END $$;
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE utilisateurs DROP COLUMN IF EXISTS status;
        ALTER TABLE utilisateurs DROP COLUMN IF EXISTS shift_type;
        ALTER TABLE utilisateurs DROP COLUMN IF EXISTS updated_at;
    """)
    
    userstatus = postgresql.ENUM('PENDING', 'APPROVED', 'REJECTED', name='userstatus')
    userstatus.drop(op.get_bind(), checkfirst=True)
    
    usershifttype = postgresql.ENUM('MORNING', 'NIGHT', name='usershifttype')
    usershifttype.drop(op.get_bind(), checkfirst=True)

"""Add machine telemetry sensor columns

Revision ID: add_machine_telemetry_columns
Revises: add_pdca_ml_tables
Create Date: 2026-03-01

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


revision: str = "add_machine_telemetry_columns"
down_revision: Union[str, Sequence[str], None] = "add_pdca_ml_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if not _column_exists("machines", "air_temperature"):
        op.add_column("machines", sa.Column("air_temperature", sa.Float(), nullable=True, server_default="300.0"))
    
    if not _column_exists("machines", "process_temperature"):
        op.add_column("machines", sa.Column("process_temperature", sa.Float(), nullable=True, server_default="310.0"))
        
    if not _column_exists("machines", "rotational_speed"):
        op.add_column("machines", sa.Column("rotational_speed", sa.Integer(), nullable=True, server_default="1500"))
        
    if not _column_exists("machines", "torque"):
        op.add_column("machines", sa.Column("torque", sa.Float(), nullable=True, server_default="40.0"))
        
    if not _column_exists("machines", "tool_wear"):
        op.add_column("machines", sa.Column("tool_wear", sa.Integer(), nullable=True, server_default="0"))


def downgrade() -> None:
    op.drop_column("machines", "tool_wear")
    op.drop_column("machines", "torque")
    # op.drop_column("machines", "rotational_speed")
    # op.drop_column("machines", "process_temperature")
    # op.drop_column("machines", "air_temperature")
    # Dropping them one by one for safety
    op.drop_column("machines", "rotational_speed")
    op.drop_column("machines", "process_temperature")
    op.drop_column("machines", "air_temperature")

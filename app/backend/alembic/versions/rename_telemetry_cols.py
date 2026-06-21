"""Rename machine_telemetry_logs columns and drop machines telemetry columns

Revision ID: rename_telemetry_cols
Revises: add_machine_telemetry_columns
Create Date: 2026-04-16
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "rename_telemetry_cols"
down_revision: Union[str, Sequence[str], None] = "add_machine_telemetry_columns"
branch_labels = None
depends_on = None


def _col_exists(table: str, col: str) -> bool:
    bind = op.get_bind()
    r = bind.execute(
        sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name=:t AND column_name=:c"
        ),
        {"t": table, "c": col},
    )
    return r.first() is not None


def upgrade() -> None:
    # --- machine_telemetry_logs: rename placeholder cols ---
    renames = [
        ("temperature", "air_temperature"),
        ("vibration", "process_temperature"),
        ("rpm", "rotational_speed"),
        ("power", "tool_wear"),
    ]
    for old, new in renames:
        old_exists = _col_exists("machine_telemetry_logs", old)
        new_exists = _col_exists("machine_telemetry_logs", new)
        if old_exists and not new_exists:
            op.alter_column("machine_telemetry_logs", old, new_column_name=new)
        elif old_exists and new_exists:
            # Both columns exist (partial migration state) — drop the legacy one
            op.drop_column("machine_telemetry_logs", old)
        # if only new_exists or neither: already done, skip

    # --- machines: drop static telemetry columns ---
    for col in [
        "air_temperature",
        "process_temperature",
        "rotational_speed",
        "torque",
        "tool_wear",
    ]:
        if _col_exists("machines", col):
            op.drop_column("machines", col)


def downgrade() -> None:
    # Restore machines columns
    op.add_column("machines", sa.Column("air_temperature", sa.Float(), nullable=True))
    op.add_column(
        "machines", sa.Column("process_temperature", sa.Float(), nullable=True)
    )
    op.add_column(
        "machines", sa.Column("rotational_speed", sa.Integer(), nullable=True)
    )
    op.add_column("machines", sa.Column("torque", sa.Float(), nullable=True))
    op.add_column("machines", sa.Column("tool_wear", sa.Integer(), nullable=True))
    # Reverse renames on machine_telemetry_logs
    renames = [
        ("air_temperature", "temperature"),
        ("process_temperature", "vibration"),
        ("rotational_speed", "rpm"),
        ("tool_wear", "power"),
    ]
    for old, new in renames:
        if _col_exists("machine_telemetry_logs", old):
            op.alter_column("machine_telemetry_logs", old, new_column_name=new)

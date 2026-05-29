"""Make stock.quantity DECIMAL(10,2) for consumable fractional units

Revision ID: inventory_stock_decimal
Revises: inventory_consumption_workflow
Create Date: 2026-05-17

Follow-up to inventory_consumption_workflow: the parent migration converted
``mouvement_stock.quantity`` but missed ``stock.quantity``, causing fractional
values (e.g. 0.5 L) to be truncated when written back to stock.
"""
from alembic import op
import sqlalchemy as sa


revision = "inventory_stock_decimal"
down_revision = "inventory_consumption_workflow"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "stock",
        "quantity",
        existing_type=sa.Integer(),
        type_=sa.Numeric(10, 2),
        postgresql_using="quantity::numeric(10,2)",
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "stock",
        "quantity",
        existing_type=sa.Numeric(10, 2),
        type_=sa.Integer(),
        postgresql_using="quantity::integer",
        existing_nullable=False,
    )

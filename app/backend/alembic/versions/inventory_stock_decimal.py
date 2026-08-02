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
    bind = op.get_bind()
    # `stock` was never created by any tracked migration -- only ever
    # existed via untracked dev-DB drift. On a fresh database, create it
    # directly with the final Numeric(10,2) type and skip the conversion.
    table_exists = bind.execute(
        sa.text("SELECT 1 FROM information_schema.tables WHERE table_name='stock'")
    ).first()
    if table_exists:
        op.alter_column(
            "stock",
            "quantity",
            existing_type=sa.Integer(),
            type_=sa.Numeric(10, 2),
            postgresql_using="quantity::numeric(10,2)",
            existing_nullable=False,
        )
    else:
        op.create_table(
            "stock",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column(
                "piece_id", sa.Integer(), sa.ForeignKey("pieces.id"), nullable=False
            ),
            sa.Column("quantity", sa.Numeric(10, 2), nullable=False, server_default=sa.text("0")),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
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

"""Inventory consumption workflow — reservations, consumed pieces, pending pieces

Revision ID: inventory_consumption_workflow
Revises: add_pgvector_rag
Create Date: 2026-05-17

Adds the inventory ↔ work-order consumption workflow:
- Extends `pieces` with `is_consumable`, `default_unit`
- Extends `mouvement_stock` for DECIMAL quantities, units, new movement types,
  and nullable piece_id (so pending-piece placeholder movements can exist
  before their piece is resolved).
- Extends `ordres_intervention` with `parts_approved` flag and renames
  `parts_replaced` to `legacy_parts_text` (kept for old records only).
- Creates `required_pieces`, `consumed_pieces`, `pending_pieces` tables with
  CHECK constraints and indexes.
- Enables pg_trgm for fuzzy piece-name matching.
- Creates a `intervention_consumption_summary` VIEW used as the single source
  of truth for consumed-parts JSON reports.
"""
from alembic import op
import sqlalchemy as sa


revision = "inventory_consumption_workflow"
down_revision = "add_pgvector_rag"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Extensions ────────────────────────────────────────────────────────────
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # ── pieces: add columns ──────────────────────────────────────────────────
    with op.batch_alter_table("pieces") as batch:
        batch.add_column(sa.Column("is_consumable", sa.Boolean(), nullable=False, server_default=sa.text("false")))
        batch.add_column(sa.Column("default_unit", sa.String(20), nullable=False, server_default="pcs"))

    op.create_index("idx_pieces_name_trgm", "pieces", [sa.text("name gin_trgm_ops")], postgresql_using="gin")
    op.create_index("idx_pieces_reference_trgm", "pieces", [sa.text("reference gin_trgm_ops")], postgresql_using="gin")

    # ── mouvement_stock: extend ──────────────────────────────────────────────
    # Drop NOT NULL on piece_id (pending pieces have no piece_id yet)
    op.alter_column("mouvement_stock", "piece_id", existing_type=sa.Integer(), nullable=True)
    # Convert quantity to DECIMAL
    op.alter_column(
        "mouvement_stock",
        "quantity",
        existing_type=sa.Integer(),
        type_=sa.Numeric(10, 2),
        postgresql_using="quantity::numeric(10,2)",
    )
    # Add unit + pending_piece_id + intervention_id
    op.add_column("mouvement_stock", sa.Column("unit", sa.String(20), nullable=False, server_default="pcs"))
    op.add_column("mouvement_stock", sa.Column("intervention_id", sa.Integer(), nullable=True))
    # pending_piece_id added AFTER pending_pieces table exists (see below)

    # ── ordres_intervention: parts_approved + rename ─────────────────────────
    op.add_column(
        "ordres_intervention",
        sa.Column("parts_approved", sa.Boolean(), nullable=True),
    )
    # Keep parts_replaced as legacy_parts_text — preserve existing data
    op.alter_column(
        "ordres_intervention",
        "parts_replaced",
        new_column_name="legacy_parts_text",
        existing_type=sa.Text(),
    )

    # ── pending_pieces ───────────────────────────────────────────────────────
    op.create_table(
        "pending_pieces",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("intervention_id", sa.Integer(), sa.ForeignKey("ordres_intervention.id", ondelete="SET NULL"), nullable=True),
        sa.Column("submitted_by", sa.Integer(), sa.ForeignKey("utilisateurs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("category", sa.String(50), nullable=True),
        sa.Column("quantity", sa.Numeric(10, 2), nullable=False),
        sa.Column("unit", sa.String(20), nullable=False, server_default="pcs"),
        sa.Column("photo_object_key", sa.String(500), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING_REVIEW"),
        sa.Column("matched_piece_id", sa.Integer(), sa.ForeignKey("pieces.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reviewed_by", sa.Integer(), sa.ForeignKey("utilisateurs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("quantity > 0", name="ck_pending_pieces_qty_positive"),
        sa.CheckConstraint(
            "status IN ('PENDING_REVIEW', 'MATCHED', 'CREATED', 'REJECTED')",
            name="ck_pending_pieces_status_valid",
        ),
    )
    op.create_index(
        "idx_pending_pieces_pending",
        "pending_pieces",
        ["status"],
        postgresql_where=sa.text("status = 'PENDING_REVIEW'"),
    )
    op.create_index("idx_pending_pieces_name_trgm", "pending_pieces", [sa.text("name gin_trgm_ops")], postgresql_using="gin")

    # Now add the FK column on mouvement_stock that references pending_pieces
    op.add_column(
        "mouvement_stock",
        sa.Column(
            "pending_piece_id",
            sa.Integer(),
            sa.ForeignKey("pending_pieces.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    # Extended movement_type CHECK
    # 'in' + 'out' = existing types; new ones added
    op.create_check_constraint(
        "ck_mouvement_stock_type_valid",
        "mouvement_stock",
        "movement_type IN ('in', 'out', 'PENDING_OUT', 'RESERVED', 'RESERVATION_RELEASED', 'REJECTED')",
    )
    # Either piece_id OR pending_piece_id must be present
    op.create_check_constraint(
        "ck_mouvement_stock_piece_or_pending",
        "mouvement_stock",
        "(piece_id IS NOT NULL) OR (pending_piece_id IS NOT NULL)",
    )

    op.create_index("idx_mouvement_stock_intervention", "mouvement_stock", ["intervention_id"])
    op.create_index("idx_mouvement_stock_pending", "mouvement_stock", ["pending_piece_id"])
    op.create_index(
        "idx_mouvement_stock_active_reservations",
        "mouvement_stock",
        ["piece_id"],
        postgresql_where=sa.text("movement_type = 'RESERVED'"),
    )

    # ── required_pieces ──────────────────────────────────────────────────────
    op.create_table(
        "required_pieces",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "intervention_id",
            sa.Integer(),
            sa.ForeignKey("ordres_intervention.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("piece_id", sa.Integer(), sa.ForeignKey("pieces.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("quantity_planned", sa.Numeric(10, 2), nullable=False),
        sa.Column("unit", sa.String(20), nullable=False, server_default="pcs"),
        sa.Column("quantity_reserved", sa.Numeric(10, 2), nullable=False, server_default=sa.text("0")),
        sa.Column("reservation_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved", sa.Boolean(), nullable=True),  # NULL=pending, True=approved, False=rejected
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("quantity_planned >= 0 AND quantity_reserved >= 0", name="ck_required_pieces_non_negative"),
        sa.CheckConstraint("quantity_reserved <= quantity_planned", name="ck_required_pieces_reserve_le_plan"),
    )
    op.create_index("idx_required_pieces_itv", "required_pieces", ["intervention_id"])
    op.create_index("idx_required_pieces_piece", "required_pieces", ["piece_id"])
    op.create_index(
        "idx_required_pieces_active_reservation",
        "required_pieces",
        ["piece_id"],
        postgresql_where=sa.text("quantity_reserved > 0"),
    )

    # ── consumed_pieces ──────────────────────────────────────────────────────
    op.create_table(
        "consumed_pieces",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "intervention_id",
            sa.Integer(),
            sa.ForeignKey("ordres_intervention.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "required_piece_id",
            sa.Integer(),
            sa.ForeignKey("required_pieces.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("piece_id", sa.Integer(), sa.ForeignKey("pieces.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("quantity_used", sa.Numeric(10, 2), nullable=False, server_default=sa.text("0")),
        sa.Column("quantity_returned", sa.Numeric(10, 2), nullable=False, server_default=sa.text("0")),
        sa.Column("quantity_wasted", sa.Numeric(10, 2), nullable=False, server_default=sa.text("0")),
        sa.Column("unit", sa.String(20), nullable=False, server_default="pcs"),
        sa.Column("disposition", sa.String(20), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "quantity_used >= 0 AND quantity_returned >= 0 AND quantity_wasted >= 0",
            name="ck_consumed_pieces_non_negative",
        ),
        sa.CheckConstraint(
            "disposition IN ('used', 'partial', 'not_used', 'wasted', 'returned')",
            name="ck_consumed_pieces_disposition_valid",
        ),
    )
    op.create_index("idx_consumed_pieces_itv", "consumed_pieces", ["intervention_id"])
    op.create_index("idx_consumed_pieces_piece", "consumed_pieces", ["piece_id"])
    op.create_index("idx_consumed_pieces_required", "consumed_pieces", ["required_piece_id"])

    # Cross-table CHECK enforced via trigger (Postgres CHECKs can't subquery)
    op.execute(
        """
        CREATE OR REPLACE FUNCTION fn_check_consumed_le_planned()
        RETURNS TRIGGER AS $$
        DECLARE
            planned NUMERIC(10,2);
            total NUMERIC(10,2);
        BEGIN
            SELECT quantity_planned INTO planned
            FROM required_pieces
            WHERE id = NEW.required_piece_id;

            total := COALESCE(NEW.quantity_used, 0)
                   + COALESCE(NEW.quantity_returned, 0)
                   + COALESCE(NEW.quantity_wasted, 0);

            IF planned IS NOT NULL AND total > planned THEN
                RAISE EXCEPTION
                    'Consumed quantity (%) exceeds planned (%) for required_piece %',
                    total, planned, NEW.required_piece_id
                USING ERRCODE = 'check_violation';
            END IF;

            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_consumed_le_planned
        BEFORE INSERT OR UPDATE ON consumed_pieces
        FOR EACH ROW EXECUTE FUNCTION fn_check_consumed_le_planned();
        """
    )

    # ── VIEW: intervention_consumption_summary (single source of truth) ──────
    op.execute(
        """
        CREATE OR REPLACE VIEW intervention_consumption_summary AS
        SELECT
            cp.intervention_id,
            json_agg(
                json_build_object(
                    'consumed_piece_id', cp.id,
                    'piece_id',          cp.piece_id,
                    'piece_name',        p.name,
                    'piece_reference',   p.reference,
                    'used',              cp.quantity_used,
                    'returned',          cp.quantity_returned,
                    'wasted',            cp.quantity_wasted,
                    'unit',              cp.unit,
                    'disposition',       cp.disposition,
                    'notes',             cp.notes,
                    'created_at',        cp.created_at
                )
                ORDER BY cp.id
            ) AS parts_replaced_json
        FROM consumed_pieces cp
        JOIN pieces p ON p.id = cp.piece_id
        GROUP BY cp.intervention_id;
        """
    )


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS intervention_consumption_summary")
    op.execute("DROP TRIGGER IF EXISTS trg_consumed_le_planned ON consumed_pieces")
    op.execute("DROP FUNCTION IF EXISTS fn_check_consumed_le_planned()")

    op.drop_index("idx_consumed_pieces_required", table_name="consumed_pieces")
    op.drop_index("idx_consumed_pieces_piece", table_name="consumed_pieces")
    op.drop_index("idx_consumed_pieces_itv", table_name="consumed_pieces")
    op.drop_table("consumed_pieces")

    op.drop_index("idx_required_pieces_active_reservation", table_name="required_pieces")
    op.drop_index("idx_required_pieces_piece", table_name="required_pieces")
    op.drop_index("idx_required_pieces_itv", table_name="required_pieces")
    op.drop_table("required_pieces")

    op.drop_index("idx_mouvement_stock_active_reservations", table_name="mouvement_stock")
    op.drop_index("idx_mouvement_stock_pending", table_name="mouvement_stock")
    op.drop_index("idx_mouvement_stock_intervention", table_name="mouvement_stock")
    op.drop_constraint("ck_mouvement_stock_piece_or_pending", "mouvement_stock", type_="check")
    op.drop_constraint("ck_mouvement_stock_type_valid", "mouvement_stock", type_="check")
    op.drop_column("mouvement_stock", "pending_piece_id")

    op.drop_index("idx_pending_pieces_name_trgm", table_name="pending_pieces")
    op.drop_index("idx_pending_pieces_pending", table_name="pending_pieces")
    op.drop_table("pending_pieces")

    op.alter_column(
        "ordres_intervention",
        "legacy_parts_text",
        new_column_name="parts_replaced",
        existing_type=sa.Text(),
    )
    op.drop_column("ordres_intervention", "parts_approved")

    op.drop_column("mouvement_stock", "intervention_id")
    op.drop_column("mouvement_stock", "unit")
    op.alter_column(
        "mouvement_stock",
        "quantity",
        existing_type=sa.Numeric(10, 2),
        type_=sa.Integer(),
        postgresql_using="quantity::integer",
    )
    op.alter_column("mouvement_stock", "piece_id", existing_type=sa.Integer(), nullable=False)

    op.drop_index("idx_pieces_reference_trgm", table_name="pieces")
    op.drop_index("idx_pieces_name_trgm", table_name="pieces")
    with op.batch_alter_table("pieces") as batch:
        batch.drop_column("default_unit")
        batch.drop_column("is_consumable")

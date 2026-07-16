"""add performance indexes

Revision ID: new_perf_indexes
Revises: 55c181562e1e
Create Date: 2026-04-02 13:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "new_perf_indexes"
down_revision: Union[str, None] = "55c181562e1e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    indexes_to_create = [
        ("idx_OrdresTravail_utilisateur_id", "OrdresTravail", ["utilisateur_id"]),
        ("idx_OrdresTravail_machine_id", "OrdresTravail", ["machine_id"]),
        ("idx_OrdresTravail_statut", "OrdresTravail", ["statut"]),
        ("idx_interventions_machine_id", "OrdresIntervention", ["machine_id"]),
        ("idx_interventions_created_at", "OrdresIntervention", ["created_at"]),
        ("idx_notifications_utilisateur_id", "notifications", ["utilisateur_id"]),
        ("idx_notifications_lu", "notifications", ["lu"]),
    ]

    for idx_name, table_name, columns in indexes_to_create:
        result = conn.execute(
            sa.text(
                "SELECT 1 FROM pg_indexes WHERE schemaname = 'public' AND indexname = :idx_name"
            ),
            {"idx_name": idx_name},
        )
        if not result.first():
            op.create_index(idx_name, table_name, columns)


def downgrade() -> None:
    op.drop_index("idx_notifications_lu", table_name="notifications")
    op.drop_index("idx_notifications_utilisateur_id", table_name="notifications")
    op.drop_index("idx_interventions_created_at", table_name="OrdresIntervention")
    op.drop_index("idx_interventions_machine_id", table_name="OrdresIntervention")
    op.drop_index("idx_OrdresTravail_statut", table_name="OrdresTravail")
    op.drop_index("idx_OrdresTravail_machine_id", table_name="OrdresTravail")
    op.drop_index("idx_OrdresTravail_utilisateur_id", table_name="OrdresTravail")

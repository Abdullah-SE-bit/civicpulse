"""create complaints table

Revision ID: 0001
Revises:
"""
import sqlalchemy as sa

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

CATEGORIES = "('water','electricity','sanitation','roads','streetlights','other')"
PRIORITIES = "('high','normal','low')"
STATUSES = "('open','in_progress','resolved','rejected')"
TRIAGED_BY = "('llm:groq','llm:gemini','llm:ollama','rules','rules:fallback','simulated')"


def upgrade() -> None:
    op.create_table(
        "complaints",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("location", sa.String(200), nullable=False),
        sa.Column("reporter_contact", sa.String(200), nullable=True),
        sa.Column("category", sa.String(20), nullable=False),
        sa.Column("priority", sa.String(10), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),
        sa.Column("ai_summary", sa.String(140), nullable=True),
        sa.Column("triaged_by", sa.String(30), nullable=False),
        sa.Column("triage_latency_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("length(text) BETWEEN 10 AND 2000", name="ck_complaints_text_len"),
        sa.CheckConstraint("length(location) BETWEEN 3 AND 200", name="ck_complaints_location_len"),
        sa.CheckConstraint(f"category IN {CATEGORIES}", name="ck_complaints_category"),
        sa.CheckConstraint(f"priority IN {PRIORITIES}", name="ck_complaints_priority"),
        sa.CheckConstraint(f"status IN {STATUSES}", name="ck_complaints_status"),
        sa.CheckConstraint(f"triaged_by IN {TRIAGED_BY}", name="ck_complaints_triaged_by"),
        sa.CheckConstraint("ai_summary IS NULL OR length(ai_summary) <= 140", name="ck_complaints_summary_len"),
    )
    # Serves the dashboard filter: WHERE status = ? [AND priority = ?] and stats GROUP BY.
    op.create_index("ix_complaints_status_priority", "complaints", ["status", "priority"])
    # Serves the dashboard ordering: ORDER BY created_at DESC LIMIT/OFFSET, and /api/meta/providers.
    op.create_index("ix_complaints_created_at", "complaints", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_complaints_created_at", table_name="complaints")
    op.drop_index("ix_complaints_status_priority", table_name="complaints")
    op.drop_table("complaints")

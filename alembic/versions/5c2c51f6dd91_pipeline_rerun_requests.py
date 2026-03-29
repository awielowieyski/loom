"""pipeline rerun requests

Revision ID: 5c2c51f6dd91
Revises: 1b0f2c7a9d44
Create Date: 2026-03-28 20:10:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "5c2c51f6dd91"
down_revision: str | Sequence[str] | None = "1b0f2c7a9d44"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "pipeline_run_requests",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("skill_id", sa.UUID(), nullable=True),
        sa.Column("artifact_id", sa.UUID(), nullable=True),
        sa.Column("request_mode", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), server_default="pending", nullable=False),
        sa.Column("requested_via", sa.Text(), server_default="dashboard", nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "result_summary",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["artifact_id"], ["source_artifacts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["skill_id"], ["skills.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_pipeline_run_requests_skill",
        "pipeline_run_requests",
        ["skill_id"],
        unique=False,
    )
    op.create_index(
        "idx_pipeline_run_requests_status",
        "pipeline_run_requests",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_pipeline_run_requests_status", table_name="pipeline_run_requests")
    op.drop_index("idx_pipeline_run_requests_skill", table_name="pipeline_run_requests")
    op.drop_table("pipeline_run_requests")

"""external services and pricing evidence

Revision ID: 1b0f2c7a9d44
Revises: 2f6d72fd9b63
Create Date: 2026-03-28 18:45:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "1b0f2c7a9d44"
down_revision: str | Sequence[str] | None = "2f6d72fd9b63"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "external_services",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("service_key", sa.Text(), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("vendor_name", sa.Text(), nullable=True),
        sa.Column("service_type", sa.Text(), server_default="other", nullable=False),
        sa.Column("homepage_url", sa.Text(), nullable=True),
        sa.Column("docs_url", sa.Text(), nullable=True),
        sa.Column("pricing_url", sa.Text(), nullable=True),
        sa.Column(
            "default_auth_methods",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "default_env_vars",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "metadata",
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
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("service_key"),
    )

    op.create_table(
        "skill_service_dependencies",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("skill_version_id", sa.UUID(), nullable=False),
        sa.Column("service_id", sa.UUID(), nullable=False),
        sa.Column("required", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("dependency_role", sa.Text(), server_default="primary_runtime", nullable=False),
        sa.Column(
            "operations",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "pricing_summary",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "evidence_summary",
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
        sa.ForeignKeyConstraint(["service_id"], ["external_services.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["skill_version_id"], ["skill_versions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "skill_version_id",
            "service_id",
            "dependency_role",
            name="uq_skill_service_dependencies_version_service_role",
        ),
    )
    op.create_index(
        "idx_skill_service_dependencies_version",
        "skill_service_dependencies",
        ["skill_version_id"],
        unique=False,
    )

    op.create_table(
        "pricing_facts",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("subject_kind", sa.Text(), nullable=False),
        sa.Column("subject_id", sa.UUID(), nullable=False),
        sa.Column("fact_type", sa.Text(), nullable=False),
        sa.Column("pricing_model", sa.Text(), server_default="unknown", nullable=False),
        sa.Column("operation_name", sa.Text(), nullable=True),
        sa.Column("unit_name", sa.Text(), nullable=True),
        sa.Column("unit_cost_usd", sa.Float(), nullable=True),
        sa.Column("currency", sa.Text(), nullable=True),
        sa.Column("price_text_raw", sa.Text(), nullable=True),
        sa.Column(
            "price_structured",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("source_kind", sa.Text(), server_default="artifact", nullable=False),
        sa.Column("source_artifact_id", sa.UUID(), nullable=True),
        sa.Column("source_uri", sa.Text(), nullable=True),
        sa.Column("evidence_snippet", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column(
            "observed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("superseded_by", sa.UUID(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["source_artifact_id"], ["source_artifacts.id"]),
        sa.ForeignKeyConstraint(["superseded_by"], ["pricing_facts.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_pricing_facts_subject",
        "pricing_facts",
        ["subject_kind", "subject_id"],
        unique=False,
    )

    op.create_table(
        "service_setup_requirements",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("skill_version_id", sa.UUID(), nullable=False),
        sa.Column("service_id", sa.UUID(), nullable=False),
        sa.Column("requirement_type", sa.Text(), nullable=False),
        sa.Column("key", sa.Text(), nullable=True),
        sa.Column("value_hint", sa.Text(), nullable=True),
        sa.Column("required", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("instructions", sa.Text(), nullable=True),
        sa.Column(
            "evidence_summary",
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
        sa.ForeignKeyConstraint(["service_id"], ["external_services.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["skill_version_id"], ["skill_versions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_service_setup_requirements_version",
        "service_setup_requirements",
        ["skill_version_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_service_setup_requirements_version", table_name="service_setup_requirements")
    op.drop_table("service_setup_requirements")
    op.drop_index("idx_pricing_facts_subject", table_name="pricing_facts")
    op.drop_table("pricing_facts")
    op.drop_index("idx_skill_service_dependencies_version", table_name="skill_service_dependencies")
    op.drop_table("skill_service_dependencies")
    op.drop_table("external_services")

"""normalized package manager foundations

Revision ID: 9e28a7df9c61
Revises: 0e57295dae16
Create Date: 2026-03-28 13:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "9e28a7df9c61"
down_revision: str | Sequence[str] | None = "0e57295dae16"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "skills",
        sa.Column(
            "lifecycle_state",
            sa.String(length=20),
            server_default="published",
            nullable=False,
        ),
    )
    op.add_column("skills", sa.Column("current_version_id", sa.UUID(), nullable=True))
    op.add_column("skills", sa.Column("published_version_id", sa.UUID(), nullable=True))
    op.add_column(
        "skills",
        sa.Column(
            "provenance_summary",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column("skills", sa.Column("display_name", sa.Text(), nullable=True))
    op.add_column("skills", sa.Column("embedding_text", sa.Text(), nullable=True))
    op.add_column("skills", sa.Column("canonical_hash", sa.Text(), nullable=True))
    op.add_column("skills", sa.Column("execution_bundle_hash", sa.Text(), nullable=True))
    op.add_column("skills", sa.Column("canonicalization_level", sa.Text(), nullable=True))
    op.add_column("skills", sa.Column("authorship_status", sa.Text(), nullable=True))
    op.add_column("skills", sa.Column("change_type", sa.Text(), nullable=True))
    op.add_column("skills", sa.Column("change_agent", sa.Text(), nullable=True))
    op.add_column("skills", sa.Column("change_rationale", sa.Text(), nullable=True))
    op.add_column(
        "skills",
        sa.Column(
            "diff_summary",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )
    op.create_index("idx_skills_lifecycle_state", "skills", ["lifecycle_state"], unique=False)

    op.add_column(
        "capabilities",
        sa.Column(
            "lifecycle_state",
            sa.String(length=20),
            server_default="published",
            nullable=False,
        ),
    )
    op.add_column("capabilities", sa.Column("current_version_id", sa.UUID(), nullable=True))
    op.add_column("capabilities", sa.Column("published_version_id", sa.UUID(), nullable=True))
    op.add_column(
        "capabilities",
        sa.Column(
            "provenance_summary",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column("capabilities", sa.Column("display_name", sa.Text(), nullable=True))
    op.add_column("capabilities", sa.Column("embedding_text", sa.Text(), nullable=True))
    op.add_column("capabilities", sa.Column("capability_root_hash", sa.Text(), nullable=True))
    op.add_column("capabilities", sa.Column("execution_bundle_hash", sa.Text(), nullable=True))
    op.add_column("capabilities", sa.Column("canonicalization_level", sa.Text(), nullable=True))
    op.add_column("capabilities", sa.Column("authorship_status", sa.Text(), nullable=True))
    op.add_column("capabilities", sa.Column("change_type", sa.Text(), nullable=True))
    op.add_column("capabilities", sa.Column("change_agent", sa.Text(), nullable=True))
    op.add_column("capabilities", sa.Column("change_rationale", sa.Text(), nullable=True))
    op.add_column(
        "capabilities",
        sa.Column(
            "diff_summary",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )
    op.create_index(
        "idx_capabilities_lifecycle_state",
        "capabilities",
        ["lifecycle_state"],
        unique=False,
    )

    for table_name in ("skill_versions", "capability_versions"):
        op.add_column(table_name, sa.Column("execution_bundle_hash", sa.Text(), nullable=True))
        op.add_column(table_name, sa.Column("change_type", sa.Text(), nullable=True))
        op.add_column(table_name, sa.Column("change_agent", sa.Text(), nullable=True))
        op.add_column(table_name, sa.Column("change_rationale", sa.Text(), nullable=True))
        op.add_column(
            table_name,
            sa.Column(
                "diff_summary",
                postgresql.JSONB(astext_type=sa.Text()),
                server_default=sa.text("'{}'::jsonb"),
                nullable=False,
            ),
        )
        op.add_column(table_name, sa.Column("parent_version_id", sa.UUID(), nullable=True))
        op.add_column(
            table_name,
            sa.Column(
                "derived_from_artifact_ids",
                postgresql.JSONB(astext_type=sa.Text()),
                server_default=sa.text("'[]'::jsonb"),
                nullable=False,
            ),
        )
        op.add_column(table_name, sa.Column("display_name", sa.Text(), nullable=True))
        op.add_column(table_name, sa.Column("embedding_text", sa.Text(), nullable=True))
        op.add_column(
            table_name,
            sa.Column(
                "safety_notices",
                postgresql.JSONB(astext_type=sa.Text()),
                server_default=sa.text("'[]'::jsonb"),
                nullable=False,
            ),
        )
        op.add_column(table_name, sa.Column("canonicalization_level", sa.Text(), nullable=True))
        op.add_column(table_name, sa.Column("authorship_status", sa.Text(), nullable=True))

    op.add_column("skill_versions", sa.Column("canonical_hash", sa.Text(), nullable=True))
    op.add_column(
        "capability_versions",
        sa.Column("capability_root_hash", sa.Text(), nullable=True),
    )

    op.add_column("eval_jobs", sa.Column("subject_kind", sa.Text(), nullable=True))
    op.add_column("eval_jobs", sa.Column("subject_id", sa.UUID(), nullable=True))
    op.add_column("eval_jobs", sa.Column("canonical_hash", sa.Text(), nullable=True))
    op.add_column("eval_jobs", sa.Column("execution_bundle_hash", sa.Text(), nullable=True))
    op.add_column(
        "eval_jobs",
        sa.Column("meta_feedback", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )

    op.create_table(
        "source_artifacts",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("entity_kind", sa.Text(), nullable=False),
        sa.Column("source_type", sa.Text(), nullable=False),
        sa.Column("source_uri", sa.Text(), nullable=False),
        sa.Column("source_ref", sa.Text(), nullable=True),
        sa.Column("artifact_hash", sa.Text(), nullable=False),
        sa.Column(
            "raw_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "ingest_notes",
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_uri",
            "source_ref",
            "artifact_hash",
            name="uq_source_artifacts_uri_ref_hash",
        ),
    )

    op.create_table(
        "artifact_files",
        sa.Column("artifact_id", sa.UUID(), nullable=False),
        sa.Column("path", sa.Text(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("sha256", sa.Text(), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("language", sa.Text(), nullable=True),
        sa.Column("is_entrypoint", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("content_ref", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["artifact_id"], ["source_artifacts.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("artifact_id", "path", name="uq_artifact_files_artifact_path"),
    )

    op.create_table(
        "dedup_clusters",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("cluster_key", sa.Text(), nullable=False),
        sa.Column("entity_kind", sa.Text(), nullable=False),
        sa.Column("canonical_member_id", sa.UUID(), nullable=True),
        sa.Column(
            "cluster_summary",
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cluster_key"),
    )

    op.create_table(
        "artifact_adaptations",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("artifact_id", sa.UUID(), nullable=False),
        sa.Column("target_kind", sa.Text(), nullable=False),
        sa.Column("target_id", sa.UUID(), nullable=False),
        sa.Column("adaptation_type", sa.Text(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column(
            "diff_summary",
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
        sa.ForeignKeyConstraint(["artifact_id"], ["source_artifacts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("artifact_adaptations")
    op.drop_table("dedup_clusters")
    op.drop_table("artifact_files")
    op.drop_table("source_artifacts")

    op.drop_column("eval_jobs", "meta_feedback")
    op.drop_column("eval_jobs", "execution_bundle_hash")
    op.drop_column("eval_jobs", "canonical_hash")
    op.drop_column("eval_jobs", "subject_id")
    op.drop_column("eval_jobs", "subject_kind")

    op.drop_column("capability_versions", "capability_root_hash")
    op.drop_column("skill_versions", "canonical_hash")

    for table_name in ("capability_versions", "skill_versions"):
        op.drop_column(table_name, "authorship_status")
        op.drop_column(table_name, "canonicalization_level")
        op.drop_column(table_name, "safety_notices")
        op.drop_column(table_name, "embedding_text")
        op.drop_column(table_name, "display_name")
        op.drop_column(table_name, "derived_from_artifact_ids")
        op.drop_column(table_name, "parent_version_id")
        op.drop_column(table_name, "diff_summary")
        op.drop_column(table_name, "change_rationale")
        op.drop_column(table_name, "change_agent")
        op.drop_column(table_name, "change_type")
        op.drop_column(table_name, "execution_bundle_hash")

    op.drop_index("idx_capabilities_lifecycle_state", table_name="capabilities")
    op.drop_column("capabilities", "diff_summary")
    op.drop_column("capabilities", "change_rationale")
    op.drop_column("capabilities", "change_agent")
    op.drop_column("capabilities", "change_type")
    op.drop_column("capabilities", "authorship_status")
    op.drop_column("capabilities", "canonicalization_level")
    op.drop_column("capabilities", "execution_bundle_hash")
    op.drop_column("capabilities", "capability_root_hash")
    op.drop_column("capabilities", "embedding_text")
    op.drop_column("capabilities", "display_name")
    op.drop_column("capabilities", "provenance_summary")
    op.drop_column("capabilities", "published_version_id")
    op.drop_column("capabilities", "current_version_id")
    op.drop_column("capabilities", "lifecycle_state")

    op.drop_index("idx_skills_lifecycle_state", table_name="skills")
    op.drop_column("skills", "diff_summary")
    op.drop_column("skills", "change_rationale")
    op.drop_column("skills", "change_agent")
    op.drop_column("skills", "change_type")
    op.drop_column("skills", "authorship_status")
    op.drop_column("skills", "canonicalization_level")
    op.drop_column("skills", "execution_bundle_hash")
    op.drop_column("skills", "canonical_hash")
    op.drop_column("skills", "embedding_text")
    op.drop_column("skills", "display_name")
    op.drop_column("skills", "provenance_summary")
    op.drop_column("skills", "published_version_id")
    op.drop_column("skills", "current_version_id")
    op.drop_column("skills", "lifecycle_state")

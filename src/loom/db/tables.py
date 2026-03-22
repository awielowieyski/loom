"""SQLAlchemy Core table definitions for Alembic and query building."""

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    ARRAY,
    Column,
    DateTime,
    ForeignKey,
    Index,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

metadata = MetaData()

users = Table(
    "users",
    metadata,
    Column("id", UUID, primary_key=True, server_default=text("gen_random_uuid()")),
    Column("handle", Text, unique=True, nullable=False),
    Column("email", Text, unique=True, nullable=False),
    Column("api_key", Text, unique=True, nullable=False),
    Column("role", String(20), nullable=False, server_default="contributor"),
    Column("signing_public_key", Text, nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=text("now()")),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=text("now()")),
)

categories = Table(
    "categories",
    metadata,
    Column("id", UUID, primary_key=True, server_default=text("gen_random_uuid()")),
    Column("slug", Text, unique=True, nullable=False),
    Column("name", Text, nullable=False),
    Column("description", Text, nullable=True),
    Column("parent_id", UUID, ForeignKey("categories.id"), nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=text("now()")),
)

skills = Table(
    "skills",
    metadata,
    Column("id", UUID, primary_key=True, server_default=text("gen_random_uuid()")),
    Column("slug", Text, unique=True, nullable=False),
    Column("name", Text, nullable=False),
    Column("description", Text, nullable=False),
    Column("content", Text, nullable=False),
    Column("category_id", UUID, ForeignKey("categories.id"), nullable=False),
    Column("tags", ARRAY(Text), nullable=False, server_default="{}"),
    Column("scope", String(20), nullable=False, server_default="community"),
    Column("version", Text, nullable=False),
    Column("author_id", UUID, ForeignKey("users.id"), nullable=False),
    Column("signature", Text, nullable=True),
    Column("trust_tier", String(20), nullable=False, server_default="experimental"),
    Column("cost_profile", String(20), nullable=False, server_default="free"),
    Column("cost_drivers", ARRAY(Text), nullable=False, server_default="{}"),
    Column("estimated_duration", String(20), nullable=False, server_default="fast"),
    Column("dependencies", JSONB, nullable=False, server_default="{}"),
    Column("eval_spec", JSONB, nullable=False, server_default="{}"),
    Column("extends", Text, nullable=True),
    Column("embedding", Vector(1536), nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=text("now()")),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=text("now()")),
    Index("idx_skills_category", "category_id"),
    Index("idx_skills_trust_tier", "trust_tier"),
    Index("idx_skills_scope", "scope"),
    Index("idx_skills_tags", "tags", postgresql_using="gin"),
)

skill_versions = Table(
    "skill_versions",
    metadata,
    Column("id", UUID, primary_key=True, server_default=text("gen_random_uuid()")),
    Column("skill_id", UUID, ForeignKey("skills.id", ondelete="CASCADE"), nullable=False),
    Column("version", Text, nullable=False),
    Column("content", Text, nullable=False),
    Column("dependencies", JSONB, nullable=False, server_default="{}"),
    Column("eval_spec", JSONB, nullable=False, server_default="{}"),
    Column("cost_profile", String(20), nullable=False, server_default="free"),
    Column("cost_drivers", ARRAY(Text), nullable=False, server_default="{}"),
    Column("estimated_duration", String(20), nullable=False, server_default="fast"),
    Column("extends", Text, nullable=True),
    Column("signature", Text, nullable=True),
    Column("author_id", UUID, ForeignKey("users.id"), nullable=False),
    Column("changelog", Text, nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=text("now()")),
    UniqueConstraint("skill_id", "version", name="uq_skill_versions_skill_version"),
    Index("idx_skill_versions_skill", "skill_id"),
)

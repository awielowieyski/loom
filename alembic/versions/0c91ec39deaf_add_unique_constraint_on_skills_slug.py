"""add unique constraint on skills slug

Revision ID: 0c91ec39deaf
Revises: 0e57295dae16
Create Date: 2026-03-27 11:41:10.447788

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0c91ec39deaf'
down_revision: Union[str, Sequence[str], None] = '0e57295dae16'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add unique constraint on skills.slug and capabilities.slug."""
    # Deduplicate any existing duplicate slugs before adding constraint
    op.execute("""
        DELETE FROM skills
        WHERE id NOT IN (
            SELECT DISTINCT ON (slug) id
            FROM skills
            ORDER BY slug, created_at ASC
        )
    """)
    op.create_unique_constraint('uq_skills_slug', 'skills', ['slug'])

    op.execute("""
        DELETE FROM capabilities
        WHERE id NOT IN (
            SELECT DISTINCT ON (slug) id
            FROM capabilities
            ORDER BY slug, created_at ASC
        )
    """)
    op.create_unique_constraint('uq_capabilities_slug', 'capabilities', ['slug'])


def downgrade() -> None:
    """Remove unique constraints."""
    op.drop_constraint('uq_capabilities_slug', 'capabilities', type_='unique')
    op.drop_constraint('uq_skills_slug', 'skills', type_='unique')

"""merge normalized package manager heads

Revision ID: 2f6d72fd9b63
Revises: 0c91ec39deaf, 9e28a7df9c61
Create Date: 2026-03-28 13:30:00.000000

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "2f6d72fd9b63"
down_revision: str | Sequence[str] | None = ("0c91ec39deaf", "9e28a7df9c61")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Merge revision heads."""


def downgrade() -> None:
    """Unmerge revision heads."""

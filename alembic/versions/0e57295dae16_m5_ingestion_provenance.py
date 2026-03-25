"""m5_ingestion_provenance

Revision ID: 0e57295dae16
Revises: cc4e18a686fa
Create Date: 2026-03-25 15:23:15.586243

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '0e57295dae16'
down_revision: Union[str, Sequence[str], None] = 'cc4e18a686fa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add provenance columns to skills
    op.add_column('skills', sa.Column('source_uri', sa.Text(), nullable=True))
    op.add_column('skills', sa.Column('license', sa.Text(), nullable=True))

    # Create ingestion_sources table
    op.create_table('ingestion_sources',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('source_type', sa.Text(), nullable=False),
        sa.Column('source_uri', sa.Text(), nullable=False),
        sa.Column('content_hash', sa.Text(), nullable=False),
        sa.Column('skill_id', sa.UUID(), nullable=True),
        sa.Column('skill_version', sa.Text(), nullable=True),
        sa.Column('ingested_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('raw_metadata', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.ForeignKeyConstraint(['skill_id'], ['skills.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_ingestion_sources_content_hash', 'ingestion_sources', ['content_hash'])
    op.create_index('idx_ingestion_sources_skill_id', 'ingestion_sources', ['skill_id'])


def downgrade() -> None:
    op.drop_index('idx_ingestion_sources_skill_id')
    op.drop_index('idx_ingestion_sources_content_hash')
    op.drop_table('ingestion_sources')
    op.drop_column('skills', 'license')
    op.drop_column('skills', 'source_uri')

"""Fix media_files table structure
Revision ID: fix_media_structure
Revises: 2d25fe666075
Create Date: 2025-04-05 12:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'fix_media_structure'
down_revision = '2d25fe666075'
branch_labels = None
depends_on = None

def upgrade():
    # Drop the problematic tables
    op.drop_table('media_file_actual', if_exists=True)
    op.drop_table('media_file', if_exists=True)
    op.drop_table('media_files', if_exists=True)
    
    # Create the correct media_files table
    op.create_table('media_files',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('post_id', sa.String(50), nullable=False),
        sa.Column('filename', sa.String(255), nullable=False),
        sa.Column('file_url', sa.String(500), nullable=False),
        sa.Column('uploaded_at', sa.DateTime(), nullable=True)
    )

def downgrade():
    op.drop_table('media_files')
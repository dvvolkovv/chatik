"""initial_schema

Revision ID: 2026_02_03_1000
Revises: 
Create Date: 2026-02-03 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID
import uuid


# revision identifiers, used by Alembic.
revision = '2026_02_03_1000'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('email', sa.String(255), unique=True, nullable=False, index=True),
        sa.Column('phone', sa.String(20), nullable=True),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('balance', sa.Numeric(10, 2), default=0.0, nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False),
        sa.Column('is_verified', sa.Boolean(), default=False, nullable=False),
        sa.Column('is_superuser', sa.Boolean(), default=False, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=False),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
    )

    # Create user_profiles table with ALL fields
    op.create_table(
        'user_profiles',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False),
        
        # Core attributes
        sa.Column('values', JSONB, default=list, nullable=False),
        sa.Column('beliefs', JSONB, default=list, nullable=False),
        sa.Column('interests', JSONB, default=list, nullable=False),
        sa.Column('skills', JSONB, default=list, nullable=False),
        sa.Column('desires', JSONB, default=list, nullable=False),
        sa.Column('intentions', JSONB, default=list, nullable=False),
        
        # Preferences
        sa.Column('likes', JSONB, default=list, nullable=False),
        sa.Column('dislikes', JSONB, default=list, nullable=False),
        sa.Column('loves', JSONB, default=list, nullable=False),
        sa.Column('hates', JSONB, default=list, nullable=False),
        
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=False),
    )

    # Create chats table
    op.create_table(
        'chats',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('title', sa.String(255), default='Новый чат', nullable=False),
        sa.Column('folder_id', UUID(as_uuid=True), nullable=True),
        sa.Column('tags', sa.ARRAY(sa.String), nullable=False, server_default='{}'),
        sa.Column('is_favorite', sa.Boolean(), default=False, nullable=False),
        sa.Column('is_deleted', sa.Boolean(), default=False, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=False),
    )

    # Create messages table
    op.create_table(
        'messages',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('chat_id', UUID(as_uuid=True), sa.ForeignKey('chats.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('role', sa.String(20), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    # Create indexes
    op.create_index('ix_messages_chat_id_created_at', 'messages', ['chat_id', 'created_at'])


def downgrade() -> None:
    op.drop_index('ix_messages_chat_id_created_at', 'messages')
    op.drop_table('messages')
    op.drop_table('chats')
    op.drop_table('user_profiles')
    op.drop_table('users')

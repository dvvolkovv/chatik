"""add_profile_preferences_and_simplify_structure

Revision ID: eb899b335711
Revises: 
Create Date: 2026-02-03 00:58:39.060721+00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision = 'eb899b335711'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new preference columns
    op.add_column('user_profiles', sa.Column('likes', JSONB, nullable=True))
    op.add_column('user_profiles', sa.Column('dislikes', JSONB, nullable=True))
    op.add_column('user_profiles', sa.Column('loves', JSONB, nullable=True))
    op.add_column('user_profiles', sa.Column('hates', JSONB, nullable=True))
    
    # Migrate existing data: transform values from [{"name": "X", "value": 90}] to ["X"]
    op.execute("""
        UPDATE user_profiles
        SET values = (
            SELECT jsonb_agg(value->>'name')
            FROM jsonb_array_elements(COALESCE(values, '[]'::jsonb)) AS value
            WHERE value->>'name' IS NOT NULL
        )
        WHERE jsonb_typeof(values) = 'array' 
        AND jsonb_array_length(values) > 0
        AND values->0 ? 'name';
    """)
    
    # Migrate existing data: transform skills from [{"name": "X", "level": 4}] to ["X"]
    op.execute("""
        UPDATE user_profiles
        SET skills = (
            SELECT jsonb_agg(skill->>'name')
            FROM jsonb_array_elements(COALESCE(skills, '[]'::jsonb)) AS skill
            WHERE skill->>'name' IS NOT NULL
        )
        WHERE jsonb_typeof(skills) = 'array'
        AND jsonb_array_length(skills) > 0
        AND skills->0 ? 'name';
    """)
    
    # Set defaults for new columns
    op.execute("UPDATE user_profiles SET likes = '[]'::jsonb WHERE likes IS NULL")
    op.execute("UPDATE user_profiles SET dislikes = '[]'::jsonb WHERE dislikes IS NULL")
    op.execute("UPDATE user_profiles SET loves = '[]'::jsonb WHERE loves IS NULL")
    op.execute("UPDATE user_profiles SET hates = '[]'::jsonb WHERE hates IS NULL")


def downgrade() -> None:
    # Remove new columns
    op.drop_column('user_profiles', 'hates')
    op.drop_column('user_profiles', 'loves')
    op.drop_column('user_profiles', 'dislikes')
    op.drop_column('user_profiles', 'likes')
    
    # Note: We cannot reverse the data transformation from simple strings back to objects
    # This is acceptable as it's a one-way migration

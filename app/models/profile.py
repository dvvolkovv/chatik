"""
User Profile model for personalization
"""
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid

from app.core.database import Base


class UserProfile(Base):
    """User profile with personalization data"""
    
    __tablename__ = "user_profiles"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    
    # Personalization data - Core attributes
    values = Column(JSONB, default=list)  # ["Развитие", "Семья", "Честность", ...]
    beliefs = Column(JSONB, default=list)  # ["Belief 1", "Belief 2", ...]
    interests = Column(JSONB, default=list)  # ["Python", "AI", ...]
    skills = Column(JSONB, default=list)  # ["Python", "FastAPI", "Machine Learning", ...]
    desires = Column(JSONB, default=list)  # ["Goal 1", "Goal 2", ...]
    intentions = Column(JSONB, default=list)  # ["Current project", ...]
    
    # Personalization data - Preferences
    likes = Column(JSONB, default=list)  # ["Reading", "Coffee", "Morning walks", ...]
    dislikes = Column(JSONB, default=list)  # ["Waiting", "Loud noises", ...]
    loves = Column(JSONB, default=list)  # ["Family", "Creating products", ...]
    hates = Column(JSONB, default=list)  # ["Injustice", "Bureaucracy", ...]
    
    # Vector embedding for semantic search (pgvector)
    # profile_embedding = Column(Vector(384))  # Requires pgvector extension
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    user = relationship("User", back_populates="profile")
    
    def __repr__(self):
        return f"<UserProfile user_id={self.user_id}>"

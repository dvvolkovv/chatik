"""
Message model
"""
from datetime import datetime
from sqlalchemy import Column, String, Text, Integer, Float, DateTime, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid
import enum

from app.core.database import Base


class MessageRole(str, enum.Enum):
    """Message role enum"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Message(Base):
    """Message model"""
    
    __tablename__ = "messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chat_id = Column(UUID(as_uuid=True), ForeignKey("chats.id", ondelete="CASCADE"), nullable=False)
    
    role = Column(Enum(MessageRole), nullable=False)
    content = Column(Text, nullable=False)
    
    # Model information
    model_used = Column(String, nullable=True)  # e.g., "gpt-4-turbo"
    
    # Token usage
    tokens_input = Column(Integer, default=0)
    tokens_output = Column(Integer, default=0)
    cost = Column(Float, default=0.0)
    
    # Attachments (file IDs)
    attachments = Column(JSONB, default=list)  # [{"file_id": "...", "type": "image"}, ...]
    
    # Additional metadata
    message_metadata = Column(JSONB, default=dict)
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationship
    chat = relationship("Chat", back_populates="messages")
    
    def __repr__(self):
        return f"<Message {self.role} in chat {self.chat_id}>"

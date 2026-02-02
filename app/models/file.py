"""
File model
"""
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from app.core.database import Base


class File(Base):
    """File model for uploaded files"""
    
    __tablename__ = "files"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    filename = Column(String, nullable=False)
    original_filename = Column(String, nullable=False)
    mime_type = Column(String, nullable=False)
    size = Column(Integer, nullable=False)  # in bytes
    
    # Storage path
    storage_path = Column(String, nullable=False)
    
    # Optional: linked to chat/message
    chat_id = Column(UUID(as_uuid=True), ForeignKey("chats.id", ondelete="SET NULL"), nullable=True)
    message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id", ondelete="SET NULL"), nullable=True)
    
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    user = relationship("User", back_populates="files")
    
    def __repr__(self):
        return f"<File {self.original_filename}>"

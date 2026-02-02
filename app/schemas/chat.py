"""
Chat schemas
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, UUID4

from app.schemas.message import MessageResponse


class ChatBase(BaseModel):
    """Base chat schema"""
    title: str = "Новый чат"
    tags: List[str] = []
    is_favorite: bool = False


class ChatCreate(ChatBase):
    """Chat creation schema"""
    pass


class ChatUpdate(BaseModel):
    """Chat update schema"""
    title: Optional[str] = None
    tags: Optional[List[str]] = None
    is_favorite: Optional[bool] = None
    is_deleted: Optional[bool] = None


class ChatResponse(ChatBase):
    """Chat response schema"""
    id: UUID4
    user_id: UUID4
    is_deleted: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class ChatWithMessages(ChatResponse):
    """Chat with messages"""
    messages: List[MessageResponse] = []
    
    class Config:
        from_attributes = True

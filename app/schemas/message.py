"""
Message schemas
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, UUID4
from enum import Enum


class MessageRole(str, Enum):
    """Message role"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class MessageCreate(BaseModel):
    """Message creation schema"""
    content: str
    model: str = "gpt-4-turbo"
    attachments: List[Dict[str, Any]] = []


class MessageResponse(BaseModel):
    """Message response schema"""
    id: UUID4
    chat_id: UUID4
    role: MessageRole
    content: str
    model_used: Optional[str]
    tokens_input: int
    tokens_output: int
    cost: float
    attachments: List[Dict[str, Any]]
    message_metadata: Dict[str, Any] = {}
    created_at: datetime
    
    class Config:
        from_attributes = True
        populate_by_name = True


class StreamChunk(BaseModel):
    """Streaming chunk schema"""
    type: str  # "start", "content", "end", "error"
    content: Optional[str] = None
    message_id: Optional[str] = None  # UUID as string for JSON serialization
    model: Optional[str] = None
    tokens: Optional[Dict[str, int]] = None
    cost: Optional[float] = None
    error: Optional[str] = None

"""
User Profile schemas
"""
from typing import List, Optional, Dict
from pydantic import BaseModel, UUID4


class ProfileBase(BaseModel):
    """Base profile schema"""
    # Core attributes
    values: List[str] = []
    beliefs: List[str] = []
    interests: List[str] = []
    skills: List[str] = []
    desires: List[str] = []
    intentions: List[str] = []
    
    # Preferences
    likes: List[str] = []
    dislikes: List[str] = []
    loves: List[str] = []
    hates: List[str] = []


class ProfileCreate(ProfileBase):
    """Profile creation schema"""
    pass


class ProfileUpdate(BaseModel):
    """Profile update schema"""
    values: Optional[List[str]] = None
    beliefs: Optional[List[str]] = None
    interests: Optional[List[str]] = None
    skills: Optional[List[str]] = None
    desires: Optional[List[str]] = None
    intentions: Optional[List[str]] = None
    likes: Optional[List[str]] = None
    dislikes: Optional[List[str]] = None
    loves: Optional[List[str]] = None
    hates: Optional[List[str]] = None


class ProfileResponse(ProfileBase):
    """Profile response schema"""
    id: UUID4
    user_id: UUID4
    
    class Config:
        from_attributes = True

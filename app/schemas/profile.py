"""
User Profile schemas
"""
from typing import List, Optional, Dict
from pydantic import BaseModel, UUID4


class Value(BaseModel):
    """Value with weight"""
    name: str
    value: int  # 0-100


class Skill(BaseModel):
    """Skill with level"""
    name: str
    level: int  # 1-5


class ProfileBase(BaseModel):
    """Base profile schema"""
    values: List[Value] = []
    beliefs: List[str] = []
    interests: List[str] = []
    skills: List[Skill] = []
    desires: List[str] = []
    intentions: List[str] = []


class ProfileCreate(ProfileBase):
    """Profile creation schema"""
    pass


class ProfileUpdate(BaseModel):
    """Profile update schema"""
    values: Optional[List[Value]] = None
    beliefs: Optional[List[str]] = None
    interests: Optional[List[str]] = None
    skills: Optional[List[Skill]] = None
    desires: Optional[List[str]] = None
    intentions: Optional[List[str]] = None


class ProfileResponse(ProfileBase):
    """Profile response schema"""
    id: UUID4
    user_id: UUID4
    
    class Config:
        from_attributes = True

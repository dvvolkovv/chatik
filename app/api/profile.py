"""
User Profile API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.profile import UserProfile
from app.schemas.profile import ProfileResponse, ProfileUpdate, ProfileCreate

router = APIRouter()


@router.get("/", response_model=ProfileResponse)
async def get_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current user's profile
    """
    result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()
    
    if not profile:
        # Create default profile if doesn't exist
        profile = UserProfile(
            user_id=current_user.id,
            values=[],
            beliefs=[],
            interests=[],
            skills=[],
            desires=[],
            intentions=[],
        )
        db.add(profile)
        await db.commit()
        await db.refresh(profile)
    
    return ProfileResponse.from_orm(profile)


@router.put("/", response_model=ProfileResponse)
async def update_profile(
    profile_data: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update user profile
    
    - **values**: List of values with weights
    - **beliefs**: List of beliefs
    - **interests**: List of interests
    - **skills**: List of skills with levels
    - **desires**: List of goals/desires
    - **intentions**: List of current intentions
    """
    result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )
    
    # Update fields
    update_data = profile_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            setattr(profile, field, value)
    
    await db.commit()
    await db.refresh(profile)
    
    return ProfileResponse.from_orm(profile)


@router.post("/analyze/{chat_id}")
async def analyze_message_for_profile(
    chat_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Analyze chat messages to extract and update profile information
    
    This endpoint uses LLM to analyze recent chat messages and automatically
    update user's profile (values, interests, skills, etc.)
    
    - **chat_id**: ID of chat to analyze
    """
    from app.core.config import settings
    from app.services.profile_extractor import ProfileExtractor
    from app.models.chat import Chat
    from app.models.message import MessageRole
    from sqlalchemy.orm import selectinload
    
    # Get chat with messages
    result = await db.execute(
        select(Chat)
        .where(and_(Chat.id == chat_id, Chat.user_id == current_user.id))
        .options(selectinload(Chat.messages))
    )
    chat = result.scalar_one_or_none()
    
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found"
        )
    
    if len(chat.messages) < 2:
        return {
            "extracted": {},
            "message": "Not enough messages to analyze"
        }
    
    # Get last user and assistant messages
    messages = sorted(chat.messages, key=lambda m: m.created_at)
    last_messages = messages[-2:]
    
    user_message = None
    assistant_message = None
    for msg in last_messages:
        if msg.role == MessageRole.USER:
            user_message = msg.content
        elif msg.role == MessageRole.ASSISTANT:
            assistant_message = msg.content
    
    if not user_message or not assistant_message:
        return {
            "extracted": {},
            "message": "Missing user or assistant message"
        }
    
    # Extract profile information
    extractor = ProfileExtractor(settings)
    extracted_data = await extractor.extract_from_messages(
        user_message=user_message,
        assistant_message=assistant_message
    )
    
    # Get user profile
    result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()
    
    if not profile:
        profile = UserProfile(
            user_id=current_user.id,
            values=[],
            beliefs=[],
            interests=[],
            skills=[],
            desires=[],
            intentions=[],
        )
        db.add(profile)
        await db.flush()
    
    # Merge and update profile
    merged_data = extractor.merge_with_existing(profile, extracted_data)
    
    profile.interests = merged_data["interests"]
    profile.skills = merged_data["skills"]
    profile.values = merged_data["values"]
    profile.beliefs = merged_data["beliefs"]
    profile.desires = merged_data["desires"]
    profile.intentions = merged_data["intentions"]
    
    await db.commit()
    
    total_extracted = sum(len(v) for v in extracted_data.values())
    
    return {
        "extracted": extracted_data,
        "merged_profile": merged_data,
        "message": f"Successfully extracted and merged {total_extracted} items"
    }

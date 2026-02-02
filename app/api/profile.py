"""
User Profile API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

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


@router.post("/analyze")
async def analyze_message_for_profile(
    message: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Analyze a message to extract profile information
    
    This endpoint uses LLM to analyze user's message and suggest
    updates to their profile (values, interests, skills, etc.)
    
    - **message**: Message to analyze
    """
    # TODO: Implement profile extraction using LLM
    # This would use a separate LLM call to analyze the message
    # and suggest profile updates
    
    return {
        "suggestions": {
            "interests": [],
            "skills": [],
            "values": [],
        },
        "message": "Profile analysis feature coming soon"
    }

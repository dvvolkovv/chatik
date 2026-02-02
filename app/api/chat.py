"""
Chat API endpoints
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.chat import Chat
from app.models.message import Message
from app.schemas.chat import ChatCreate, ChatUpdate, ChatResponse, ChatWithMessages

router = APIRouter()


@router.get("/", response_model=List[ChatResponse])
async def get_user_chats(
    skip: int = 0,
    limit: int = 100,
    include_deleted: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all user chats
    
    - **skip**: Number of chats to skip (pagination)
    - **limit**: Maximum number of chats to return
    - **include_deleted**: Include deleted chats
    """
    query = select(Chat).where(Chat.user_id == current_user.id)
    
    if not include_deleted:
        query = query.where(Chat.is_deleted == False)
    
    query = query.order_by(Chat.updated_at.desc()).offset(skip).limit(limit)
    
    result = await db.execute(query)
    chats = result.scalars().all()
    
    return [ChatResponse.from_orm(chat) for chat in chats]


@router.post("/", response_model=ChatResponse, status_code=status.HTTP_201_CREATED)
async def create_chat(
    chat_data: ChatCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new chat
    
    - **title**: Chat title
    - **tags**: Optional tags
    """
    new_chat = Chat(
        user_id=current_user.id,
        title=chat_data.title,
        tags=chat_data.tags,
        is_favorite=chat_data.is_favorite,
    )
    
    db.add(new_chat)
    await db.commit()
    await db.refresh(new_chat)
    
    return ChatResponse.from_orm(new_chat)


@router.get("/{chat_id}", response_model=ChatWithMessages)
async def get_chat(
    chat_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific chat with all messages
    
    - **chat_id**: Chat ID
    """
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
    
    # Convert messages manually to avoid metadata conflict
    from app.schemas.message import MessageResponse
    messages = [
        MessageResponse(
            id=msg.id,
            chat_id=msg.chat_id,
            role=msg.role,
            content=msg.content,
            model_used=msg.model_used,
            tokens_input=msg.tokens_input,
            tokens_output=msg.tokens_output,
            cost=msg.cost,
            attachments=msg.attachments or [],
            message_metadata=msg.message_metadata or {},
            created_at=msg.created_at,
        )
        for msg in chat.messages
    ]
    
    # Create response
    chat_response = ChatWithMessages(
        id=chat.id,
        user_id=chat.user_id,
        title=chat.title,
        is_favorite=chat.is_favorite,
        is_deleted=chat.is_deleted,
        created_at=chat.created_at,
        updated_at=chat.updated_at,
        messages=messages
    )
    
    return chat_response


@router.patch("/{chat_id}", response_model=ChatResponse)
async def update_chat(
    chat_id: str,
    chat_data: ChatUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update chat
    
    - **chat_id**: Chat ID
    - **title**: Optional new title
    - **tags**: Optional new tags
    - **is_favorite**: Optional favorite status
    - **is_deleted**: Optional deleted status
    """
    result = await db.execute(
        select(Chat).where(and_(Chat.id == chat_id, Chat.user_id == current_user.id))
    )
    chat = result.scalar_one_or_none()
    
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found"
        )
    
    # Update fields
    update_data = chat_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(chat, field, value)
    
    await db.commit()
    await db.refresh(chat)
    
    return ChatResponse.from_orm(chat)


@router.delete("/{chat_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chat(
    chat_id: str,
    permanent: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete chat
    
    - **chat_id**: Chat ID
    - **permanent**: If True, permanently delete. Otherwise, mark as deleted.
    """
    result = await db.execute(
        select(Chat).where(and_(Chat.id == chat_id, Chat.user_id == current_user.id))
    )
    chat = result.scalar_one_or_none()
    
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found"
        )
    
    if permanent:
        await db.delete(chat)
    else:
        chat.is_deleted = True
    
    await db.commit()
    
    return None


@router.post("/{chat_id}/favorite", response_model=ChatResponse)
async def toggle_favorite(
    chat_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Toggle chat favorite status
    
    - **chat_id**: Chat ID
    """
    result = await db.execute(
        select(Chat).where(and_(Chat.id == chat_id, Chat.user_id == current_user.id))
    )
    chat = result.scalar_one_or_none()
    
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found"
        )
    
    chat.is_favorite = not chat.is_favorite
    await db.commit()
    await db.refresh(chat)
    
    return ChatResponse.from_orm(chat)

"""
LLM Integration API endpoints
"""
from typing import AsyncGenerator
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
import json

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.config import settings
from app.models.user import User
from app.models.chat import Chat
from app.models.message import Message, MessageRole
from app.schemas.message import MessageCreate, MessageResponse, StreamChunk
from app.services.llm_service import LLMService

router = APIRouter()


@router.post("/chat/{chat_id}/message", response_model=MessageResponse)
async def send_message(
    chat_id: str,
    message_data: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Send a message to chat (non-streaming)
    
    - **chat_id**: Chat ID
    - **content**: Message content
    - **model**: LLM model to use (e.g., "gpt-4-turbo", "claude-3-opus")
    - **attachments**: Optional file attachments
    """
    # Get chat
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
    
    # Check balance
    if current_user.balance < 0.01:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Insufficient balance"
        )
    
    # Save user message
    user_message = Message(
        chat_id=chat.id,
        role=MessageRole.USER,
        content=message_data.content,
        attachments=message_data.attachments,
    )
    db.add(user_message)
    await db.flush()
    
    # Get user profile for personalization
    await db.execute(select(User).where(User.id == current_user.id).options(selectinload(User.profile)))
    user_profile = current_user.profile if hasattr(current_user, 'profile') else None
    
    # Call LLM service
    llm_service = LLMService(settings)
    
    try:
        response = await llm_service.generate_response(
            model=message_data.model,
            messages=chat.messages + [user_message],
            user_profile=user_profile,
        )
        
        # Save assistant message
        assistant_message = Message(
            chat_id=chat.id,
            role=MessageRole.ASSISTANT,
            content=response["content"],
            model_used=message_data.model,
            tokens_input=response["tokens"]["input"],
            tokens_output=response["tokens"]["output"],
            cost=response["cost"],
        )
        db.add(assistant_message)
        
        # Update user balance
        current_user.balance -= response["cost"]
        
        # Update chat
        chat.updated_at = assistant_message.created_at
        if chat.title == "Новый чат" and len(chat.messages) == 0:
            # Auto-generate title from first message
            chat.title = message_data.content[:50] + ("..." if len(message_data.content) > 50 else "")
        
        await db.commit()
        await db.refresh(assistant_message)
        
        return MessageResponse.from_orm(assistant_message)
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"LLM error: {str(e)}"
        )


@router.post("/chat/{chat_id}/message/stream")
async def send_message_stream(
    chat_id: str,
    message_data: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Send a message to chat with streaming response
    
    - **chat_id**: Chat ID
    - **content**: Message content
    - **model**: LLM model to use
    - **attachments**: Optional file attachments
    
    Returns Server-Sent Events (SSE) stream
    """
    # Get chat
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
    
    # Check balance
    if current_user.balance < 0.01:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Insufficient balance"
        )
    
    # Save user message
    user_message = Message(
        chat_id=chat.id,
        role=MessageRole.USER,
        content=message_data.content,
        attachments=message_data.attachments,
    )
    db.add(user_message)
    await db.flush()
    
    # Get user profile
    await db.execute(select(User).where(User.id == current_user.id).options(selectinload(User.profile)))
    user_profile = current_user.profile if hasattr(current_user, 'profile') else None
    
    async def event_stream() -> AsyncGenerator[str, None]:
        """Generate SSE stream"""
        llm_service = LLMService(settings)
        accumulated_content = ""
        
        try:
            # Send start event
            yield f"data: {json.dumps(StreamChunk(type='start', model=message_data.model).dict())}\n\n"
            
            # Stream response
            async for chunk in llm_service.stream_response(
                model=message_data.model,
                messages=chat.messages + [user_message],
                user_profile=user_profile,
            ):
                accumulated_content += chunk["content"]
                
                yield f"data: {json.dumps(StreamChunk(type='content', content=chunk['content']).dict())}\n\n"
            
            # Save assistant message
            assistant_message = Message(
                chat_id=chat.id,
                role=MessageRole.ASSISTANT,
                content=accumulated_content,
                model_used=message_data.model,
                tokens_input=chunk.get("tokens", {}).get("input", 0),
                tokens_output=chunk.get("tokens", {}).get("output", 0),
                cost=chunk.get("cost", 0.0),
            )
            db.add(assistant_message)
            
            # Update user balance
            current_user.balance -= assistant_message.cost
            
            # Update chat
            chat.updated_at = assistant_message.created_at
            if chat.title == "Новый чат":
                chat.title = message_data.content[:50] + ("..." if len(message_data.content) > 50 else "")
            
            await db.commit()
            await db.refresh(assistant_message)
            
            # Send end event
            yield f"data: {json.dumps(StreamChunk(type='end', message_id=assistant_message.id, tokens=chunk.get('tokens'), cost=chunk.get('cost')).dict())}\n\n"
            
        except Exception as e:
            await db.rollback()
            yield f"data: {json.dumps(StreamChunk(type='error', error=str(e)).dict())}\n\n"
    
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.get("/models")
async def get_available_models():
    """
    Get list of available LLM models
    """
    models = [
        {
            "id": "gpt-4-turbo",
            "name": "GPT-4 Turbo",
            "provider": "openai",
            "price_input": 0.01,  # per 1K tokens
            "price_output": 0.03,
            "context_length": 128000,
            "capabilities": ["text", "vision"],
        },
        {
            "id": "gpt-3.5-turbo",
            "name": "GPT-3.5 Turbo",
            "provider": "openai",
            "price_input": 0.0015,
            "price_output": 0.002,
            "context_length": 16385,
            "capabilities": ["text"],
        },
        {
            "id": "claude-3-opus",
            "name": "Claude 3 Opus",
            "provider": "anthropic",
            "price_input": 0.015,
            "price_output": 0.075,
            "context_length": 200000,
            "capabilities": ["text", "vision"],
        },
        {
            "id": "claude-3-sonnet",
            "name": "Claude 3 Sonnet",
            "provider": "anthropic",
            "price_input": 0.003,
            "price_output": 0.015,
            "context_length": 200000,
            "capabilities": ["text", "vision"],
        },
        {
            "id": "gemini-pro",
            "name": "Gemini Pro",
            "provider": "google",
            "price_input": 0.00025,
            "price_output": 0.0005,
            "context_length": 32000,
            "capabilities": ["text", "vision"],
        },
    ]
    
    return {"models": models}

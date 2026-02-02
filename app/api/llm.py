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


@router.post("/chat/{chat_id}/message")
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
        
        # Convert to response manually to avoid metadata conflict
        response_data = {
            "id": str(assistant_message.id),
            "chat_id": str(assistant_message.chat_id),
            "role": assistant_message.role.value,
            "content": assistant_message.content,
            "model_used": assistant_message.model_used,
            "tokens_input": assistant_message.tokens_input,
            "tokens_output": assistant_message.tokens_output,
            "cost": assistant_message.cost,
            "attachments": assistant_message.attachments or [],
            "message_metadata": assistant_message.message_metadata or {},
            "created_at": assistant_message.created_at.isoformat(),
        }
        
        return response_data
        
    except Exception as e:
        await db.rollback()
        import traceback
        error_details = traceback.format_exc()
        print(f"❌ LLM Error: {error_details}")  # Log to console
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
            # No need to refresh - we already have the id
            
            # Send end event (convert UUID to string)
            yield f"data: {json.dumps(StreamChunk(type='end', message_id=str(assistant_message.id), tokens=chunk.get('tokens'), cost=chunk.get('cost')).dict())}\n\n"
            
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
    Get list of available LLM models via OpenRouter (Top 20)
    """
    models = [
        # Tier 1: Premium Models
        {
            "id": "openai/gpt-5.2",
            "name": "GPT-5.2",
            "provider": "OpenAI",
            "price_input": 0.015,  # per 1K tokens USD
            "price_output": 0.045,
            "context_length": 256000,
            "capabilities": ["text", "vision", "reasoning"],
            "tier": "premium",
        },
        {
            "id": "openai/gpt-5",
            "name": "GPT-5",
            "provider": "OpenAI",
            "price_input": 0.012,  # per 1K tokens USD
            "price_output": 0.036,
            "context_length": 200000,
            "capabilities": ["text", "vision", "reasoning"],
            "tier": "premium",
        },
        {
            "id": "anthropic/claude-4.5-sonnet",
            "name": "Claude 4.5 Sonnet",
            "provider": "Anthropic",
            "price_input": 0.008,
            "price_output": 0.024,
            "context_length": 300000,
            "capabilities": ["text", "vision", "reasoning"],
            "tier": "premium",
        },
        {
            "id": "openai/gpt-4-turbo",
            "name": "GPT-4 Turbo",
            "provider": "OpenAI",
            "price_input": 0.01,  # per 1K tokens USD
            "price_output": 0.03,
            "context_length": 128000,
            "capabilities": ["text", "vision"],
            "tier": "premium",
        },
        {
            "id": "openai/gpt-4o",
            "name": "GPT-4o",
            "provider": "OpenAI",
            "price_input": 0.005,
            "price_output": 0.015,
            "context_length": 128000,
            "capabilities": ["text", "vision"],
            "tier": "premium",
        },
        {
            "id": "anthropic/claude-3.5-sonnet",
            "name": "Claude 3.5 Sonnet",
            "provider": "Anthropic",
            "price_input": 0.003,
            "price_output": 0.015,
            "context_length": 200000,
            "capabilities": ["text", "vision"],
            "tier": "premium",
        },
        {
            "id": "anthropic/claude-3-opus",
            "name": "Claude 3 Opus",
            "provider": "Anthropic",
            "price_input": 0.015,
            "price_output": 0.075,
            "context_length": 200000,
            "capabilities": ["text", "vision"],
            "tier": "premium",
        },
        {
            "id": "google/gemini-pro-1.5",
            "name": "Gemini Pro 1.5",
            "provider": "Google",
            "price_input": 0.00125,
            "price_output": 0.005,
            "context_length": 2000000,
            "capabilities": ["text", "vision"],
            "tier": "premium",
        },
        
        # Tier 2: Balanced Models
        {
            "id": "openai/gpt-3.5-turbo",
            "name": "GPT-3.5 Turbo",
            "provider": "OpenAI",
            "price_input": 0.0005,
            "price_output": 0.0015,
            "context_length": 16385,
            "capabilities": ["text"],
            "tier": "balanced",
        },
        {
            "id": "anthropic/claude-3-sonnet",
            "name": "Claude 3 Sonnet",
            "provider": "Anthropic",
            "price_input": 0.003,
            "price_output": 0.015,
            "context_length": 200000,
            "capabilities": ["text", "vision"],
            "tier": "balanced",
        },
        {
            "id": "anthropic/claude-3-haiku",
            "name": "Claude 3 Haiku",
            "provider": "Anthropic",
            "price_input": 0.00025,
            "price_output": 0.00125,
            "context_length": 200000,
            "capabilities": ["text", "vision"],
            "tier": "balanced",
        },
        {
            "id": "google/gemini-flash-1.5",
            "name": "Gemini Flash 1.5",
            "provider": "Google",
            "price_input": 0.000075,
            "price_output": 0.0003,
            "context_length": 1000000,
            "capabilities": ["text", "vision"],
            "tier": "balanced",
        },
        {
            "id": "mistralai/mistral-large",
            "name": "Mistral Large",
            "provider": "Mistral AI",
            "price_input": 0.004,
            "price_output": 0.012,
            "context_length": 128000,
            "capabilities": ["text"],
            "tier": "balanced",
        },
        
        # Tier 3: Budget Models
        {
            "id": "meta-llama/llama-3.1-70b-instruct",
            "name": "Llama 3.1 70B",
            "provider": "Meta",
            "price_input": 0.00052,
            "price_output": 0.00075,
            "context_length": 131072,
            "capabilities": ["text"],
            "tier": "budget",
        },
        {
            "id": "meta-llama/llama-3.1-8b-instruct",
            "name": "Llama 3.1 8B",
            "provider": "Meta",
            "price_input": 0.00006,
            "price_output": 0.00006,
            "context_length": 131072,
            "capabilities": ["text"],
            "tier": "budget",
        },
        {
            "id": "mistralai/mistral-7b-instruct",
            "name": "Mistral 7B",
            "provider": "Mistral AI",
            "price_input": 0.00006,
            "price_output": 0.00006,
            "context_length": 32768,
            "capabilities": ["text"],
            "tier": "budget",
        },
        {
            "id": "qwen/qwen-2-72b-instruct",
            "name": "Qwen 2 72B",
            "provider": "Alibaba",
            "price_input": 0.00056,
            "price_output": 0.00077,
            "context_length": 32768,
            "capabilities": ["text"],
            "tier": "budget",
        },
        {
            "id": "deepseek/deepseek-chat",
            "name": "DeepSeek Chat",
            "provider": "DeepSeek",
            "price_input": 0.00014,
            "price_output": 0.00028,
            "context_length": 64000,
            "capabilities": ["text"],
            "tier": "budget",
        },
        
        # Tier 4: Specialized Models
        {
            "id": "perplexity/llama-3.1-sonar-large-128k-online",
            "name": "Perplexity Sonar Large (Online)",
            "provider": "Perplexity",
            "price_input": 0.001,
            "price_output": 0.001,
            "context_length": 127072,
            "capabilities": ["text", "web-search"],
            "tier": "specialized",
        },
        {
            "id": "cohere/command-r-plus",
            "name": "Command R+",
            "provider": "Cohere",
            "price_input": 0.003,
            "price_output": 0.015,
            "context_length": 128000,
            "capabilities": ["text"],
            "tier": "specialized",
        },
        {
            "id": "x-ai/grok-beta",
            "name": "Grok Beta",
            "provider": "xAI",
            "price_input": 0.005,
            "price_output": 0.015,
            "context_length": 131072,
            "capabilities": ["text"],
            "tier": "specialized",
        },
        {
            "id": "openai/o1-mini",
            "name": "o1-mini (Reasoning)",
            "provider": "OpenAI",
            "price_input": 0.003,
            "price_output": 0.012,
            "context_length": 128000,
            "capabilities": ["text", "reasoning"],
            "tier": "specialized",
        },
        {
            "id": "anthropic/claude-2.1",
            "name": "Claude 2.1",
            "provider": "Anthropic",
            "price_input": 0.008,
            "price_output": 0.024,
            "context_length": 200000,
            "capabilities": ["text"],
            "tier": "balanced",
        },
    ]
    
    return {"models": models, "gateway": "OpenRouter"}

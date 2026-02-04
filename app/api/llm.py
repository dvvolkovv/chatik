"""
LLM Integration API endpoints
"""
from typing import AsyncGenerator
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
import json
import asyncio
import logging

from app.core.database import get_db, AsyncSessionLocal
from app.core.security import get_current_user
from app.core.config import settings
from app.models.user import User
from app.models.chat import Chat
from app.models.message import Message, MessageRole
from app.models.profile import UserProfile
from app.schemas.message import MessageCreate, MessageResponse, StreamChunk
from app.services.llm_service import LLMService
from app.services.profile_extractor import ProfileExtractor

logger = logging.getLogger(__name__)

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
        chat.updated_at = datetime.utcnow()
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


async def extract_and_update_profile_delayed(
    user_id: str,
    chat_id: str,
    delay_seconds: int = 3
):
    """
    Background task to extract profile information from recent messages
    Waits for streaming to complete before analyzing
    
    Args:
        user_id: User ID
        chat_id: Chat ID to analyze
        delay_seconds: Seconds to wait before extraction
    """
    print(f"🔍 [Profile Extraction] Task scheduled for user {user_id}, waiting {delay_seconds}s...")
    
    if not settings.PROFILE_EXTRACTION_ENABLED:
        print(f"⚠️ [Profile Extraction] Disabled in settings")
        return
    
    # Wait for streaming to complete
    await asyncio.sleep(delay_seconds)
    
    try:
        print(f"✨ [Profile Extraction] Starting extraction for user {user_id}...")
        logger.info(f"[Profile Extraction] Starting extraction for user {user_id}")
        
        # Create new database session for background task
        async with AsyncSessionLocal() as db:
            # Get chat with last 2 messages
            result = await db.execute(
                select(Chat)
                .where(Chat.id == chat_id)
                .options(selectinload(Chat.messages))
            )
            chat = result.scalar_one_or_none()
            
            if not chat or len(chat.messages) < 2:
                print(f"⚠️ [Profile Extraction] No messages to analyze")
                return
            
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
                print(f"⚠️ [Profile Extraction] Missing user or assistant message")
                return
            
            print(f"📝 [Profile Extraction] Analyzing messages...")
            
            # Get user profile
            result = await db.execute(
                select(UserProfile).where(UserProfile.user_id == user_id)
            )
            profile = result.scalar_one_or_none()
            
            # Create profile if doesn't exist
            if not profile:
                profile = UserProfile(
                    user_id=user_id,
                    values=[],
                    beliefs=[],
                    interests=[],
                    skills=[],
                    desires=[],
                    intentions=[],
                )
                db.add(profile)
                await db.flush()
            
            # Extract profile data using LLM
            extractor = ProfileExtractor(settings)
            extracted_data = await extractor.extract_from_messages(
                user_message=user_message,
                assistant_message=assistant_message
            )
            
            # Check if anything was extracted
            total_extracted = sum(len(v) for v in extracted_data.values())
            if total_extracted == 0:
                logger.debug(f"[Profile Extraction] No information extracted from messages")
                return
            
            # Merge with existing profile
            merged_data = extractor.merge_with_existing(profile, extracted_data)
            
            # Update profile (all 10 fields)
            profile.values = merged_data["values"]
            profile.beliefs = merged_data["beliefs"]
            profile.interests = merged_data["interests"]
            profile.skills = merged_data["skills"]
            profile.desires = merged_data["desires"]
            profile.intentions = merged_data["intentions"]
            profile.likes = merged_data["likes"]
            profile.dislikes = merged_data["dislikes"]
            profile.loves = merged_data["loves"]
            profile.hates = merged_data["hates"]
            
            await db.commit()
            
            logger.info(f"[Profile Extraction] Successfully updated profile for user {user_id}: {total_extracted} items extracted")
            
    except Exception as e:
        logger.error(f"[Profile Extraction] Error in background task: {e}", exc_info=True)


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
        print(f"🎬 [Stream] event_stream() started", flush=True)
        llm_service = LLMService(settings)
        accumulated_content = ""
        final_tokens = {"input": 0, "output": 0}
        final_cost = 0.0
        
        print(f"🎯 [Stream] Creating extraction thread...", flush=True)
        
        # Schedule profile extraction to run after stream completes
        # Using asyncio task so it persists after HTTP connection closes
        async def run_extraction_async():
            try:
                await asyncio.sleep(5)  # Wait for stream to complete
                print(f"⏰ [Profile] Task woke up after sleep, starting extraction...", flush=True)
                logger.info(f"[Profile] Task woke up, starting extraction...")
                await extract_and_update_profile_delayed(
                    user_id=str(current_user.id),
                    chat_id=str(chat.id),
                    delay_seconds=0  # Already waited 5s
                )
            except Exception as e:
                logger.error(f"[Profile] Task error: {e}", exc_info=True)
        
        task = asyncio.create_task(run_extraction_async())
        print(f"🚀 [Profile] Extraction task scheduled", flush=True)
        logger.info(f"[Profile] Extraction task scheduled")
        
        try:
            # Send start event
            yield f"data: {json.dumps(StreamChunk(type='start', model=message_data.model).dict())}\n\n"
            
            # Stream response
            async for chunk in llm_service.stream_response(
                model=message_data.model,
                messages=chat.messages + [user_message],
                user_profile=user_profile,
            ):
                # Accumulate content if present
                if chunk.get("content"):
                    accumulated_content += chunk["content"]
                    yield f"data: {json.dumps(StreamChunk(type='content', content=chunk['content']).dict())}\n\n"
                
                # Update tokens and cost (will get accurate values in final chunk)
                if chunk.get("tokens"):
                    final_tokens = chunk["tokens"]
                if chunk.get("cost") is not None:
                    final_cost = chunk["cost"]
            
            # Save assistant message with accurate token counts
            assistant_message = Message(
                chat_id=chat.id,
                role=MessageRole.ASSISTANT,
                content=accumulated_content,
                model_used=message_data.model,
                tokens_input=final_tokens.get("input", 0),
                tokens_output=final_tokens.get("output", 0),
                cost=final_cost,
            )
            db.add(assistant_message)
            
            # Update user balance
            current_user.balance -= assistant_message.cost
            
            # Update chat
            chat.updated_at = datetime.utcnow()
            if chat.title == "Новый чат":
                chat.title = message_data.content[:50] + ("..." if len(message_data.content) > 50 else "")
            
            await db.commit()
            logger.info(f"COMMIT DONE - scheduling profile extraction")
            
            # Schedule profile extraction in background using asyncio task
            # This ensures the task continues even after client disconnects
            async def run_extraction_async():
                try:
                    await asyncio.sleep(2)  # Wait for stream to complete
                    logger.info(f"Task starting extraction...")
                    await extract_and_update_profile_delayed(
                        user_id=str(current_user.id),
                        chat_id=str(chat.id),
                        delay_seconds=0  # Already waited 2s
                    )
                except Exception as e:
                    logger.error(f"Task extraction error: {e}", exc_info=True)
            
            task = asyncio.create_task(run_extraction_async())
            logger.info(f"Profile extraction task scheduled")
            
            # Send end event with accurate stats (convert UUID to string)
            yield f"data: {json.dumps(StreamChunk(type='end', message_id=str(assistant_message.id), tokens=final_tokens, cost=final_cost).dict())}\n\n"
            
        except Exception as e:
            await db.rollback()
            import traceback
            error_details = traceback.format_exc()
            print(f"❌ Streaming Error: {error_details}")
            yield f"data: {json.dumps(StreamChunk(type='error', error=str(e)).dict())}\n\n"
    
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
            "Content-Encoding": "none",  # Disable compression
            "Transfer-Encoding": "chunked",  # Enable chunked transfer
        }
    )


@router.get("/models")
async def get_available_models():
    """
    Get list of available LLM models via OpenRouter (23 models including Gemini, Grok, DeepSeek)
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
            "id": "anthropic/claude-3.7-sonnet",
            "name": "Claude 3.7 Sonnet",
            "provider": "Anthropic",
            "price_input": 0.003,
            "price_output": 0.015,
            "context_length": 200000,
            "capabilities": ["text", "vision"],
            "tier": "premium",
        },
        {
            "id": "openai/chatgpt-4o-latest",
            "name": "ChatGPT-4o Latest",
            "provider": "OpenAI",
            "price_input": 0.005,
            "price_output": 0.015,
            "context_length": 128000,
            "capabilities": ["text", "vision"],
            "tier": "premium",
        },
        
        # Tier 2: Balanced Models
        {
            "id": "google/gemini-2.0-flash-001",
            "name": "Gemini 2.0 Flash",
            "provider": "Google",
            "price_input": 0.0001,
            "price_output": 0.0004,
            "context_length": 1048576,
            "capabilities": ["text", "vision", "audio", "video"],
            "tier": "balanced",
        },
        {
            "id": "x-ai/grok-2-1212",
            "name": "Grok 2 1212",
            "provider": "xAI",
            "price_input": 0.002,
            "price_output": 0.010,
            "context_length": 131072,
            "capabilities": ["text", "reasoning"],
            "tier": "balanced",
        },
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
            "id": "openai/gpt-4o-mini",
            "name": "GPT-4o Mini",
            "provider": "OpenAI",
            "price_input": 0.00015,
            "price_output": 0.0006,
            "context_length": 128000,
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
            "id": "mistralai/mistral-nemo",
            "name": "Mistral Nemo",
            "provider": "Mistral AI",
            "price_input": 0.00015,
            "price_output": 0.00015,
            "context_length": 128000,
            "capabilities": ["text"],
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
        {
            "id": "mistralai/mixtral-8x7b-instruct",
            "name": "Mixtral 8x7B",
            "provider": "Mistral AI",
            "price_input": 0.00024,
            "price_output": 0.00024,
            "context_length": 32768,
            "capabilities": ["text"],
            "tier": "balanced",
        },
        
        # Tier 3: Budget Models
        {
            "id": "meta-llama/llama-3.3-70b-instruct",
            "name": "Llama 3.3 70B",
            "provider": "Meta",
            "price_input": 0.00035,
            "price_output": 0.0004,
            "context_length": 131072,
            "capabilities": ["text"],
            "tier": "budget",
        },
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
            "id": "nvidia/llama-3.1-nemotron-70b-instruct",
            "name": "Nemotron 70B",
            "provider": "NVIDIA",
            "price_input": 0.00035,
            "price_output": 0.0004,
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
            "id": "qwen/qwen-2.5-72b-instruct",
            "name": "Qwen 2.5 72B",
            "provider": "Alibaba",
            "price_input": 0.00035,
            "price_output": 0.0004,
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
            "id": "deepseek/deepseek-chat",
            "name": "DeepSeek Chat",
            "provider": "DeepSeek",
            "price_input": 0.0003,
            "price_output": 0.0012,
            "context_length": 163840,
            "capabilities": ["text", "reasoning"],
            "tier": "budget",
        },
    ]
    
    return {"models": models, "gateway": "OpenRouter"}

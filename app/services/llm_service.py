"""
LLM Service for interacting with various AI models via OpenRouter
"""
from typing import List, Dict, Any, AsyncGenerator, Optional
from openai import AsyncOpenAI
import asyncio

from app.core.config import Settings
from app.models.message import Message
from app.models.profile import UserProfile


class LLMService:
    """Service for LLM interactions via OpenRouter"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        
        # Initialize OpenRouter client (uses OpenAI-compatible API)
        if settings.OPENROUTER_API_KEY:
            self.openrouter_client = AsyncOpenAI(
                api_key=settings.OPENROUTER_API_KEY,
                base_url="https://openrouter.ai/api/v1"
            )
    
    def _build_system_prompt(self, user_profile: Optional[UserProfile]) -> str:
        """Build comprehensive system prompt with full user profile"""
        if not user_profile:
            return "Ты полезный AI-ассистент."
        
        prompt = "Ты полезный AI-ассистент. Вот полный профиль пользователя:\n\n"
        
        # Core attributes
        if user_profile.values:
            prompt += f"💎 Ценности: {', '.join(user_profile.values)}\n"
        
        if user_profile.beliefs:
            prompt += f"🌟 Убеждения: {', '.join(user_profile.beliefs)}\n"
        
        if user_profile.interests:
            prompt += f"🎯 Интересы: {', '.join(user_profile.interests)}\n"
        
        if user_profile.skills:
            prompt += f"🛠️ Навыки: {', '.join(user_profile.skills)}\n"
        
        if user_profile.desires:
            prompt += f"🎓 Цели и желания: {', '.join(user_profile.desires)}\n"
        
        if user_profile.intentions:
            prompt += f"📍 Текущие намерения: {', '.join(user_profile.intentions)}\n"
        
        # Preferences
        if user_profile.likes:
            prompt += f"👍 Нравится: {', '.join(user_profile.likes)}\n"
        
        if user_profile.dislikes:
            prompt += f"👎 Не нравится: {', '.join(user_profile.dislikes)}\n"
        
        if user_profile.loves:
            prompt += f"❤️ Любит: {', '.join(user_profile.loves)}\n"
        
        if user_profile.hates:
            prompt += f"🚫 Ненавидит: {', '.join(user_profile.hates)}\n"
        
        prompt += "\n📝 ВАЖНО: Используй этот профиль для формирования персонализированных ответов. Адаптируй свои примеры, рекомендации и стиль общения под ценности, интересы и предпочтения пользователя. Избегай тем из списка 'не нравится' и 'ненавидит'."
        
        return prompt
    
    def _format_messages(self, messages: List[Message], user_profile: Optional[UserProfile]) -> List[Dict[str, str]]:
        """Format messages for LLM API"""
        formatted = []
        
        # Add system message with profile
        system_prompt = self._build_system_prompt(user_profile)
        formatted.append({"role": "system", "content": system_prompt})
        
        # Add conversation history (limit to MAX_CONTEXT_MESSAGES to stay within context)
        max_messages = self.settings.MAX_CONTEXT_MESSAGES
        for msg in messages[-max_messages:]:
            formatted.append({
                "role": msg.role.value,
                "content": msg.content
            })
        
        return formatted
    
    async def generate_response(
        self,
        model: str,
        messages: List[Message],
        user_profile: Optional[UserProfile] = None,
    ) -> Dict[str, Any]:
        """Generate response from LLM via OpenRouter (non-streaming)"""
        
        formatted_messages = self._format_messages(messages, user_profile)
        
        # All models go through OpenRouter
        return await self._generate_openrouter(model, formatted_messages)
    
    async def stream_response(
        self,
        model: str,
        messages: List[Message],
        user_profile: Optional[UserProfile] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream response from LLM via OpenRouter"""
        
        formatted_messages = self._format_messages(messages, user_profile)
        
        # All models stream through OpenRouter
        async for chunk in self._stream_openrouter(model, formatted_messages):
            yield chunk
    
    # OpenRouter (unified gateway)
    async def _generate_openrouter(self, model: str, messages: List[Dict]) -> Dict[str, Any]:
        """Generate response from OpenRouter"""
        response = await self.openrouter_client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=self.settings.LLM_TEMPERATURE,
        )
        
        content = response.choices[0].message.content
        tokens_input = response.usage.prompt_tokens if response.usage else 0
        tokens_output = response.usage.completion_tokens if response.usage else 0
        
        # Calculate cost (approximate, in rubles)
        cost = self._calculate_cost(model, tokens_input, tokens_output)
        
        return {
            "content": content,
            "tokens": {"input": tokens_input, "output": tokens_output},
            "cost": cost,
        }
    
    async def _stream_openrouter(self, model: str, messages: List[Dict]) -> AsyncGenerator:
        """Stream response from OpenRouter"""
        print(f"🔄 Starting stream for model: {model}")
        
        try:
            stream = await self.openrouter_client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=self.settings.LLM_TEMPERATURE,
                stream=True
                # Note: stream_options not supported by current OpenAI SDK version
            )
            
            total_tokens_input = 0
            total_tokens_output = 0
            accumulated_content = ""
            chunk_count = 0
            
            # Estimate input tokens (approximate: 1 token ≈ 4 characters)
            input_text = " ".join([msg.get("content", "") for msg in messages])
            total_tokens_input = len(input_text) // 4
            
            async for chunk in stream:
                chunk_count += 1
                
                # Handle content chunks
                if chunk.choices and len(chunk.choices) > 0 and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    accumulated_content += content
                    total_tokens_output += 1  # Approximate token count
                    
                    # Debug log every 10 chunks
                    if chunk_count % 10 == 0:
                        print(f"📦 Chunk {chunk_count}: {len(content)} chars, total: {len(accumulated_content)}")
                    
                    yield {
                        "content": content,
                        "tokens": {"input": total_tokens_input, "output": total_tokens_output},
                        "cost": self._calculate_cost(model, total_tokens_input, total_tokens_output),
                    }
                
                # Try to get usage data from final chunk (if available)
                if hasattr(chunk, 'usage') and chunk.usage:
                    try:
                        # OpenAI SDK returns usage as an object with attributes
                        if hasattr(chunk.usage, 'prompt_tokens'):
                            total_tokens_input = chunk.usage.prompt_tokens or 0
                            total_tokens_output = chunk.usage.completion_tokens or total_tokens_output
                        # Or as a dict
                        elif isinstance(chunk.usage, dict):
                            total_tokens_input = chunk.usage.get('prompt_tokens', 0)
                            total_tokens_output = chunk.usage.get('completion_tokens', total_tokens_output)
                        print(f"📊 Final usage: {total_tokens_input} in, {total_tokens_output} out")
                    except Exception as e:
                        print(f"⚠️ Could not extract usage data: {e}")
            
            print(f"✅ Stream completed: {chunk_count} chunks, {len(accumulated_content)} total chars")
            
            # Yield final chunk with accurate token counts
            yield {
                "content": "",
                "tokens": {"input": total_tokens_input, "output": total_tokens_output},
                "cost": self._calculate_cost(model, total_tokens_input, total_tokens_output),
                "final": True
            }
        except Exception as e:
            print(f"❌ Stream error: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    
    def _calculate_cost(self, model: str, tokens_input: int, tokens_output: int) -> float:
        """Calculate cost in rubles (OpenRouter pricing)"""
        # OpenRouter pricing per 1K tokens in USD
        # https://openrouter.ai/docs#models
        pricing = {
            # OpenAI models
            "openai/gpt-4-turbo": {"input": 0.01, "output": 0.03},
            "openai/gpt-4": {"input": 0.03, "output": 0.06},
            "openai/gpt-3.5-turbo": {"input": 0.0015, "output": 0.002},
            
            # Anthropic Claude models
            "anthropic/claude-3-opus": {"input": 0.015, "output": 0.075},
            "anthropic/claude-3-sonnet": {"input": 0.003, "output": 0.015},
            "anthropic/claude-3-haiku": {"input": 0.00025, "output": 0.00125},
            
            # Google models
            "google/gemini-pro": {"input": 0.000125, "output": 0.000375},
            "google/gemini-pro-1.5": {"input": 0.0005, "output": 0.0015},
            
            # Meta Llama models
            "meta-llama/llama-3-70b-instruct": {"input": 0.00059, "output": 0.00079},
            "meta-llama/llama-3-8b-instruct": {"input": 0.00006, "output": 0.00006},
        }
        
        # Default pricing if model not found
        prices = pricing.get(model, {"input": 0.001, "output": 0.002})
        
        # Calculate cost in USD
        cost_usd = (tokens_input / 1000 * prices["input"]) + (tokens_output / 1000 * prices["output"])
        
        # Convert to RUB (approximate rate: 1 USD = 95 RUB)
        cost_rub = cost_usd * 95
        
        return round(cost_rub, 4)

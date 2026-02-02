"""
LLM Service for interacting with various AI models via OpenRouter
"""
from typing import List, Dict, Any, AsyncGenerator, Optional
from openai import AsyncOpenAI

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
        """Build system prompt with user profile"""
        if not user_profile:
            return "Ты полезный AI-ассистент."
        
        prompt = "Ты полезный AI-ассистент. Вот информация о пользователе:\n\n"
        
        if user_profile.values:
            values_str = ", ".join([f"{v['name']} ({v['value']}/100)" for v in user_profile.values])
            prompt += f"Ценности: {values_str}\n"
        
        if user_profile.interests:
            prompt += f"Интересы: {', '.join(user_profile.interests)}\n"
        
        if user_profile.skills:
            skills_str = ", ".join([f"{s['name']} (уровень {s['level']}/5)" for s in user_profile.skills])
            prompt += f"Навыки: {skills_str}\n"
        
        if user_profile.desires:
            prompt += f"Цели: {', '.join(user_profile.desires)}\n"
        
        prompt += "\nУчитывай этот контекст при формировании ответов. Адаптируй примеры и рекомендации под интересы и навыки пользователя."
        
        return prompt
    
    def _format_messages(self, messages: List[Message], user_profile: Optional[UserProfile]) -> List[Dict[str, str]]:
        """Format messages for LLM API"""
        formatted = []
        
        # Add system message with profile
        system_prompt = self._build_system_prompt(user_profile)
        formatted.append({"role": "system", "content": system_prompt})
        
        # Add conversation history (last 20 messages to stay within context)
        for msg in messages[-20:]:
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
            temperature=0.7,
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
        stream = await self.openrouter_client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.7,
            stream=True,
        )
        
        total_tokens_input = 0
        total_tokens_output = 0
        
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                total_tokens_output += 1  # Approximate
                
                yield {
                    "content": content,
                    "tokens": {"input": total_tokens_input, "output": total_tokens_output},
                    "cost": self._calculate_cost(model, total_tokens_input, total_tokens_output),
                }
    
    
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

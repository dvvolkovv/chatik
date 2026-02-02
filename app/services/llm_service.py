"""
LLM Service for interacting with various AI models
"""
from typing import List, Dict, Any, AsyncGenerator, Optional
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic
import google.generativeai as genai

from app.core.config import Settings
from app.models.message import Message
from app.models.profile import UserProfile


class LLMService:
    """Service for LLM interactions"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        
        # Initialize clients
        if settings.OPENAI_API_KEY:
            self.openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        
        if settings.ANTHROPIC_API_KEY:
            self.anthropic_client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        
        if settings.GOOGLE_API_KEY:
            genai.configure(api_key=settings.GOOGLE_API_KEY)
    
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
        """Generate response from LLM (non-streaming)"""
        
        formatted_messages = self._format_messages(messages, user_profile)
        
        if model.startswith("gpt"):
            return await self._generate_openai(model, formatted_messages)
        elif model.startswith("claude"):
            return await self._generate_anthropic(model, formatted_messages)
        elif model.startswith("gemini"):
            return await self._generate_google(model, formatted_messages)
        else:
            raise ValueError(f"Unknown model: {model}")
    
    async def stream_response(
        self,
        model: str,
        messages: List[Message],
        user_profile: Optional[UserProfile] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream response from LLM"""
        
        formatted_messages = self._format_messages(messages, user_profile)
        
        if model.startswith("gpt"):
            async for chunk in self._stream_openai(model, formatted_messages):
                yield chunk
        elif model.startswith("claude"):
            async for chunk in self._stream_anthropic(model, formatted_messages):
                yield chunk
        elif model.startswith("gemini"):
            async for chunk in self._stream_google(model, formatted_messages):
                yield chunk
        else:
            raise ValueError(f"Unknown model: {model}")
    
    # OpenAI
    async def _generate_openai(self, model: str, messages: List[Dict]) -> Dict[str, Any]:
        """Generate response from OpenAI"""
        response = await self.openai_client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.7,
        )
        
        content = response.choices[0].message.content
        tokens_input = response.usage.prompt_tokens
        tokens_output = response.usage.completion_tokens
        
        # Calculate cost (approximate, in rubles)
        cost = self._calculate_cost(model, tokens_input, tokens_output)
        
        return {
            "content": content,
            "tokens": {"input": tokens_input, "output": tokens_output},
            "cost": cost,
        }
    
    async def _stream_openai(self, model: str, messages: List[Dict]) -> AsyncGenerator:
        """Stream response from OpenAI"""
        stream = await self.openai_client.chat.completions.create(
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
    
    # Anthropic (Claude)
    async def _generate_anthropic(self, model: str, messages: List[Dict]) -> Dict[str, Any]:
        """Generate response from Anthropic"""
        # Extract system message
        system = next((m["content"] for m in messages if m["role"] == "system"), "")
        user_messages = [m for m in messages if m["role"] != "system"]
        
        response = await self.anthropic_client.messages.create(
            model=model,
            max_tokens=4096,
            system=system,
            messages=user_messages,
        )
        
        content = response.content[0].text
        tokens_input = response.usage.input_tokens
        tokens_output = response.usage.output_tokens
        cost = self._calculate_cost(model, tokens_input, tokens_output)
        
        return {
            "content": content,
            "tokens": {"input": tokens_input, "output": tokens_output},
            "cost": cost,
        }
    
    async def _stream_anthropic(self, model: str, messages: List[Dict]) -> AsyncGenerator:
        """Stream response from Anthropic"""
        system = next((m["content"] for m in messages if m["role"] == "system"), "")
        user_messages = [m for m in messages if m["role"] != "system"]
        
        async with self.anthropic_client.messages.stream(
            model=model,
            max_tokens=4096,
            system=system,
            messages=user_messages,
        ) as stream:
            async for text in stream.text_stream:
                yield {
                    "content": text,
                    "tokens": {"input": 0, "output": 1},
                    "cost": 0.0,
                }
    
    # Google (Gemini)
    async def _generate_google(self, model: str, messages: List[Dict]) -> Dict[str, Any]:
        """Generate response from Google Gemini"""
        # Gemini uses a different format
        model_instance = genai.GenerativeModel(model)
        
        # Convert messages to Gemini format
        prompt = "\n".join([f"{m['role']}: {m['content']}" for m in messages])
        
        response = await model_instance.generate_content_async(prompt)
        content = response.text
        
        # Approximate tokens (Gemini doesn't provide exact counts)
        tokens_input = len(prompt) // 4
        tokens_output = len(content) // 4
        cost = self._calculate_cost(model, tokens_input, tokens_output)
        
        return {
            "content": content,
            "tokens": {"input": tokens_input, "output": tokens_output},
            "cost": cost,
        }
    
    async def _stream_google(self, model: str, messages: List[Dict]) -> AsyncGenerator:
        """Stream response from Google Gemini"""
        model_instance = genai.GenerativeModel(model)
        prompt = "\n".join([f"{m['role']}: {m['content']}" for m in messages])
        
        response = await model_instance.generate_content_async(prompt, stream=True)
        
        async for chunk in response:
            if chunk.text:
                yield {
                    "content": chunk.text,
                    "tokens": {"input": 0, "output": 1},
                    "cost": 0.0,
                }
    
    def _calculate_cost(self, model: str, tokens_input: int, tokens_output: int) -> float:
        """Calculate cost in rubles"""
        # Prices per 1K tokens in USD
        pricing = {
            "gpt-4-turbo": {"input": 0.01, "output": 0.03},
            "gpt-3.5-turbo": {"input": 0.0015, "output": 0.002},
            "claude-3-opus": {"input": 0.015, "output": 0.075},
            "claude-3-sonnet": {"input": 0.003, "output": 0.015},
            "gemini-pro": {"input": 0.00025, "output": 0.0005},
        }
        
        # Default pricing if model not found
        prices = pricing.get(model, {"input": 0.001, "output": 0.002})
        
        # Calculate cost in USD
        cost_usd = (tokens_input / 1000 * prices["input"]) + (tokens_output / 1000 * prices["output"])
        
        # Convert to RUB (approximate rate: 1 USD = 90 RUB)
        cost_rub = cost_usd * 90
        
        return round(cost_rub, 4)

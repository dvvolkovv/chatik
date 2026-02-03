"""
Profile Extractor Service for automatic profile information extraction from messages
"""
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI
import json
import logging

from app.core.config import Settings
from app.models.profile import UserProfile

logger = logging.getLogger(__name__)


class ProfileExtractor:
    """Service for extracting profile information from user messages using LLM"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        
        # Initialize OpenRouter client for profile extraction
        if settings.OPENROUTER_API_KEY:
            self.client = AsyncOpenAI(
                api_key=settings.OPENROUTER_API_KEY,
                base_url="https://openrouter.ai/api/v1"
            )
    
    def _build_extraction_prompt(self) -> str:
        """Build system prompt for profile extraction"""
        return """Ты — эксперт по анализу текста. Твоя задача — извлечь информацию о пользователе из диалога.

Анализируй ТОЛЬКО явную информацию, которую пользователь сам сообщил о себе. Не делай предположений.

Извлекай:
**Основные атрибуты:**
1. **values** - ценности, что важно для человека (список строк)
2. **beliefs** - убеждения, принципы, мировоззрение (список строк)
3. **interests** - интересы, хобби, темы которыми интересуется (список строк)
4. **skills** - навыки и умения (список строк)
5. **desires** - цели, желания, планы на будущее (список строк)
6. **intentions** - текущие намерения, проекты, чем занимается сейчас (список строк)

**Предпочтения:**
7. **likes** - что нравится (вещи, занятия, привычки) (список строк)
8. **dislikes** - что не нравится, что раздражает (список строк)
9. **loves** - что любит, что очень важно (список строк)
10. **hates** - что ненавидит, категорически не принимает (список строк)

Верни ТОЛЬКО валидный JSON без дополнительного текста:
{
  "values": ["семья", "развитие"],
  "beliefs": ["важно учиться всю жизнь"],
  "interests": ["Python", "AI"],
  "skills": ["FastAPI", "машинное обучение"],
  "desires": ["создать AI продукт"],
  "intentions": ["работаю над чат-ботом"],
  "likes": ["кофе", "утренние прогулки"],
  "dislikes": ["ожидание", "шум"],
  "loves": ["создавать продукты"],
  "hates": ["несправедливость"]
}

Если информации нет - верни пустые массивы для всех полей."""
    
    async def extract_from_messages(
        self,
        user_message: str,
        assistant_message: str
    ) -> Dict[str, Any]:
        """
        Extract profile information from conversation messages
        
        Args:
            user_message: User's message content
            assistant_message: Assistant's response content
            
        Returns:
            Dictionary with extracted profile data
        """
        # Skip if message too short
        if len(user_message) < self.settings.PROFILE_MIN_MESSAGE_LENGTH:
            logger.debug(f"Message too short ({len(user_message)} chars), skipping extraction")
            return self._empty_extraction()
        
        try:
            # Build conversation for analysis
            messages = [
                {"role": "system", "content": self._build_extraction_prompt()},
                {"role": "user", "content": f"Сообщение пользователя: {user_message}"},
                {"role": "assistant", "content": f"Ответ ассистента: {assistant_message}"},
                {"role": "user", "content": "Извлеки информацию о пользователе в JSON формате."}
            ]
            
            logger.info(f"[Profile Extraction] Starting extraction for message: {user_message[:50]}...")
            
            # Call LLM for extraction
            response = await self.client.chat.completions.create(
                model=self.settings.PROFILE_EXTRACTION_MODEL,
                messages=messages,
                temperature=self.settings.PROFILE_EXTRACTION_TEMPERATURE,
                max_tokens=1000
            )
            
            content = response.choices[0].message.content.strip()
            logger.debug(f"[Profile Extraction] LLM response: {content}")
            
            # Parse JSON response
            # Remove markdown code blocks if present
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            extracted_data = json.loads(content)
            
            # Validate structure
            validated_data = self._validate_extraction(extracted_data)
            
            logger.info(f"[Profile Extraction] Successfully extracted: {sum(len(v) for v in validated_data.values())} items")
            
            return validated_data
            
        except json.JSONDecodeError as e:
            logger.error(f"[Profile Extraction] Failed to parse JSON: {e}")
            logger.error(f"[Profile Extraction] Content: {content}")
            return self._empty_extraction()
        except Exception as e:
            logger.error(f"[Profile Extraction] Error during extraction: {e}")
            return self._empty_extraction()
    
    def _validate_extraction(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and normalize extracted data"""
        validated = {
            "values": [],
            "beliefs": [],
            "interests": [],
            "skills": [],
            "desires": [],
            "intentions": [],
            "likes": [],
            "dislikes": [],
            "loves": [],
            "hates": []
        }
        
        # Helper to validate simple string lists
        def validate_string_list(key: str, max_items: int = 20) -> List[str]:
            if key in data and isinstance(data[key], list):
                return [
                    str(item).strip() 
                    for item in data[key] 
                    if item and len(str(item).strip()) > 0
                ][:max_items]
            return []
        
        # Validate all fields as simple string lists
        validated["values"] = validate_string_list("values")
        validated["beliefs"] = validate_string_list("beliefs")
        validated["interests"] = validate_string_list("interests")
        validated["skills"] = validate_string_list("skills")
        validated["desires"] = validate_string_list("desires")
        validated["intentions"] = validate_string_list("intentions")
        validated["likes"] = validate_string_list("likes")
        validated["dislikes"] = validate_string_list("dislikes")
        validated["loves"] = validate_string_list("loves")
        validated["hates"] = validate_string_list("hates")
        
        return validated
    
    def _empty_extraction(self) -> Dict[str, Any]:
        """Return empty extraction result"""
        return {
            "values": [],
            "beliefs": [],
            "interests": [],
            "skills": [],
            "desires": [],
            "intentions": [],
            "likes": [],
            "dislikes": [],
            "loves": [],
            "hates": []
        }
    
    def merge_with_existing(
        self,
        existing_profile: UserProfile,
        extracted_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Merge extracted data with existing profile intelligently
        
        Args:
            existing_profile: Current user profile from DB
            extracted_data: Newly extracted profile data
            
        Returns:
            Merged profile data ready to save
        """
        merged = {
            # Core attributes
            "values": self._merge_lists(
                existing_profile.values or [],
                extracted_data.get("values", []),
                max_items=50
            ),
            "beliefs": self._merge_lists(
                existing_profile.beliefs or [],
                extracted_data.get("beliefs", []),
                max_items=50
            ),
            "interests": self._merge_lists(
                existing_profile.interests or [],
                extracted_data.get("interests", []),
                max_items=50
            ),
            "skills": self._merge_lists(
                existing_profile.skills or [],
                extracted_data.get("skills", []),
                max_items=50
            ),
            "desires": self._merge_lists(
                existing_profile.desires or [],
                extracted_data.get("desires", []),
                max_items=50
            ),
            "intentions": self._merge_lists(
                existing_profile.intentions or [],
                extracted_data.get("intentions", []),
                max_items=30
            ),
            # Preferences
            "likes": self._merge_lists(
                existing_profile.likes or [],
                extracted_data.get("likes", []),
                max_items=50
            ),
            "dislikes": self._merge_lists(
                existing_profile.dislikes or [],
                extracted_data.get("dislikes", []),
                max_items=50
            ),
            "loves": self._merge_lists(
                existing_profile.loves or [],
                extracted_data.get("loves", []),
                max_items=50
            ),
            "hates": self._merge_lists(
                existing_profile.hates or [],
                extracted_data.get("hates", []),
                max_items=50
            )
        }
        
        return merged
    
    def _merge_lists(
        self,
        existing: List[str],
        new: List[str],
        max_items: int = 50
    ) -> List[str]:
        """Merge two lists removing duplicates (case-insensitive)"""
        # Create lowercase set for comparison
        existing_lower = {item.lower() for item in existing}
        
        # Add new items that don't exist
        merged = list(existing)
        for item in new:
            if item.lower() not in existing_lower:
                merged.append(item)
                existing_lower.add(item.lower())
        
        # Limit total items
        return merged[:max_items]
    

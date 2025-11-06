"""
Gemini AI Helper for NEPTUN Alert System
Улучшает распознавание городов и исправляет опечатки в сообщениях о угрозах
"""

import os
import logging
from typing import Optional, Tuple, Dict
import google.generativeai as genai

log = logging.getLogger(__name__)

# Initialize Gemini
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
GEMINI_ENABLED = bool(GEMINI_API_KEY)

if GEMINI_ENABLED:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        log.info("✅ Gemini AI initialized successfully")
    except Exception as e:
        log.error(f"❌ Failed to initialize Gemini: {e}")
        GEMINI_ENABLED = False
else:
    log.warning("⚠️ Gemini API key not found - AI features disabled")


def fix_message_typos(text: str) -> str:
    """
    Исправляет опечатки в сообщениях о угрозах
    
    Args:
        text: Оригинальное сообщение
        
    Returns:
        Исправленное сообщение
    """
    if not GEMINI_ENABLED or not text:
        return text
    
    try:
        prompt = f"""Ти - експерт з української мови. Виправ орфографічні помилки в цьому повідомленні про повітряну тривогу, але НЕ змінюй структуру та НЕ додавай нічого нового. Просто виправ опечатки у назвах міст та ключових словах.

Повідомлення: {text}

Поверни ТІЛЬКИ виправлений текст, без пояснень."""

        response = model.generate_content(
            prompt,
            generation_config={
                'temperature': 0.1,  # Минимальная креативность - только исправления
                'max_output_tokens': 500,
            }
        )
        
        corrected = response.text.strip()
        
        # Проверка что AI не добавил лишнего
        if len(corrected) > len(text) * 1.5:
            log.warning("⚠️ Gemini returned too long response, using original")
            return text
            
        log.debug(f"✨ Gemini corrected: '{text[:50]}...' → '{corrected[:50]}...'")
        return corrected
        
    except Exception as e:
        log.error(f"❌ Gemini typo correction error: {e}")
        return text


def extract_city_from_text(text: str, region: Optional[str] = None) -> Optional[Tuple[str, float]]:
    """
    Извлекает название города из сложного текста используя AI
    
    Args:
        text: Текст сообщения
        region: Область (опционально) для уточнения
        
    Returns:
        (city_name, confidence) или None
    """
    if not GEMINI_ENABLED or not text:
        return None
    
    try:
        region_hint = f" в {region} області" if region else ""
        
        prompt = f"""Ти - експерт з географії України. З цього повідомлення про повітряну тривогу витягни ТІЛЬКИ назву міста або населеного пункту{region_hint}.

Повідомлення: {text}

Поверни ТІЛЬКИ назву міста в називному відмінку (наприклад: "Київ", "Харків", "Дніпро"), без додаткових слів. Якщо міста немає - поверни "НЕМАЄ"."""

        response = model.generate_content(
            prompt,
            generation_config={
                'temperature': 0.1,
                'max_output_tokens': 50,
            }
        )
        
        city = response.text.strip()
        
        # Проверка результата
        if city == "НЕМАЄ" or len(city) > 50 or '\n' in city:
            return None
            
        # Оценка уверенности (простая эвристика)
        confidence = 0.8 if region else 0.6
        
        log.debug(f"✨ Gemini extracted city: '{city}' (confidence: {confidence})")
        return (city, confidence)
        
    except Exception as e:
        log.error(f"❌ Gemini city extraction error: {e}")
        return None


def classify_threat_type(text: str) -> Optional[str]:
    """
    Классифицирует тип угрозы используя AI
    
    Args:
        text: Текст сообщения
        
    Returns:
        Тип угрозы: 'shahed', 'cruise_missile', 'ballistic_missile', 'aviation', etc.
    """
    if not GEMINI_ENABLED or not text:
        return None
    
    try:
        prompt = f"""Визнач ТИП повітряної загрози з цього повідомлення. Поверни ТІЛЬКИ ОДНЕ слово з цього списку:
- shahed (БпЛА, дрони, Шахед)
- cruise_missile (крилаті ракети, КР)
- ballistic_missile (балістичні ракети, Іскандер)
- aviation (авіація, літаки, Ту-95)
- artillery (артилерія, РСЗВ, Град)
- unknown (невідомо)

Повідомлення: {text}

Поверни ТІЛЬКИ одне слово з списку вище."""

        response = model.generate_content(
            prompt,
            generation_config={
                'temperature': 0.1,
                'max_output_tokens': 20,
            }
        )
        
        threat_type = response.text.strip().lower()
        
        # Валидация результата
        valid_types = ['shahed', 'cruise_missile', 'ballistic_missile', 'aviation', 'artillery', 'unknown']
        if threat_type not in valid_types:
            return None
            
        log.debug(f"✨ Gemini classified threat: {threat_type}")
        return threat_type
        
    except Exception as e:
        log.error(f"❌ Gemini threat classification error: {e}")
        return None


def get_ai_stats() -> Dict[str, any]:
    """
    Возвращает статистику использования AI
    """
    return {
        'enabled': GEMINI_ENABLED,
        'model': 'gemini-1.5-flash' if GEMINI_ENABLED else None,
        'api_key_configured': bool(GEMINI_API_KEY),
    }

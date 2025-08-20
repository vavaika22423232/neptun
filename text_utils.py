import re

def clean_message_text(text):
    """
    Очищает текст сообщения от служебных элементов и форматирования.
    
    Args:
        text: исходный текст сообщения
    
    Returns:
        str: очищенный текст
    """
    # 1. Markdown-ссылки на канал
    text = re.sub(r'\[.*?\]\(https?://t\.me/[^)]*\)', '', text, flags=re.IGNORECASE)
    
    # 2. Прямые ссылки
    text = re.sub(r'https?://\S+', '', text, flags=re.IGNORECASE)
    
    # 3. Текстовые упоминания каналов и ботов
    text = re.sub(r'(український\s*\|\s*ппошник|ukrainskiy\s*\|\s*pposhnik|ukrainsiypposhnik|ппошник|pposhnik)', '', text, flags=re.IGNORECASE)
    text = re.sub(r'@\w+', '', text)  # упоминания
    
    # 4. Подписи в квадратных скобках
    text = re.sub(r'(✙\[.*?\]\([^\)]+\)✙\s*)+', '', text, flags=re.IGNORECASE)
    
    # 5. Специальные символы и эмодзи
    text = re.sub(r'[✙♥♦♣♠♪♫♬☺☻]', '', text)
    
    # 6. Хэштеги
    text = re.sub(r'#\w+', '', text)
    
    # 7. Множественные пробелы и переносы строк
    text = re.sub(r'\n+', '\n', text)
    text = re.sub(r'\s{2,}', ' ', text)
    
    return text.strip()

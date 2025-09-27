#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import process_message

def test_link_removal():
    print("=== ТЕСТ УДАЛЕНИЯ ССЫЛОК ===")
    
    # Тест с реальным сообщением об угрозе, но со ссылками
    message_with_links = """БпЛА курс на Полтаву
    
Дополнительная информация:
— Ссылка: https://send.monobank.ua/jar/4psGDZGeQb
— Телеграм: https://t.me/test_channel
@test_channel"""
    
    print("Исходное сообщение:")
    print(message_with_links)
    print("\n" + "="*50)
    
    try:
        result = process_message(message_with_links, "link_test", "2025-09-27 12:00:00", "test")
        
        if result and len(result) > 0:
            cleaned_text = result[0].get('text', '')
            print(f"Очищенный текст:\n{cleaned_text}")
            
            # Проверяем, что ссылки удалены
            links_removed = all([
                'https://' not in cleaned_text,
                'www.' not in cleaned_text,
                't.me/' not in cleaned_text,
                '@test_channel' not in cleaned_text,
                '4874100028842055' not in cleaned_text
            ])
            
            if links_removed:
                print("\n✅ ПРАВИЛЬНО: Все ссылки и реквизиты удалены")
            else:
                print("\n❌ НЕПРАВИЛЬНО: Некоторые ссылки остались")
                
            # Проверяем, что основной текст об угрозе остался
            if 'БпЛА' in cleaned_text and 'Полтаву' in cleaned_text:
                print("✅ ПРАВИЛЬНО: Основная информация об угрозе сохранена")
            else:
                print("❌ НЕПРАВИЛЬНО: Основная информация об угрозе потеряна")
                
        else:
            print("❌ Сообщение отфильтровано полностью")
            
    except Exception as e:
        print(f"❌ ОШИБКА: {e}")

if __name__ == "__main__":
    test_link_removal()

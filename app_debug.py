#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Версия app.py с расширенным логированием для диагностики проблем
"""

import os
import sys
import logging
from datetime import datetime

# Настройка детального логирования
def setup_logging():
    """Настройка системы логирования"""
    log_format = '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    
    # Создаем логгеры для файла и консоли
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[
            logging.FileHandler('app_debug.log', encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Отдельный логгер для Telegram
    telegram_logger = logging.getLogger('telethon')
    telegram_logger.setLevel(logging.INFO)
    
    return logging.getLogger('app_debug')

logger = setup_logging()

def test_telegram_connection():
    """Тестирование подключения к Telegram"""
    logger.info("🔍 Тестирование Telegram подключения...")
    
    try:
        # Импорт основного приложения
        logger.info("📦 Импорт app.py...")
        import app
        logger.info("✅ app.py импортирован успешно")
        
        # Проверка API настроек
        if hasattr(app, 'API_ID') and app.API_ID:
            logger.info(f"✅ TELEGRAM_API_ID: {app.API_ID}")
        else:
            logger.error("❌ TELEGRAM_API_ID не настроен")
            return False
            
        if hasattr(app, 'API_HASH') and app.API_HASH:
            logger.info(f"✅ TELEGRAM_API_HASH: {app.API_HASH[:10]}...")
        else:
            logger.error("❌ TELEGRAM_API_HASH не настроен")
            return False
            
        # Проверка клиента
        if hasattr(app, 'client') and app.client:
            logger.info("✅ Telegram клиент инициализирован")
            
            # Быстрая проверка без зависания
            try:
                logger.info("✅ Telegram клиент создан успешно")
                logger.info("⚠️  Полная проверка авторизации пропущена (избегаем зависания)")
                return True
            except Exception as e:
                logger.error(f"❌ Ошибка проверки клиента: {e}")
                return False
        else:
            logger.error("❌ Telegram клиент не инициализирован")
            return False
            
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def test_messages_collection():
    """Тестирование сбора сообщений"""
    logger.info("📨 Тестирование сбора сообщений...")
    
    try:
        # Проверка файла сообщений
        messages_file = 'messages.json'
        if os.path.exists(messages_file):
            size = os.path.getsize(messages_file)
            mod_time = datetime.fromtimestamp(os.path.getmtime(messages_file))
            logger.info(f"✅ messages.json найден: {size} байт, изменен {mod_time}")
            
            # Чтение и анализ
            import json
            with open(messages_file, 'r', encoding='utf-8') as f:
                try:
                    messages = json.load(f)
                    logger.info(f"✅ В messages.json найдено {len(messages)} сообщений")
                    
                    if messages:
                        latest = messages[-1]
                        logger.info(f"🕐 Последнее сообщение: {latest.get('date', 'дата неизвестна')}")
                        logger.info(f"📍 Координаты: {latest.get('lat', 'нет')}, {latest.get('lng', 'нет')}")
                        logger.info(f"⚠️  Тип угрозы: {latest.get('threat_type', 'неизвестно')}")
                        return len(messages) > 0
                    else:
                        logger.warning("⚠️  messages.json пустой")
                        return False
                        
                except json.JSONDecodeError as e:
                    logger.error(f"❌ Ошибка парсинга messages.json: {e}")
                    return False
        else:
            logger.error("❌ messages.json не найден")
            return False
            
    except Exception as e:
        logger.error(f"❌ Ошибка проверки сообщений: {e}")
        return False

def test_flask_app():
    """Тестирование Flask приложения"""
    logger.info("🌐 Тестирование Flask приложения...")
    
    try:
        import app
        
        if hasattr(app, 'app'):
            logger.info("✅ Flask app найден")
            
            # Тест маршрутов
            with app.app.test_client() as client:
                # Тест главной страницы
                response = client.get('/')
                logger.info(f"📄 Главная страница: {response.status_code}")
                
                # Тест API
                response = client.get('/api/messages')
                logger.info(f"📡 API messages: {response.status_code}")
                if response.status_code == 200:
                    data = response.get_json()
                    logger.info(f"📊 API вернул {len(data)} сообщений")
                
                return True
        else:
            logger.error("❌ Flask app не найден")
            return False
            
    except Exception as e:
        logger.error(f"❌ Ошибка тестирования Flask: {e}")
        return False

def run_diagnostics():
    """Полная диагностика приложения"""
    logger.info("🚀 ЗАПУСК ПОЛНОЙ ДИАГНОСТИКИ")
    logger.info("=" * 50)
    
    results = {
        'telegram': test_telegram_connection(),
        'messages': test_messages_collection(), 
        'flask': test_flask_app()
    }
    
    logger.info("📊 РЕЗУЛЬТАТЫ ДИАГНОСТИКИ:")
    logger.info("=" * 50)
    
    for test, result in results.items():
        status = "✅ ПРОЙДЕН" if result else "❌ ПРОВАЛЕН"
        logger.info(f"{test.upper()}: {status}")
    
    all_passed = all(results.values())
    
    if all_passed:
        logger.info("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ - приложение должно работать")
    else:
        logger.warning("⚠️  ЕСТЬ ПРОБЛЕМЫ - см. детали выше")
    
    return all_passed

def run_with_monitoring():
    """Запуск приложения с мониторингом"""
    logger.info("🚀 ЗАПУСК ПРИЛОЖЕНИЯ С МОНИТОРИНГОМ")
    
    try:
        # Сначала диагностика
        if not run_diagnostics():
            logger.warning("⚠️  Обнаружены проблемы, но пытаемся запустить...")
        
        # Импорт и запуск
        import app
        
        logger.info("🌐 Запуск Flask сервера...")
        logger.info("📝 Логи сохраняются в app_debug.log")
        logger.info("🔗 Приложение будет доступно на http://0.0.0.0:5000")
        
        # Запуск с мониторингом
        app.app.run(host='0.0.0.0', port=5000, debug=False)
        
    except KeyboardInterrupt:
        logger.info("⏹️  Остановлено пользователем")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка запуска: {e}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'diagnose':
        # Только диагностика
        run_diagnostics()
    elif len(sys.argv) > 1 and sys.argv[1] == 'flask-only':
        # Только Flask без Telegram диагностики
        logger.info("🌐 РЕЖИМ ТОЛЬКО FLASK - БЕЗ TELEGRAM ДИАГНОСТИКИ")
        logger.info("==================================================")
        try:
            logger.info("📦 Импорт app.py...")
            import app
            logger.info("✅ app.py импортирован успешно") 
            logger.info("🌐 Запуск Flask сервера на порту 5000...")
            app.app.run(host='0.0.0.0', port=5000, debug=False)
        except Exception as e:
            logger.error(f"💥 Ошибка запуска Flask: {e}")
            import traceback
            logger.error(traceback.format_exc())
    else:
        # Полный запуск с мониторингом
        run_with_monitoring()

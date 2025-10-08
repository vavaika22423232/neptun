#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Простая версия index.py без тяжелых зависимостей для тестирования на GMhost
"""

import sys
import os
import cgi
import cgitb
import json
from datetime import datetime

# Включаем отладку CGI  
cgitb.enable()

# CGI заголовки
print("Content-Type: text/html; charset=utf-8")
print("")

# Простая HTML страница с информацией
html = f"""<!DOCTYPE html>
<html lang="uk">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NEPTUN - GMhost Test</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        .status {{ background: #e8f5e8; padding: 20px; border-radius: 8px; }}
        .error {{ background: #ffe8e8; padding: 20px; border-radius: 8px; }}
        .info {{ background: #e8f0ff; padding: 20px; border-radius: 8px; margin: 20px 0; }}
        pre {{ background: #f5f5f5; padding: 10px; border-radius: 4px; }}
        .api-test {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 8px; }}
    </style>
</head>
<body>
    <h1>🛰️ NEPTUN - Система раннего предупреждения</h1>
    
    <div class="status">
        <h2>✅ Python CGI работает!</h2>
        <p><strong>Время:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p><strong>Python версия:</strong> {sys.version}</p>
        <p><strong>Текущая директория:</strong> {os.getcwd()}</p>
        <p><strong>Файлов в директории:</strong> {len(os.listdir('.')) if os.path.exists('.') else 0}</p>
    </div>
    
    <div class="info">
        <h3>📁 Файлы в директории:</h3>
        <pre>{chr(10).join(sorted(os.listdir('.')) if os.path.exists('.') else ['Нет доступа к директории'])}</pre>
    </div>
    
    <div class="api-test">
        <h3>🔗 Тестовые ссылки:</h3>
        <ul>
            <li><a href="api_messages.py">📡 API Messages (JSON)</a></li>
            <li><a href="test_cgi.py">🧪 CGI Test</a></li>
            <li><a href="messages.json">📄 Messages JSON</a> (если существует)</li>
        </ul>
    </div>
    
    <div class="info">
        <h3>📊 Состояние системы:</h3>
        <p><strong>Статус:</strong> Базовая система работает</p>
        <p><strong>Следующий шаг:</strong> Настройка Telegram API и получение данных</p>
        <p><strong>Версия:</strong> GMhost Test v1.0</p>
    </div>
    
    <script>
        // Простая проверка API
        fetch('api_messages.py')
            .then(response => response.json())
            .then(data => {{
                console.log('API Response:', data);
                document.getElementById('api-status').innerHTML = 
                    `<span style="color: green;">✅ API работает: ${{data.count || 0}} сообщений</span>`;
            }})
            .catch(error => {{
                console.error('API Error:', error);
                document.getElementById('api-status').innerHTML = 
                    `<span style="color: red;">❌ API недоступен: ${{error.message}}</span>`;
            }});
    </script>
    
    <p id="api-status">🔄 Проверяем API...</p>
    
    <hr>
    <footer>
        <p><em>NEPTUN System - Early Warning для України 🇺🇦</em></p>
    </footer>
</body>
</html>"""

print(html)

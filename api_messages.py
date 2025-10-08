#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import cgi
import cgitb
import json
from datetime import datetime

# Включаем отладку CGI
cgitb.enable()

# CGI заголовки
print("Status: 200 OK")
print("Content-Type: application/json; charset=utf-8")
print("Access-Control-Allow-Origin: *")
print("")

# Простая проверка API
try:
    # Проверяем наличие файла messages.json
    messages_file = "messages.json"
    if os.path.exists(messages_file):
        with open(messages_file, 'r', encoding='utf-8') as f:
            messages = json.load(f)
    else:
        messages = []
    
    # Возвращаем ответ
    response = {
        "status": "success",
        "count": len(messages),
        "messages": messages,
        "timestamp": datetime.now().isoformat(),
        "server_info": {
            "python_version": sys.version,
            "current_dir": os.getcwd(),
            "files_count": len(os.listdir(".")) if os.path.exists(".") else 0
        }
    }
    
    print(json.dumps(response, ensure_ascii=False, indent=2))

except Exception as e:
    error_response = {
        "status": "error",
        "message": str(e),
        "type": type(e).__name__,
        "server_info": {
            "python_version": sys.version,
            "current_dir": os.getcwd()
        }
    }
    print(json.dumps(error_response, ensure_ascii=False, indent=2))

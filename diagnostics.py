#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import cgi
import cgitb
import json
import os
from datetime import datetime

# Включаем отладку CGI
cgitb.enable()

# CGI заголовки
print("Content-Type: application/json; charset=utf-8")
print("Access-Control-Allow-Origin: *")
print("")

try:
    # Диагностическая информация
    diagnostics = {
        "timestamp": datetime.now().isoformat(),
        "server_status": "working",
        "current_directory": os.getcwd(),
        "files_in_directory": [],
        "messages_file_status": {},
        "python_info": {
            "version": "Python 3 (CGI)",
            "executable": "CGI Handler"
        }
    }
    
    # Список файлов
    try:
        diagnostics["files_in_directory"] = sorted(os.listdir("."))
    except Exception as e:
        diagnostics["files_in_directory"] = [f"Error: {str(e)}"]
    
    # Проверяем messages.json
    messages_file = "messages.json"
    if os.path.exists(messages_file):
        try:
            stat = os.stat(messages_file)
            with open(messages_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            diagnostics["messages_file_status"] = {
                "exists": True,
                "size_bytes": stat.st_size,
                "content_length": len(content),
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "preview": content[:200] + "..." if len(content) > 200 else content
            }
            
            # Попытка парсинга JSON
            try:
                messages = json.loads(content)
                diagnostics["messages_file_status"]["json_valid"] = True
                diagnostics["messages_file_status"]["messages_count"] = len(messages) if isinstance(messages, list) else "Not a list"
            except Exception as parse_error:
                diagnostics["messages_file_status"]["json_valid"] = False
                diagnostics["messages_file_status"]["parse_error"] = str(parse_error)
                
        except Exception as e:
            diagnostics["messages_file_status"] = {
                "exists": True,
                "error": str(e)
            }
    else:
        diagnostics["messages_file_status"] = {
            "exists": False,
            "message": "messages.json file not found"
        }
    
    print(json.dumps(diagnostics, ensure_ascii=False, indent=2))
    
except Exception as e:
    error_response = {
        "error": True,
        "message": str(e),
        "timestamp": datetime.now().isoformat()
    }
    print(json.dumps(error_response, ensure_ascii=False, indent=2))

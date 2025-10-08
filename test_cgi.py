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
print("Content-Type: application/json")
print("Access-Control-Allow-Origin: *")
print("")

# Простой тест
try:
    test_data = {
        "status": "ok",
        "message": "Python CGI работает",
        "timestamp": datetime.now().isoformat(),
        "python_version": sys.version,
        "current_dir": os.getcwd(),
        "files": os.listdir(".") if os.path.exists(".") else []
    }
    print(json.dumps(test_data, ensure_ascii=False, indent=2))
except Exception as e:
    error_data = {
        "status": "error",
        "message": str(e),
        "type": type(e).__name__
    }
    print(json.dumps(error_data, ensure_ascii=False, indent=2))

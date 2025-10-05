#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CGI wrapper для GMhost
Этот файл запускает Flask приложение через CGI
"""

import sys
import os
from wsgiref.handlers import CGIHandler

# Добавляем текущую директорию в путь Python
sys.path.insert(0, os.path.dirname(__file__))

# Импортируем Flask приложение
from app import app

if __name__ == '__main__':
    # Запускаем через CGI handler для GMhost
    CGIHandler().run(app)

@echo off
REM Запуск сервера тревог (alerts) с использованием виртуального окружения
cd /d %~dp0
call .venv\Scripts\activate.bat
python main.py
pause

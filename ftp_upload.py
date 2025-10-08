#!/usr/bin/env python3
"""
Простой FTP загрузчик для GMhost
"""
import ftplib
import os
import sys
from pathlib import Path

# FTP настройки для GMhost (замените на ваши)
FTP_HOST = "195.226.192.65"  # или ftp.yourdomain.com
FTP_USER = "your_ftp_user"    # ваш FTP логин
FTP_PASS = "your_ftp_pass"    # ваш FTP пароль
REMOTE_DIR = "/public_html"   # удаленная директория

# Список файлов для загрузки
FILES_TO_UPLOAD = [
    "index.py",
    "app.py", 
    "api_messages.py",
    "test_cgi.py",
    "test.html",
    ".htaccess",
    "messages.json",
    "requirements.txt"
]

def upload_files():
    """Загружает файлы по FTP"""
    try:
        # Подключение к FTP
        print(f"Подключение к {FTP_HOST}...")
        ftp = ftplib.FTP(FTP_HOST)
        ftp.login(FTP_USER, FTP_PASS)
        
        # Переход в нужную директорию
        try:
            ftp.cwd(REMOTE_DIR)
            print(f"Перешли в директорию: {REMOTE_DIR}")
        except:
            print(f"Не удалось перейти в {REMOTE_DIR}, работаем в корне")
        
        # Загружаем файлы
        for filename in FILES_TO_UPLOAD:
            if os.path.exists(filename):
                print(f"Загружаем {filename}...")
                with open(filename, 'rb') as file:
                    ftp.storbinary(f'STOR {filename}', file)
                    print(f"✅ {filename} загружен")
            else:
                print(f"⚠️ Файл {filename} не найден")
        
        # Устанавливаем права на выполнение для Python файлов
        for filename in FILES_TO_UPLOAD:
            if filename.endswith('.py'):
                try:
                    ftp.voidcmd(f'SITE CHMOD 755 {filename}')
                    print(f"Установлены права 755 для {filename}")
                except:
                    print(f"Не удалось установить права для {filename}")
        
        ftp.quit()
        print("✅ Загрузка завершена!")
        
    except Exception as e:
        print(f"❌ Ошибка FTP: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("🚀 FTP загрузчик для GMhost")
    print("Внимание: отредактируйте FTP_USER и FTP_PASS в скрипте!")
    
    if len(sys.argv) > 1 and sys.argv[1] == "--upload":
        upload_files()
    else:
        print("Для загрузки запустите: python3 ftp_upload.py --upload")

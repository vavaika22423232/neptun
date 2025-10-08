#!/usr/bin/env python3
"""
Автономный сервис для обновления данных NEPTUN каждые 2 минуты
Работает как демон без зависимости от cron
"""
import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime

# Добавляем путь к app.py
sys.path.append('/var/www/neptun')

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/neptun_daemon.log'),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

async def run_fetcher():
    """Запускает telegram_fetcher_v2.py в subprocess"""
    try:
        # Устанавливаем переменные окружения
        env = os.environ.copy()
        env.update({
            'TELEGRAM_API_ID': '24031340',
            'TELEGRAM_API_HASH': '2daaa58652e315ce52adb1090313d36a',
            'TELEGRAM_SESSION': '1BJWap1sBu6QoWnDN-K1gsnKkz_Y8EYEpkkY9s6jbhYQxQbdElK641Goae8BtQDxUHOf4gV1pIPGpWDrgvMol8Jz3plFMSBbFQ03zD_qK4UD5OMsbEr-30HrMgFbdWzJEJ4imVpMdYX31lS1CjQLnl3vfsXYfgx2BefuxEh4V7IKceSSoLTpqoY-IlzHbaitlquhE0zV2psEx0tBgFmyGpiCLwdHdH3ZWcm1KlUPkzXO3Ml4Q_VNbs1B2QFXx_BUN_klQNVLR5TvDz5ilGF7-uPQAmlb6F8-CxczYbVl6NyKnGq5p6ZhcLMPTuMg4UZOEclmwzTgS0SBshVSY4xFxfBdag2XUXuY='
        })
        
        # Запускаем скрипт
        process = await asyncio.create_subprocess_exec(
            '/var/www/neptun/venv/bin/python3',
            '/var/www/neptun/telegram_fetcher_v2.py',
            cwd='/var/www/neptun',
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # Ждем завершения с таймаутом 180 секунд
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=180)
            
            if process.returncode == 0:
                log.info("Telegram fetcher completed successfully")
                if stdout:
                    log.debug(f"STDOUT: {stdout.decode()[-500:]}")  # Последние 500 символов
            else:
                log.error(f"Telegram fetcher failed with code {process.returncode}")
                if stderr:
                    log.error(f"STDERR: {stderr.decode()[-500:]}")
                    
        except asyncio.TimeoutError:
            log.warning("Telegram fetcher timed out, terminating process")
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), timeout=10)
            except asyncio.TimeoutError:
                log.error("Force killing telegram fetcher process")
                process.kill()
                
    except Exception as e:
        log.error(f"Error running telegram fetcher: {e}")

async def main():
    """Основной цикл демона"""
    log.info("NEPTUN Daemon started")
    
    while True:
        try:
            start_time = time.time()
            log.info("Starting data fetch cycle")
            
            await run_fetcher()
            
            # Проверяем, что файл обновился
            try:
                stat = os.stat('/var/www/neptun/messages.json')
                file_time = datetime.fromtimestamp(stat.st_mtime)
                now = datetime.now()
                
                if (now - file_time).total_seconds() < 300:  # Обновлен за последние 5 минут
                    log.info(f"Data file updated successfully at {file_time}")
                else:
                    log.warning(f"Data file is old, last updated: {file_time}")
                    
            except Exception as e:
                log.error(f"Error checking data file: {e}")
            
            # Вычисляем время выполнения
            elapsed = time.time() - start_time
            log.info(f"Fetch cycle completed in {elapsed:.1f} seconds")
            
            # Ждем до следующего цикла (2 минуты)
            sleep_time = max(0, 120 - elapsed)
            if sleep_time > 0:
                log.info(f"Sleeping for {sleep_time:.1f} seconds until next cycle")
                await asyncio.sleep(sleep_time)
            else:
                log.warning("Fetch cycle took longer than 2 minutes!")
                
        except KeyboardInterrupt:
            log.info("Received interrupt signal, shutting down")
            break
        except Exception as e:
            log.error(f"Error in main loop: {e}")
            await asyncio.sleep(60)  # Ждем минуту перед повтором

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("NEPTUN Daemon stopped")

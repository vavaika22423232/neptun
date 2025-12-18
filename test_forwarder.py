#!/usr/bin/env python3
"""
Тестовий запуск Channel Forwarder локально
"""

# ВАЖЛИВО: Встановлюємо environment variables ПЕРЕД імпортом
import os
os.environ['TELEGRAM_API_ID'] = '24031340'
os.environ['TELEGRAM_API_HASH'] = '2daaa58652e315ce52adb1090313d36a'
os.environ['TELEGRAM_SESSION'] = '1BJWap1sBuy6rg3J6zXFs4Xtq-nKAqnHnKjxRIh7T3rmY4zF1YRHhhDX9UzPzw29NLqAVArSEV-XFx2KWHBZEQxsOLHLArWEgLkH2L_Q9-5p8zR5qnQU-yd8XXh0gGP5IAptyEcpM-U0FVi3lNaOBdAN9KqLko8Q0HfuzEaeJSu_tRV7rAHCcP1qd-CbeB9NQ8eZM-eSMph2nahucd__C27fJreae5OUaDgi6-jwxuoeJJsfv-wGTJWyZ1mmdCQL_Zg3nfVw8P0MEiIQG2Ha4WWPBD3ZF9TEg3w0Uhis2obwHJ3CRNM9nPg7fZH1dN29lUeAznpnnHVzPip0TBrZp0sE1n6qeru4='
os.environ['SOURCE_CHANNELS'] = 'UkraineAlarmSignal,kpszsu,war_monitor,napramok,raketa_trevoga,ukrainsiypposhnik'
os.environ['TARGET_CHANNEL'] = 'mapstransler'

import asyncio
from channel_forwarder_render import main

print("╔════════════════════════════════════════════════════╗")
print("║  🧪 ТЕСТОВИЙ ЗАПУСК Channel Forwarder              ║")
print("╚════════════════════════════════════════════════════╝")
print()
print("📋 Налаштування:")
print(f"   API_ID: {os.environ['TELEGRAM_API_ID']}")
print(f"   SESSION: {os.environ['TELEGRAM_SESSION'][:30]}...")
print(f"   TARGET: @{os.environ['TARGET_CHANNEL']}")
print()
print("🚀 Запускаю бота...")
print()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⏹️ Тест зупинено")
    except Exception as e:
        print(f"\n\n❌ Помилка: {e}")
        import traceback
        traceback.print_exc()

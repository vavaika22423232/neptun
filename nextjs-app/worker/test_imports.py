"""Quick test: can the worker import everything it needs?"""
import sys
print("Python:", sys.version)

errors = []

try:
    from constants import API_ID, API_HASH, CHANNELS
    print(f"OK constants (API_ID={API_ID}, CHANNELS={CHANNELS})")
except Exception as e:
    errors.append(("constants", e))
    print(f"FAIL constants: {e}")

try:
    from db import db
    print(f"OK db: type={type(db).__name__}, connected={db.is_connected()}")
except Exception as e:
    errors.append(("db", e))
    print(f"FAIL db: {e}")

try:
    from core.parser_v2 import extract_entities
    print("OK core.parser_v2")
except Exception as e:
    errors.append(("core.parser_v2", e))
    print(f"FAIL core.parser_v2: {e}")

try:
    from geo.resolver import resolve
    print("OK geo.resolver")
except Exception as e:
    errors.append(("geo.resolver", e))
    print(f"FAIL geo.resolver: {e}")

try:
    from constants import OBLAST_CENTERS
    print(f"OK OBLAST_CENTERS ({len(OBLAST_CENTERS)} entries)")
except Exception as e:
    errors.append(("OBLAST_CENTERS", e))
    print(f"FAIL OBLAST_CENTERS: {e}")

try:
    from telethon import TelegramClient, events
    from telethon.sessions import StringSession
    print("OK telethon")
except Exception as e:
    errors.append(("telethon", e))
    print(f"FAIL telethon: {e}")

try:
    import requests
    print("OK requests")
except Exception as e:
    errors.append(("requests", e))
    print(f"FAIL requests: {e}")

print(f"\nResult: {len(errors)} failures out of 7 imports")
if errors:
    for name, err in errors:
        print(f"  - {name}: {err}")

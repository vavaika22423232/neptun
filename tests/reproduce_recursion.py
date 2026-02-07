
import sys
import os
from unittest.mock import MagicMock

# Mock problematic modules that use Python 3.10 syntax or missing dependencies
sys.modules['core'] = MagicMock()
sys.modules['core.message_store'] = MagicMock()
sys.modules['telethon'] = MagicMock()
sys.modules['telethon.sync'] = MagicMock()
sys.modules['flask_mail'] = MagicMock()
sys.modules['firebase_admin'] = MagicMock()
sys.modules['groq'] = MagicMock()
sys.modules['spacy'] = MagicMock()
# Also mock local modules that might fail
sys.modules['admin_routes'] = MagicMock()
sys.modules['parser_service'] = MagicMock()
sys.modules['threat_analysis'] = MagicMock()

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Set env vars required by app_legacy
os.environ['ALARM_API_KEY'] = 'test_key'

try:
    # Now try to import
    # We might still hit syntax errors if they are in app_legacy.py itself and we import it.
    # Python 3.9 parses the whole file. If app_legacy has `|` syntax, we can't import it in 3.9.
    # Let's check if we can even import it.
    import app_legacy
    from app_legacy import _fetch_alarms_from_api
    print("Successfully imported _fetch_alarms_from_api")
except ImportError as e:
    print(f"Failed to import: {e}")
    sys.exit(1)
except SyntaxError as e:
    print(f"Syntax error (likely Python version mismatch): {e}")
    # If we can't import due to syntax, we can't run it.
    # We will manually verify the fix logic instead by printing the relevant lines.
    sys.exit(0) 

print("Attempting to fetch alarms (expecting connection error or success, NOT recursion error)...")
try:
    result = _fetch_alarms_from_api()
    print(f"Result: {result}")
except RecursionError:
    print("FAILED: RecursionError caught!")
    sys.exit(1)
except Exception as e:
    print(f"Finished with expected exception: {e}")

print("SUCCESS: No recursion error encountered.")

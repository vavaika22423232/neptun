# NEPTUN Alarm API - Main Application
# 
# This is a refactored version that uses Flask Blueprints for modularity.
# The original app.py (~22000 lines) has been split into:
#   - routes/alarms.py    - Alarm API proxy and monitoring
#   - routes/payments.py  - WayForPay, Monobank payments
#   - routes/blackout.py  - Power outage schedules
#   - routes/chat.py      - Anonymous chat
#   - routes/family.py    - Family safety SOS
#   - routes/admin.py     - Admin panel
#   - routes/pages.py     - Static pages, SEO
#   - routes/devices.py   - Device registration
#
# pyright: reportUnusedVariable=false
# type: ignore
# pylint: disable=all

import os
import gc
import json
import logging
import threading

from flask import Flask
from flask_compress import Compress

# Core modules
from core.message_store import MessageStore, DeviceStore, FamilyStore

# =============================================================================
# CONFIGURATION
# =============================================================================
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger(__name__)

# Memory optimization
gc.collect()

# =============================================================================
# FLASK APP INITIALIZATION
# =============================================================================
app = Flask(__name__)

# Enable gzip compression
compress = Compress()
compress.init_app(app)

# =============================================================================
# FILE PATHS (persistent on Render)
# =============================================================================
def get_persistent_path(filename):
    """Get persistent storage path."""
    persistent_dir = os.getenv('PERSISTENT_DATA_DIR', '/data')
    if persistent_dir and os.path.isdir(persistent_dir):
        return os.path.join(persistent_dir, filename)
    return filename

MESSAGES_PATH = get_persistent_path("messages.json")
DEVICES_PATH = get_persistent_path("devices.json")
FAMILY_PATH = get_persistent_path("family_status.json")

# =============================================================================
# DATA STORES
# =============================================================================
MESSAGE_STORE = MessageStore(path=MESSAGES_PATH)
device_store = DeviceStore(path=DEVICES_PATH)
family_store = FamilyStore(path=FAMILY_PATH)

# =============================================================================
# FIREBASE INITIALIZATION
# =============================================================================
firebase_initialized = False
messaging = None

def init_firebase():
    """Initialize Firebase Admin SDK."""
    global firebase_initialized, messaging
    if firebase_initialized:
        return True
    
    try:
        import firebase_admin
        from firebase_admin import credentials, messaging as firebase_messaging
        
        cred_json = os.environ.get('FIREBASE_CREDENTIALS')
        if cred_json:
            import base64
            cred_dict = json.loads(base64.b64decode(cred_json))
            cred = credentials.Certificate(cred_dict)
        elif os.path.exists('firebase-credentials.json'):
            cred = credentials.Certificate('firebase-credentials.json')
        else:
            log.warning("Firebase credentials not found")
            return False
        
        firebase_admin.initialize_app(cred)
        messaging = firebase_messaging
        firebase_initialized = True
        log.info("Firebase Admin SDK initialized successfully")
        return True
        
    except Exception as e:
        log.error(f"Failed to initialize Firebase: {e}")
        return False

# Initialize Firebase on startup
init_firebase()

# =============================================================================
# REGISTER BLUEPRINTS
# =============================================================================
from routes import (
    # Core blueprints
    alarms_bp,
    payments_bp,
    blackout_bp,
    chat_bp,
    family_bp,
    admin_bp,
    pages_bp,
    devices_bp,
    # New blueprints
    geocoding_bp,
    messages_bp,
    analytics_bp,
    telegram_bp,
    comments_bp,
    stream_bp,
    # Initialization functions
    start_alarm_monitoring,
    init_firebase_messaging,
    init_family_store,
    init_device_store,
    init_visits_db,
    init_comments_db,
    preload_comments,
)

# Initialize route modules with required dependencies
init_device_store(device_store)
init_family_store(family_store, firebase_initialized, messaging)
if firebase_initialized and messaging:
    init_firebase_messaging(firebase_initialized, messaging)

# Initialize databases
init_visits_db()
init_comments_db()
preload_comments()

# Register all blueprints
app.register_blueprint(alarms_bp)
app.register_blueprint(payments_bp)
app.register_blueprint(blackout_bp)
app.register_blueprint(chat_bp)
app.register_blueprint(family_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(pages_bp)
app.register_blueprint(devices_bp)
app.register_blueprint(geocoding_bp)
app.register_blueprint(messages_bp)
app.register_blueprint(analytics_bp)
app.register_blueprint(telegram_bp)
app.register_blueprint(comments_bp)
app.register_blueprint(stream_bp)

log.info("All blueprints registered successfully")

# =============================================================================
# START BACKGROUND SERVICES
# =============================================================================
if firebase_initialized:
    start_alarm_monitoring()
    log.info("Alarm monitoring started")
else:
    log.warning("Firebase not initialized - alarm monitoring disabled")

# =============================================================================
# GLOBAL MIDDLEWARE
# =============================================================================
@app.after_request
def add_security_headers(response):
    """Add security and cache headers to all responses."""
    # CORS
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    
    # Cache control for API
    if '/api/' in request.path:
        response.headers['Cache-Control'] = 'no-store'
    
    return response

from flask import request

@app.before_request
def log_request():
    """Log incoming requests for debugging."""
    if request.path.startswith('/api/') and request.method == 'POST':
        log.debug(f"Request: {request.method} {request.path}")

# =============================================================================
# MAIN ENTRY POINT
# =============================================================================
if __name__ == '__main__':
    port = int(os.getenv('PORT', '5000'))
    host = os.getenv('HOST', '0.0.0.0')
    log.info(f'Launching Flask app on {host}:{port}')
    app.run(host=host, port=port, debug=False)

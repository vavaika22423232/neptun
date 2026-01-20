"""
New application entry point (gradual migration).

Це новий entry point для поступової міграції на модульну архітектуру.
Використовує нові сервіси разом з legacy кодом з app.py.

Використання:
1. Для локальної розробки: python app_new.py
2. Для production: поки що використовуйте app.py
3. Коли всі endpoint'и мігровано - замініть app.py на цей файл
"""
import logging
import os

# Configure logging before imports
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
log = logging.getLogger(__name__)

# ==============================================================================
# CONFIGURATION
# ==============================================================================

from config import get_config

config = get_config()
log.info("Configuration loaded")
log.info(f"  Telegram: {'✓' if config.telegram.is_configured else '✗'}")
log.info(f"  Nominatim: {'✓' if config.geocoding.nominatim_enabled else '✗'}")
log.info(f"  Photon: {'✓' if config.geocoding.photon_enabled else '✗'}")
log.info(f"  Persistent storage: {'✓' if config.storage.is_persistent_available else '✗'}")


# ==============================================================================
# FLASK APP FACTORY
# ==============================================================================

def create_app(test_config=None):
    """Create and configure Flask application (factory pattern)."""
    from flask import Flask
    from flask_cors import CORS

    flask_app = Flask(__name__)
    CORS(flask_app, origins=config.server.cors_origins)

    # Apply test config if provided
    if test_config:
        flask_app.config.update(test_config)

    flask_app.config['ADMIN_API_KEY'] = os.getenv('ADMIN_SECRET', '')

    # Register blueprints
    from api import admin_bp, alarms_bp, chat_bp, data_bp, health_bp, sse_bp, tracks_bp
    flask_app.register_blueprint(health_bp)
    flask_app.register_blueprint(data_bp)
    flask_app.register_blueprint(alarms_bp)
    flask_app.register_blueprint(tracks_bp)
    flask_app.register_blueprint(sse_bp)
    flask_app.register_blueprint(admin_bp)
    flask_app.register_blueprint(chat_bp)

    return flask_app


# ==============================================================================
# FLASK APP (module-level for compatibility)
# ==============================================================================

from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app, origins=config.server.cors_origins)

# Store config in app
app.config['ADMIN_API_KEY'] = os.getenv('ADMIN_SECRET', '')


# ==============================================================================
# SERVICES INITIALIZATION
# ==============================================================================

from services.geocoding import (
    GeocodeCache,
    GeocoderChain,
    LocalGeocoder,
    OpenCageGeocoder,
    PhotonGeocoder,
)
from services.processing import MessagePipeline
from services.realtime import RealtimeService, create_marker_callback
from services.telegram import MessageParser
from services.tracks import TrackProcessor, TrackStore

# Initialize track store
track_store = TrackStore(
    file_path=config.storage.messages_file,
    retention_minutes=config.messages.retention_minutes,
    max_count=config.messages.max_count,
)
log.info(f"TrackStore initialized with {track_store.count()} tracks")

# Initialize geocoding chain
geocode_cache = GeocodeCache(
    cache_file=config.storage.geocode_cache_file,
    negative_cache_file=config.storage.negative_cache_file,
)
log.info(f"GeocodeCache loaded: {geocode_cache.stats()}")

# Build geocoder chain
geocoders = []

# 1. Local geocoder (always first) - load from data module
try:
    # Import city coords from data module (not app.py!)
    from data import CITY_COORDS, UKRAINE_ALL_SETTLEMENTS, UKRAINE_SETTLEMENTS_BY_OBLAST

    local_geocoder = LocalGeocoder(
        city_coords=CITY_COORDS,
        settlements=UKRAINE_ALL_SETTLEMENTS or None,
        settlements_by_oblast=UKRAINE_SETTLEMENTS_BY_OBLAST or None,
    )
    geocoders.append(local_geocoder)
    log.info(f"LocalGeocoder: {local_geocoder.stats()['city_coords']} cities loaded")
except Exception as e:
    log.warning(f"Failed to load LocalGeocoder: {e}")
    local_geocoder = None

# 2. Photon geocoder (free, OpenStreetMap based)
if config.geocoding.photon_enabled:
    try:
        photon_geocoder = PhotonGeocoder(
            url=config.geocoding.photon_url or PhotonGeocoder.DEFAULT_URL,
            timeout=3.0,
        )
        geocoders.append(photon_geocoder)
        log.info("PhotonGeocoder enabled")
    except Exception as e:
        log.warning(f"Failed to initialize PhotonGeocoder: {e}")

# 3. OpenCage geocoder (paid, fallback)
opencage_key = os.getenv('OPENCAGE_API_KEY')
if opencage_key:
    try:
        opencage_geocoder = OpenCageGeocoder(api_key=opencage_key)
        geocoders.append(opencage_geocoder)
        log.info("OpenCageGeocoder enabled (with API key)")
    except Exception as e:
        log.warning(f"Failed to initialize OpenCageGeocoder: {e}")

geocoder_chain = GeocoderChain(geocoders=geocoders, cache=geocode_cache)
log.info(f"GeocoderChain initialized with {len(geocoders)} geocoders")

# Initialize track processor
track_processor = TrackProcessor(
    store=track_store,
    geocoder=geocoder_chain,
)

# Initialize message parser
message_parser = MessageParser()

# Initialize realtime service (SSE)
realtime_service = RealtimeService()
log.info("RealtimeService initialized")

# Initialize message pipeline
message_pipeline = MessagePipeline(
    parser=message_parser,
    geocoder=geocoder_chain,
    track_store=track_store,
)
# Connect realtime notifications
message_pipeline.add_callback(create_marker_callback(realtime_service))
log.info("MessagePipeline initialized")

# Store services in app.extensions for blueprints
app.extensions['track_store'] = track_store
app.extensions['geocoder'] = geocoder_chain
app.extensions['parser'] = message_parser
app.extensions['pipeline'] = message_pipeline
app.extensions['realtime'] = realtime_service


# ==============================================================================
# REGISTER BLUEPRINTS
# ==============================================================================

from api import alarms_bp, data_bp, health_bp, sse_bp, tracks_bp
from api.admin import admin_bp, init_admin_api
from api.alarms import init_alarms_api
from api.data import init_data_api
from api.health import init_health_api

# Inject dependencies
init_data_api(track_store=track_store, geocoder=geocoder_chain)
init_health_api(track_store=track_store)
init_admin_api(
    admin_secret=os.getenv('ADMIN_SECRET'),
    track_store=track_store,
)

# Initialize alarms if configured
alarm_client = None
alarm_monitor = None
if config.alarms.is_configured:
    try:
        from services.alarms import AlarmClient, AlarmStateManager

        alarm_client = AlarmClient(
            api_key=config.alarms.api_key,
            api_url=config.alarms.api_url,
        )

        alarm_state = AlarmStateManager()

        # Try to get district mapping from main_app
        try:
            district_to_oblast = getattr(main_app, 'DISTRICT_TO_OBLAST', {})
        except:
            district_to_oblast = {}

        init_alarms_api(
            alarm_client=alarm_client,
            alarm_state=alarm_state,
            district_mapping=district_to_oblast,
        )

        # Store alarm state for realtime notifications
        app.extensions['alarm_state'] = alarm_state
        app.extensions['alarm_client'] = alarm_client

        log.info("AlarmClient initialized")
    except Exception as e:
        log.warning(f"Failed to initialize alarms: {e}")

# Register blueprints
from api import chat_bp

app.register_blueprint(data_bp)
app.register_blueprint(health_bp)
app.register_blueprint(alarms_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(tracks_bp)
app.register_blueprint(sse_bp)
app.register_blueprint(chat_bp)


# ==============================================================================
# LEGACY ROUTES (will be migrated to blueprints)
# ==============================================================================

# For now, import and use routes from app.py
# This allows gradual migration

@app.route('/')
def index():
    """Simple index page."""
    return jsonify({
        'name': 'Neptun API',
        'version': '2.0.0-alpha',
        'status': 'running',
        'architecture': 'modular',
    })


@app.route('/config')
def show_config():
    """Show current configuration (no secrets)."""
    return jsonify(config.to_dict())


# ==============================================================================
# STARTUP
# ==============================================================================

def startup():
    """Run startup tasks."""
    log.info("Starting application...")

    # Prune old tracks
    pruned = track_store.prune()
    if pruned > 0:
        log.info(f"Pruned {pruned} expired tracks")

    # Start background processor
    track_processor.start()
    log.info("Track processor started")

    # Start alarm monitoring if configured
    if alarm_client and config.alarms.is_configured:
        try:
            global alarm_monitor
            from services.alarms import AlarmMonitor

            alarm_monitor = AlarmMonitor(
                client=alarm_client,
                poll_interval=config.alarms.poll_interval,
                district_only=True,
            )
            alarm_monitor.start()
            log.info("Alarm monitor started")
        except Exception as e:
            log.warning(f"Failed to start alarm monitor: {e}")

    # Process any pending tracks
    pending = track_processor.process_now(max_items=20)
    if pending > 0:
        log.info(f"Processed {pending} pending tracks")

    # Save state
    try:
        track_store.save(force=True)
        geocode_cache.save()
    except Exception as e:
        log.warning(f"Failed to save state: {e}")


# ==============================================================================
# MAIN
# ==============================================================================

if __name__ == '__main__':
    startup()

    # Run Flask
    log.info(f"Starting server on {config.server.host}:{config.server.port}")
    app.run(
        host=config.server.host,
        port=config.server.port,
        debug=config.server.debug,
    )

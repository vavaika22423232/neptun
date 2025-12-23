"""
Neptun Alarm v2.0 - Clean Architecture
Ukrainian Air Alert Tracking System
"""
import os
import sys
import logging
from flask import Flask, render_template, send_from_directory, Response, request
from flask_compress import Compress
import time

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger(__name__)

# Import configuration
from core.config import (
    APP_NAME, APP_VERSION, DEBUG, HOST, PORT,
    STATIC_DIR, TEMPLATES_DIR
)

# Create Flask app
app = Flask(
    __name__,
    static_folder=STATIC_DIR,
    template_folder=TEMPLATES_DIR
)
app.config['JSON_AS_ASCII'] = False
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True

# Enable compression
Compress(app)


# === Middleware ===

@app.before_request
def before_request():
    """Log requests and track visitors"""
    # Skip static files
    if request.path.startswith('/static'):
        return
    
    # Track visitor
    try:
        from core.services.storage import visits_db
        visitor_id = request.cookies.get('vid') or request.headers.get('X-Visitor-ID')
        if visitor_id:
            ip = request.headers.get('X-Forwarded-For', request.remote_addr)
            visits_db.record_visit(visitor_id, ip)
    except Exception as e:
        log.debug(f"Visitor tracking error: {e}")


@app.after_request
def after_request(response):
    """Add cache headers"""
    # Cache static assets
    if request.path.startswith('/static'):
        response.headers['Cache-Control'] = 'public, max-age=86400'
    else:
        response.headers['Cache-Control'] = 'no-cache'
    
    # CORS for API
    if request.path.startswith('/api'):
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    
    return response


# === Page Routes ===

@app.route('/')
def index():
    """Main map page"""
    return render_template('index.html')


@app.route('/map-only')
def map_only():
    """Map without header (for embedding)"""
    return render_template('map_only.html')


@app.route('/map-embed')
def map_embed():
    """Embeddable map iframe"""
    return render_template('map_embed.html')


@app.route('/about')
def about():
    """About page"""
    return render_template('about.html')


@app.route('/faq')
def faq():
    """FAQ page"""
    return render_template('faq.html')


@app.route('/privacy')
def privacy():
    """Privacy policy"""
    return render_template('privacy.html')


@app.route('/terms')
def terms():
    """Terms of service"""
    return render_template('terms.html')


@app.route('/analytics')
def analytics():
    """Analytics dashboard"""
    return render_template('analytics.html')


# === SEO & Verification ===

@app.route('/robots.txt')
def robots():
    """Robots.txt for SEO"""
    content = """User-agent: *
Allow: /
Sitemap: https://neptun.in.ua/sitemap.xml
"""
    return Response(content, mimetype='text/plain')


@app.route('/sitemap.xml')
def sitemap():
    """Sitemap for SEO"""
    return send_from_directory(STATIC_DIR, 'sitemap.xml')


@app.route('/ads.txt')
def ads_txt():
    """AdSense verification"""
    return send_from_directory('.', 'ads.txt')


@app.route('/app-ads.txt')
def app_ads_txt():
    """AdMob verification"""
    return send_from_directory('.', 'app-ads.txt')


@app.route('/google<code>.html')
def google_verify(code):
    """Google verification"""
    return f"google-site-verification: google{code}.html"


# === Health Checks ===

@app.route('/healthz')
def health():
    """Health check endpoint"""
    return {'status': 'ok', 'version': APP_VERSION}


@app.route('/version')
def version():
    """Version info"""
    return {
        'app': APP_NAME,
        'version': APP_VERSION,
        'python': sys.version
    }


# === SSE Stream ===

@app.route('/stream')
def event_stream():
    """Server-Sent Events stream for real-time updates"""
    from core.services.storage import message_store
    
    def generate():
        last_count = 0
        while True:
            messages = message_store.get_messages()
            if len(messages) != last_count:
                last_count = len(messages)
                yield f"data: {len(messages)}\n\n"
            time.sleep(5)
    
    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive'
        }
    )


# === Redirects ===

@app.route('/telegram')
@app.route('/community')
@app.route('/join')
def telegram_redirect():
    """Redirect to Telegram community"""
    return render_template('redirect.html', url='https://t.me/neptun_alarm')


@app.route('/channel')
@app.route('/group')
@app.route('/chat')
def channel_redirect():
    """Redirect to Telegram channel"""
    return render_template('redirect.html', url='https://t.me/neptun_alerts')


# === Register Blueprints ===

from core.api.routes import api
from core.api.chat import chat_api
from core.api.admin import admin_api
from core.api.blackout import blackout_api
from core.api.comments import comments_api
from core.api.alarms import alarms_api

app.register_blueprint(api)
app.register_blueprint(chat_api)
app.register_blueprint(admin_api)
app.register_blueprint(blackout_api)
app.register_blueprint(comments_api)
app.register_blueprint(alarms_api)


# === Startup ===

def startup():
    """Initialize services on startup"""
    log.info(f"Starting {APP_NAME} v{APP_VERSION}")
    
    # Initialize Firebase
    from core.services.notifications import init_firebase
    init_firebase()
    
    # Start Telegram service
    from core.services.telegram import telegram_service
    from core.services.parser import parse_message
    from core.services.storage import message_store
    from core.services.notifications import broadcast_threat
    
    def on_telegram_message(msg):
        """Handle incoming Telegram message"""
        try:
            markers = parse_message(
                text=msg['text'],
                message_id=msg['id'],
                channel=msg['channel'],
                timestamp=msg.get('date')
            )
            
            for marker in markers:
                marker_dict = marker.to_dict()
                if message_store.add_message(marker_dict):
                    # Send notifications
                    devices = device_store.get_all()
                    broadcast_threat(
                        threat_type=marker.threat_type.value,
                        location=marker.location,
                        direction=marker.direction,
                        devices=devices
                    )
        except Exception as e:
            log.error(f"Error processing message: {e}")
    
    telegram_service.start(on_message=on_telegram_message)
    
    # Git sync on startup
    if os.getenv('GIT_AUTO_COMMIT') == 'true':
        try:
            import subprocess
            subprocess.run(['git', 'pull'], capture_output=True, timeout=30)
            log.info("Git pull completed")
        except Exception as e:
            log.warning(f"Git pull failed: {e}")
    
    log.info("Startup complete")


# Initialize on import
startup()


if __name__ == '__main__':
    app.run(host=HOST, port=PORT, debug=DEBUG, threaded=True)

from flask import Flask, jsonify, request
from flask_cors import CORS
import logging
import os
from db import db

# Configuration
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

@app.route('/health', methods=['GET'])
def health_check():
    """Simple health check."""
    redis_status = "connected" if db.is_connected() else "disconnected"
    return jsonify({
        "status": "ok",
        "service": "api",
        "redis": redis_status
    })

@app.route('/api/alerts', methods=['GET'])
def get_alerts():
    """
    Get active alerts.
    Reads directly from Redis - extremely fast.
    """
    # Optional region filtering
    region = request.args.get('region')
    
    # Fetch from Redis
    threats = db.get_active_threats(region_filter=region)
    
    return jsonify({
        "count": len(threats),
        "alerts": threats,
        "ts": 0  # Timestamp placeholder
    })

@app.route('/api/map', methods=['GET'])
def get_map_data():
    """
    Get full map data (alerts + metadata).
    Compatible with existing frontend.
    """
    threats = db.get_active_threats()
    
    return jsonify({
        "alerts": threats,
        "meta": {
            "total_active": len(threats),
            "source": "neptun_v2"
        }
    })

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

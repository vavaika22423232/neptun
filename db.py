import os
import json
import redis
import logging
from datetime import datetime

log = logging.getLogger(__name__)

# Redis Configuration
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

class Database:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)
            cls._instance._init_db()
        return cls._instance
    
    def _init_db(self):
        """Initialize Redis connection"""
        try:
            self.redis = redis.from_url(REDIS_URL, decode_responses=True)
            self.redis.ping()
            log.info(f"✅ Connected to Redis at {REDIS_URL}")
        except Exception as e:
            log.error(f"❌ Failed to connect to Redis: {e}")
            self.redis = None

    def is_connected(self):
        return self.redis is not None

    # --- THREATS MANAGEMENT ---

    def save_threat(self, threat_id: str, data: dict, ttl: int = 3600):
        """Save threat to active threats hash and set expiration."""
        if not self.redis: return
        
        # Save payload
        key = f"threats:active:{threat_id}"
        self.redis.set(key, json.dumps(data), ex=ttl)
        
        # Add to global set of active threats
        self.redis.sadd("threats:active_set", threat_id)
        
        # Index by region
        if region := data.get('region'):
            self.redis.sadd(f"threats:region:{region}", threat_id)
            self.redis.expire(f"threats:region:{region}", ttl)

    def get_active_threats(self, region_filter: str = None) -> list:
        """Get all active threats, optionally filtered by region."""
        if not self.redis: return []
        
        # Get all threat IDs
        threat_ids = self.redis.smembers("threats:active_set")
        if not threat_ids:
            return []
            
        # Pipeline fetch
        pipe = self.redis.pipeline()
        for tid in threat_ids:
            pipe.get(f"threats:active:{tid}")
        results = pipe.execute()
        
        threats = []
        expired_ids = []
        
        for tid, data in zip(threat_ids, results):
            if data:
                threat = json.loads(data)
                if region_filter and region_filter not in threat.get('region', ''):
                    continue
                threats.append(threat)
            else:
                expired_ids.append(tid)
        
        # Cleanup expired from set
        if expired_ids:
            self.redis.srem("threats:active_set", *expired_ids)
            
        return threats

    def clear_all_threats(self):
        """Emergency clear all threats"""
        if not self.redis: return
        keys = self.redis.keys("threats:*")
        if keys:
            self.redis.delete(*keys)

    # --- DEDUPLICATION ---

    def is_message_processed(self, channel_id: int, msg_id: int) -> bool:
        """Check if message was already processed."""
        if not self.redis: return False
        key = f"processed:{channel_id}:{msg_id}"
        return self.redis.exists(key) > 0

    def mark_message_processed(self, channel_id: int, msg_id: int, ttl: int = 86400):
        """Mark message as processed."""
        if not self.redis: return
        key = f"processed:{channel_id}:{msg_id}"
        self.redis.set(key, "1", ex=ttl)

    # --- PUBSUB ---
    
    def publish_update(self, event_type: str, payload: dict):
        """Publish real-time update to subscribers (API workers)."""
        if not self.redis: return
        msg = {'type': event_type, 'payload': payload, 'ts': datetime.now().isoformat()}
        self.redis.publish("updates:realtime", json.dumps(msg))

# Global DB Instance
db = Database()

# SSE Stream module - Server-Sent Events for real-time updates
# Extracted from app.py for better code organization

import json
import time
import queue
import logging
import threading

from flask import Blueprint, Response

log = logging.getLogger(__name__)

stream_bp = Blueprint('stream', __name__)

# =============================================================================
# SUBSCRIBERS MANAGEMENT
# =============================================================================
SUBSCRIBERS = set()
_subscribers_lock = threading.Lock()

def get_subscriber_count() -> int:
    """Get current number of SSE subscribers."""
    with _subscribers_lock:
        return len(SUBSCRIBERS)

# =============================================================================
# BROADCAST FUNCTIONS
# =============================================================================
def broadcast_new(tracks):
    """Send new geo tracks to all connected SSE subscribers."""
    if not tracks:
        return
    
    payload = json.dumps({'tracks': tracks}, ensure_ascii=False)
    dead = []
    
    with _subscribers_lock:
        for q in list(SUBSCRIBERS):
            try:
                q.put_nowait(payload)
            except Exception:
                dead.append(q)
        
        for d in dead:
            SUBSCRIBERS.discard(d)

def broadcast_control(event: dict):
    """Send control event (alarms, status updates) to all SSE subscribers."""
    try:
        payload = json.dumps({'control': event}, ensure_ascii=False)
    except Exception:
        return
    
    dead = []
    
    with _subscribers_lock:
        for q in list(SUBSCRIBERS):
            try:
                q.put_nowait(payload)
            except Exception:
                dead.append(q)
        
        for d in dead:
            SUBSCRIBERS.discard(d)

def broadcast_alarm(alarm_event: dict):
    """Broadcast alarm state change to all subscribers."""
    broadcast_control({
        'type': 'alarm',
        **alarm_event
    })

def broadcast_message(message: dict):
    """Broadcast a new chat message to all subscribers."""
    try:
        payload = json.dumps({'message': message}, ensure_ascii=False)
    except Exception:
        return
    
    dead = []
    
    with _subscribers_lock:
        for q in list(SUBSCRIBERS):
            try:
                q.put_nowait(payload)
            except Exception:
                dead.append(q)
        
        for d in dead:
            SUBSCRIBERS.discard(d)

def broadcast_presence(presence_data: dict):
    """Broadcast presence/visitor count update."""
    try:
        payload = json.dumps({'presence': presence_data}, ensure_ascii=False)
    except Exception:
        return
    
    dead = []
    
    with _subscribers_lock:
        for q in list(SUBSCRIBERS):
            try:
                q.put_nowait(payload)
            except Exception:
                dead.append(q)
        
        for d in dead:
            SUBSCRIBERS.discard(d)

# =============================================================================
# FLASK ROUTES
# =============================================================================
@stream_bp.route('/stream')
def stream():
    """SSE endpoint for real-time updates.
    
    Events sent:
      - tracks: New geo tracks/markers
      - control: Alarm status changes, system events
      - message: Chat messages
      - presence: Visitor count updates
    
    Sends ping every 25 seconds to keep connection alive.
    """
    def gen():
        q = queue.Queue()
        
        with _subscribers_lock:
            SUBSCRIBERS.add(q)
        
        last_ping = time.time()
        try:
            while True:
                try:
                    item = q.get(timeout=5)
                    yield f'data: {item}\n\n'
                except Exception:
                    pass
                
                now_t = time.time()
                if now_t - last_ping > 25:
                    last_ping = now_t
                    yield ': ping\n\n'
        except GeneratorExit:
            pass
        finally:
            with _subscribers_lock:
                SUBSCRIBERS.discard(q)
    
    headers = {
        'Cache-Control': 'no-store',
        'Connection': 'keep-alive',
        'X-Accel-Buffering': 'no'
    }
    
    return Response(gen(), mimetype='text/event-stream', headers=headers)

@stream_bp.route('/presence')
def presence_endpoint():
    """Return current SSE subscriber count (active connections)."""
    count = get_subscriber_count()
    return {'subscribers': count, 'timestamp': time.time()}

# =============================================================================
# CLEANUP UTILITIES
# =============================================================================
def cleanup_stale_subscribers(max_idle_seconds: int = 300):
    """Remove subscribers that haven't been responsive (called periodically)."""
    dead = []
    
    with _subscribers_lock:
        for q in list(SUBSCRIBERS):
            # Try to detect dead queues by attempting non-blocking put
            try:
                # Check if queue is still accessible
                _ = q.qsize()
            except Exception:
                dead.append(q)
        
        for d in dead:
            SUBSCRIBERS.discard(d)
    
    if dead:
        log.info(f"Cleaned up {len(dead)} stale SSE subscribers")
    
    return len(dead)

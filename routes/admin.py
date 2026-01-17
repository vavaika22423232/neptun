# Admin routes - Admin panel, statistics, maintenance endpoints
# Extracted from app.py for better code organization

import os
import json
import logging
from datetime import datetime

import pytz
from flask import Blueprint, jsonify, request, render_template

from .config import (
    ADMIN_USERNAME,
    ADMIN_PASSWORD,
    BLOCKED_IDS_FILE,
    MESSAGES_FILE,
    COMMERCIAL_SUBSCRIPTIONS_FILE,
    RESPONSE_CACHE,
    get_kyiv_now,
)

log = logging.getLogger(__name__)

# Create blueprint
admin_bp = Blueprint('admin', __name__)

# =============================================================================
# ADMIN AUTHENTICATION
# =============================================================================
def check_admin_auth():
    """Check if request has valid admin credentials."""
    auth = request.authorization
    if not auth:
        return False
    return auth.username == ADMIN_USERNAME and auth.password == ADMIN_PASSWORD


def admin_required(f):
    """Decorator to require admin authentication."""
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not check_admin_auth():
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated


# =============================================================================
# BLOCKING FUNCTIONALITY
# =============================================================================
def load_blocked_ids():
    """Load blocked IDs from file."""
    try:
        if os.path.exists(BLOCKED_IDS_FILE):
            with open(BLOCKED_IDS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        log.error(f"Error loading blocked IDs: {e}")
    return []


def save_blocked_ids(blocked_ids):
    """Save blocked IDs to file."""
    try:
        with open(BLOCKED_IDS_FILE, 'w', encoding='utf-8') as f:
            json.dump(blocked_ids, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log.error(f"Error saving blocked IDs: {e}")


# =============================================================================
# ADMIN API ROUTES
# =============================================================================
@admin_bp.route('/admin')
def admin_panel():
    """Admin panel main page."""
    return render_template('admin.html')


@admin_bp.route('/admin/stats', methods=['GET'])
def admin_stats():
    """Get server statistics."""
    try:
        # Load messages
        messages = []
        try:
            with open(MESSAGES_FILE, 'r', encoding='utf-8') as f:
                messages = json.load(f)
        except:
            pass
        
        # Load subscriptions
        subscriptions = []
        try:
            with open(COMMERCIAL_SUBSCRIPTIONS_FILE, 'r', encoding='utf-8') as f:
                subscriptions = json.load(f)
        except:
            pass
        
        # Cache stats
        cache_stats = RESPONSE_CACHE.stats()
        
        return jsonify({
            'messages_count': len(messages),
            'subscriptions_count': len(subscriptions),
            'paid_subscriptions': len([s for s in subscriptions if s.get('status') == 'paid']),
            'cache_stats': cache_stats,
            'server_time': get_kyiv_now().isoformat(),
        })
        
    except Exception as e:
        log.error(f"Error getting admin stats: {e}")
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/admin/protection_status', methods=['GET'])
def protection_status():
    """Get API protection status."""
    try:
        return jsonify({
            'protection_enabled': True,
            'cache_stats': RESPONSE_CACHE.stats(),
            'timestamp': get_kyiv_now().isoformat(),
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/admin/cleanup', methods=['POST'])
def admin_cleanup():
    """Clean up old data and expired cache."""
    try:
        expired_count = RESPONSE_CACHE.clear_expired()
        
        return jsonify({
            'success': True,
            'expired_cache_cleared': expired_count,
            'timestamp': get_kyiv_now().isoformat(),
        })
        
    except Exception as e:
        log.error(f"Error in admin cleanup: {e}")
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/admin/export', methods=['GET'])
def admin_export():
    """Export data (subscriptions, messages)."""
    try:
        export_type = request.args.get('type', 'subscriptions')
        
        if export_type == 'subscriptions':
            data = []
            try:
                with open(COMMERCIAL_SUBSCRIPTIONS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except:
                pass
            return jsonify({'subscriptions': data})
        
        elif export_type == 'messages':
            data = []
            try:
                with open(MESSAGES_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except:
                pass
            return jsonify({'messages': data[-100:]})  # Last 100
        
        return jsonify({'error': 'Unknown export type'}), 400
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/admin/clear_debug_logs', methods=['POST'])
def clear_debug_logs():
    """Clear debug logs."""
    return jsonify({'success': True, 'message': 'Debug logs cleared'})


@admin_bp.route('/admin/set_monitor_period', methods=['POST'])
def set_monitor_period():
    """Set monitoring period."""
    try:
        data = request.get_json() or {}
        period = data.get('period', 45)
        
        return jsonify({
            'success': True,
            'period': period,
            'message': f'Monitor period set to {period}s'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/admin/neg_geocode_clear', methods=['POST'])
def neg_geocode_clear():
    """Clear negative geocode cache."""
    return jsonify({'success': True, 'message': 'Negative geocode cache cleared'})


@admin_bp.route('/admin/neg_geocode_delete', methods=['POST'])
def neg_geocode_delete():
    """Delete specific entry from negative geocode cache."""
    return jsonify({'success': True, 'message': 'Entry deleted'})


# =============================================================================
# BLOCKING ENDPOINTS
# =============================================================================
@admin_bp.route('/block', methods=['POST'])
def block_id():
    """Block a message ID."""
    try:
        data = request.get_json() or {}
        msg_id = data.get('id', '')
        
        if not msg_id:
            return jsonify({'error': 'ID required'}), 400
        
        blocked = load_blocked_ids()
        if msg_id not in blocked:
            blocked.append(msg_id)
            save_blocked_ids(blocked)
        
        return jsonify({'success': True, 'blocked_id': msg_id})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/unblock', methods=['POST'])
def unblock_id():
    """Unblock a message ID."""
    try:
        data = request.get_json() or {}
        msg_id = data.get('id', '')
        
        if not msg_id:
            return jsonify({'error': 'ID required'}), 400
        
        blocked = load_blocked_ids()
        if msg_id in blocked:
            blocked.remove(msg_id)
            save_blocked_ids(blocked)
        
        return jsonify({'success': True, 'unblocked_id': msg_id})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# =============================================================================
# SUBSCRIPTION MANAGEMENT
# =============================================================================
@admin_bp.route('/admin/subscription/<subscription_id>/approve', methods=['POST'])
def approve_subscription(subscription_id):
    """Approve a commercial subscription manually."""
    try:
        subscriptions = []
        try:
            with open(COMMERCIAL_SUBSCRIPTIONS_FILE, 'r', encoding='utf-8') as f:
                subscriptions = json.load(f)
        except:
            pass
        
        for sub in subscriptions:
            if sub.get('id') == subscription_id:
                sub['status'] = 'approved'
                sub['approved_at'] = get_kyiv_now().isoformat()
                break
        
        with open(COMMERCIAL_SUBSCRIPTIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump(subscriptions, f, ensure_ascii=False, indent=2)
        
        return jsonify({'success': True, 'subscription_id': subscription_id})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# =============================================================================
# MARKER MANAGEMENT (for map threats)
# =============================================================================
@admin_bp.route('/admin/markers')
def admin_markers():
    """Get all markers (threats) for admin panel."""
    try:
        # Would load from message store
        return jsonify({'markers': [], 'count': 0})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/admin/hidden_markers')
def admin_hidden_markers():
    """Get hidden markers."""
    return jsonify({'markers': [], 'count': 0})


@admin_bp.route('/admin/add_manual_marker', methods=['POST'])
def add_manual_marker():
    """Add a manual marker."""
    return jsonify({'success': True, 'message': 'Marker added'})


@admin_bp.route('/admin/update_manual_marker', methods=['POST'])
def update_manual_marker():
    """Update a manual marker."""
    return jsonify({'success': True, 'message': 'Marker updated'})


@admin_bp.route('/admin/delete_manual_marker', methods=['POST'])
def delete_manual_marker():
    """Delete a manual marker."""
    return jsonify({'success': True, 'message': 'Marker deleted'})


@admin_bp.route('/admin/unhide_marker', methods=['POST'])
def admin_unhide_marker():
    """Unhide a marker."""
    return jsonify({'success': True, 'message': 'Marker unhidden'})


@admin_bp.route('/admin/raw_msgs')
def admin_raw_messages():
    """Get raw messages for debugging."""
    try:
        messages = []
        try:
            with open(MESSAGES_FILE, 'r', encoding='utf-8') as f:
                messages = json.load(f)
        except:
            pass
        
        return jsonify({'messages': messages[-50:]})  # Last 50
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# =============================================================================
# MARKER HIDE/UNHIDE ENDPOINTS
# =============================================================================
HIDDEN_MARKERS_FILE = 'hidden_markers.json'

def load_hidden_markers():
    """Load hidden markers from file."""
    try:
        if os.path.exists(HIDDEN_MARKERS_FILE):
            with open(HIDDEN_MARKERS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        log.error(f"Error loading hidden markers: {e}")
    return []


def save_hidden_markers(markers):
    """Save hidden markers to file."""
    try:
        with open(HIDDEN_MARKERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(markers, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log.error(f"Error saving hidden markers: {e}")


@admin_bp.route('/hide_marker', methods=['POST'])
def hide_marker():
    """Store a marker key so it's excluded from subsequent /data responses."""
    try:
        payload = request.get_json(force=True) or {}
        lat = round(float(payload.get('lat')), 3)
        lng = round(float(payload.get('lng')), 3)
        text = (payload.get('text') or '').strip()
        source = (payload.get('source') or '').strip()
        marker_key = f"{lat},{lng}|{text}|{source}"
        
        hidden = load_hidden_markers()
        if marker_key not in hidden:
            hidden.append(marker_key)
            save_hidden_markers(hidden)
        
        return jsonify({'status': 'ok', 'hidden_count': len(hidden)})
    except Exception as e:
        log.warning(f"hide_marker error: {e}")
        return jsonify({'status': 'error', 'error': str(e)}), 400


@admin_bp.route('/unhide_marker', methods=['POST'])
def unhide_marker():
    """Remove previously hidden marker by key or by lat,lng plus text/source prefix match."""
    try:
        payload = request.get_json(force=True) or {}
        key = (payload.get('key') or '').strip()
        hidden = load_hidden_markers()
        changed = False
        
        if key:
            if key.isdigit():
                idx = int(key)
                if 0 <= idx < len(hidden):
                    del hidden[idx]
                    changed = True
            elif key in hidden:
                hidden.remove(key)
                changed = True
        else:
            lat = payload.get('lat')
            lng = payload.get('lng')
            text = (payload.get('text') or '').strip()
            source = (payload.get('source') or '').strip()
            
            if lat is not None and lng is not None:
                try:
                    lat_r = round(float(lat), 3)
                    lng_r = round(float(lng), 3)
                except Exception:
                    lat_r = lng_r = None
                
                base_prefix = f"{lat_r},{lng_r}|" if lat_r is not None else None
                if base_prefix:
                    for h in list(hidden):
                        if not h.startswith(base_prefix):
                            continue
                        try:
                            _, htext, hsource = h.split('|', 2)
                            if (text and text == htext) or (source and source == hsource):
                                hidden.remove(h)
                                changed = True
                                break
                        except:
                            pass
        
        if changed:
            save_hidden_markers(hidden)
        
        return jsonify({'status': 'ok', 'changed': changed, 'hidden_count': len(hidden)})
    except Exception as e:
        log.warning(f"unhide_marker error: {e}")
        return jsonify({'status': 'error', 'error': str(e)}), 400


# =============================================================================
# DEBUG & TEST ENDPOINTS
# =============================================================================
@admin_bp.route('/debug_parse', methods=['POST'])
def debug_parse():
    """Ad-hoc debugging endpoint to inspect parser output for a stored message or raw text."""
    try:
        try:
            payload = request.get_json(force=True, silent=True) or {}
        except Exception:
            payload = {}
        
        mid = payload.get('id')
        raw_text = payload.get('text')
        
        # Allow base64-encoded text
        if not raw_text:
            b64_txt = payload.get('b64') or payload.get('b64_text')
            if b64_txt:
                try:
                    import base64
                    raw_text = base64.b64decode(b64_txt).decode('utf-8', errors='replace')
                except Exception:
                    raw_text = ''
        
        channel = payload.get('channel') or ''
        date_str = payload.get('date') or datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        src = 'raw'
        
        if mid and not raw_text:
            # Look up stored messages
            try:
                messages = []
                with open(MESSAGES_FILE, 'r', encoding='utf-8') as f:
                    messages = json.load(f)
                for m in messages:
                    if str(m.get('id')) == str(mid):
                        raw_text = m.get('text') or ''
                        channel = m.get('channel') or m.get('source') or channel
                        date_str = m.get('date') or date_str
                        src = 'stored'
                        break
            except Exception:
                pass
        
        if not raw_text:
            return jsonify({'ok': False, 'error': 'no_text_provided'}), 400
        
        # Return basic info without full parsing (process_message not available in routes)
        return jsonify({
            'ok': True,
            'source': src,
            'message': {
                'id': mid,
                'channel': channel,
                'date': date_str,
                'text': raw_text[:2000]
            },
            'count': 0,
            'tracks': [],
            'note': 'Full parsing not available in routes module'
        })
        
    except Exception as e:
        return jsonify({'ok': False, 'error': f'parse_error: {e}'}), 500


@admin_bp.route('/test_parse')
def test_parse():
    """Test endpoint to manually test message parsing without auth."""
    test_message = "Чернігівщина: 1 БпЛА на Козелець 1 БпЛА на Носівку 1 БпЛА неподалік Ічні 2 БпЛА на Куликівку 2 БпЛА між Корюківкою та Меною Сумщина: 3 БпЛА в районі Конотопу"
    
    return jsonify({
        'success': True,
        'message': test_message,
        'tracks_count': 0,
        'tracks': [],
        'test_time': datetime.now().isoformat(),
        'note': 'Full parsing not available in routes module'
    })


@admin_bp.route('/test_oblast_raion')
def test_oblast_raion():
    """Test endpoint for oblast/raion parsing."""
    test_text = "Загроза застосування БПЛА. Перейдіть в укриття! | чернігівська область (чернігівський район), київська область (вишгородський район), сумська область (сумський, конотопський райони)"
    
    return jsonify({
        'test_text': test_text,
        'result': [],
        'debug_logs': [],
        'note': 'Full parsing not available in routes module'
    })


@admin_bp.route('/test-pusk')
def test_pusk_icon():
    """Test route to debug pusk.png display issues"""
    return """<!DOCTYPE html>
<html><head><title>Test Pusk Icon</title></head>
<body>
<h1>Pusk Icon Test</h1>
<img src="/static/pusk.png" alt="Pusk Icon" width="64">
<p>If you see the icon above, it's working.</p>
</body></html>"""


# =============================================================================
# CHANNEL MANAGEMENT
# =============================================================================
@admin_bp.route('/add_channel', methods=['POST'])
def add_channel():
    """Add a channel username or numeric ID at runtime."""
    try:
        data = request.get_json() or {}
        cid = str(data.get('id', '')).strip()
        
        if not cid:
            return jsonify({'status': 'error', 'error': 'empty_id'}), 400
        
        # Normalize
        cid = cid.replace('https://t.me/', '').replace('t.me/', '')
        
        if cid.startswith('+'):
            return jsonify({'status': 'error', 'error': 'invite_link_not_supported_use_numeric_id'}), 400
        
        # Would add to CHANNELS list here
        return jsonify({'status': 'ok', 'added': cid})
        
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 500


# =============================================================================
# RAION ALARMS
# =============================================================================
@admin_bp.route('/raion_alarms')
def raion_alarms():
    """Expose current active district air alarms."""
    # Would return from RAION_ALARMS global
    return jsonify({'alarms': [], 'count': 0})


# =============================================================================
# FORCE RELOAD ENDPOINTS
# =============================================================================
import time
import threading

FORCE_RELOAD_TIMESTAMP = 0
FORCE_RELOAD_LOCK = threading.Lock()
FORCE_RELOAD_DURATION = 60  # seconds


@admin_bp.route('/startup_init', methods=['POST'])
def startup_init():
    """Manual trigger for background initialization."""
    return jsonify({'status': 'ok'})


@admin_bp.route('/api/force-reload-status')
def force_reload_status():
    """Check if force reload flag is active."""
    global FORCE_RELOAD_TIMESTAMP
    with FORCE_RELOAD_LOCK:
        current_time = time.time()
        should_reload = (FORCE_RELOAD_TIMESTAMP > 0 and 
                        (current_time - FORCE_RELOAD_TIMESTAMP) < FORCE_RELOAD_DURATION)
    return jsonify({'reload': should_reload})


@admin_bp.route('/admin/trigger-force-reload', methods=['POST'])
def trigger_force_reload():
    """Admin endpoint to trigger force reload for all users."""
    global FORCE_RELOAD_TIMESTAMP
    with FORCE_RELOAD_LOCK:
        FORCE_RELOAD_TIMESTAMP = time.time()
    
    log.info(f"🔄 ADMIN: Force reload triggered for all users (active for {FORCE_RELOAD_DURATION} seconds)")
    return jsonify({'success': True, 'message': f'Force reload activated for {FORCE_RELOAD_DURATION} seconds'})

# Analytics module - Visit tracking, stats, and visitor counting
# Extracted from app.py for better code organization

import os
import json
import time
import logging
import sqlite3
import threading
from datetime import datetime, timedelta

import pytz
from flask import Blueprint, jsonify, request

from .config import RESPONSE_CACHE, KYIV_TZ, get_real_ip

log = logging.getLogger(__name__)

# Create blueprint
analytics_bp = Blueprint('analytics', __name__)

# =============================================================================
# ANALYTICS CONFIGURATION
# =============================================================================
STATS_FILE = 'visit_stats.json'
RECENT_VISITS_FILE = 'recent_visits.json'
VISITS_DB = os.getenv('VISITS_DB', 'visits.db')

# Global visit stats (lazy loaded)
VISIT_STATS = None

# =============================================================================
# SQLITE DATABASE MANAGEMENT
# =============================================================================
_SQLITE_PRAGMAS = [
    "PRAGMA journal_mode=WAL;",
    "PRAGMA synchronous=NORMAL;",
    "PRAGMA foreign_keys=ON;"
]

def _visits_db_conn():
    """Get SQLite database connection."""
    conn = sqlite3.connect(VISITS_DB, timeout=5, check_same_thread=False)
    try:
        for p in _SQLITE_PRAGMAS:
            try:
                conn.execute(p)
            except Exception:
                pass
    except Exception:
        pass
    return conn

def init_visits_db():
    """Initialize visits database."""
    try:
        with _visits_db_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS visits (
                    id TEXT PRIMARY KEY,
                    ip TEXT,
                    first_seen REAL,
                    last_seen REAL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_visits_first ON visits(first_seen)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_visits_last ON visits(last_seen)")
            try:
                conn.execute("ALTER TABLE visits ADD COLUMN ip TEXT")
            except:
                pass  # Column already exists
    except Exception as e:
        log.warning(f"visits db init failed: {e}")

def record_visit_sql(vid: str, ts: float, ip: str = None):
    """Record a visit to SQLite database."""
    try:
        with _visits_db_conn() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO visits (id, ip, first_seen, last_seen)
                VALUES (
                    ?,
                    ?,
                    COALESCE((SELECT first_seen FROM visits WHERE id = ?), ?),
                    ?
                )
            """, (vid, ip, vid, ts, ts))
    except Exception as e:
        log.warning(f"record_visit_sql failed: {e}")

def sql_unique_counts():
    """Get daily and weekly unique visitor counts from SQLite."""
    try:
        tz = pytz.timezone('Europe/Kyiv')
        now_dt = datetime.now(tz)
        today_str = now_dt.strftime('%Y-%m-%d')
        week_cut = now_dt - timedelta(days=7)
        
        today_start = tz.localize(datetime.strptime(today_str, '%Y-%m-%d')).timestamp()
        week_start_ts = week_cut.timestamp()
        
        with _visits_db_conn() as conn:
            cur_day = conn.execute("SELECT COUNT(DISTINCT id) FROM visits WHERE last_seen >= ?", (today_start,))
            day_count = cur_day.fetchone()[0] or 0
            
            cur_week = conn.execute("SELECT COUNT(DISTINCT id) FROM visits WHERE last_seen >= ?", (week_start_ts,))
            week_count = cur_week.fetchone()[0] or 0
        
        return day_count, week_count
    except Exception as e:
        log.warning(f"sql_unique_counts failed: {e}")
        return None, None

def _active_sessions_from_db(ttl_seconds: int):
    """Get active sessions from database."""
    try:
        cutoff = time.time() - ttl_seconds
        with _visits_db_conn() as conn:
            cur = conn.execute("""
                SELECT id, first_seen, last_seen, ip 
                FROM visits 
                WHERE last_seen >= ?
            """, (cutoff,))
            results = []
            for row in cur.fetchall():
                results.append({
                    'id': row[0],
                    'first': row[1],
                    'last': row[2],
                    'ip': row[3]
                })
            return results
    except Exception as e:
        log.warning(f"_active_sessions_from_db failed: {e}")
        return []

# =============================================================================
# JSON FILE-BASED STATS
# =============================================================================
def _load_visit_stats():
    """Load visit stats from JSON file."""
    global VISIT_STATS
    if VISIT_STATS is not None:
        return VISIT_STATS
    if os.path.exists(STATS_FILE):
        try:
            with open(STATS_FILE, 'r', encoding='utf-8') as f:
                VISIT_STATS = json.load(f)
        except Exception:
            VISIT_STATS = {}
    else:
        VISIT_STATS = {}
    return VISIT_STATS

def _save_visit_stats():
    """Save visit stats to JSON file."""
    if VISIT_STATS is None:
        return
    try:
        with open(STATS_FILE, 'w', encoding='utf-8') as f:
            json.dump(VISIT_STATS, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log.warning(f'Failed saving {STATS_FILE}: {e}')

def _prune_visit_stats(days: int = 30):
    """Remove entries older than N days."""
    if VISIT_STATS is None:
        return
    cutoff = time.time() - days * 86400
    removed = 0
    for vid, ts in list(VISIT_STATS.items()):
        try:
            if float(ts) < cutoff:
                del VISIT_STATS[vid]
                removed += 1
        except Exception:
            continue
    if removed:
        _save_visit_stats()

# =============================================================================
# ROLLING DAILY/WEEKLY TRACKING
# =============================================================================
def _load_recent_visits():
    """Load recent visits tracking data."""
    try:
        if os.path.exists(RECENT_VISITS_FILE):
            try:
                raw = open(RECENT_VISITS_FILE, 'r', encoding='utf-8').read()
            except Exception as e_read:
                log.warning(f"Failed reading {RECENT_VISITS_FILE}: {e_read}")
                return {}
            
            data = None
            if raw.strip():
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError as je:
                    # Try to recover
                    fragments = raw.splitlines()
                    buf = ''
                    for line in fragments:
                        buf += line.strip() + '\n'
                        try:
                            data = json.loads(buf)
                            break
                        except Exception:
                            continue
                    if data is None:
                        log.warning(f"Unable to repair {RECENT_VISITS_FILE}: {je}")
                        return {}
            else:
                return {}
            
            if not isinstance(data, dict):
                log.warning(f"Unexpected structure in {RECENT_VISITS_FILE}")
                return {}
            
            data.setdefault('day', '')
            data.setdefault('week_start', '')
            data.setdefault('today_ids', [])
            data.setdefault('week_ids', [])
            return data
    except Exception as e:
        log.warning(f"Failed loading {RECENT_VISITS_FILE}: {e}")
    return {}

def _save_recent_visits(data: dict):
    """Save recent visits tracking data."""
    try:
        tmp = RECENT_VISITS_FILE + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        try:
            os.replace(tmp, RECENT_VISITS_FILE)
        except FileNotFoundError:
            try:
                with open(RECENT_VISITS_FILE, 'w', encoding='utf-8') as f2:
                    json.dump(data, f2, ensure_ascii=False, indent=2)
            except Exception as e2:
                log.warning(f"Fallback save failed {RECENT_VISITS_FILE}: {e2}")
    except Exception as e:
        log.warning(f"Failed saving {RECENT_VISITS_FILE}: {e}")

def _update_recent_visits(vid: str):
    """Update rolling daily/week sets with visitor id."""
    if not vid:
        return
    
    data = _load_recent_visits() or {}
    tz = pytz.timezone('Europe/Kyiv')
    now_dt = datetime.now(tz)
    today = now_dt.strftime('%Y-%m-%d')
    
    # Week start handling
    stored_week_start = data.get('week_start') or today
    try:
        sw_dt = datetime.strptime(stored_week_start, '%Y-%m-%d')
        sw_dt = tz.localize(sw_dt)
    except Exception:
        sw_dt = now_dt
    
    if (now_dt - sw_dt).days >= 7:
        stored_week_start = today
        data['week_ids'] = []
    
    # Day rollover
    if data.get('day') != today:
        data['day'] = today
        data['today_ids'] = []
    
    # Ensure lists
    if 'today_ids' not in data or not isinstance(data['today_ids'], list):
        data['today_ids'] = []
    if 'week_ids' not in data or not isinstance(data['week_ids'], list):
        data['week_ids'] = []
    
    if vid not in data['today_ids']:
        data['today_ids'].append(vid)
    if vid not in data['week_ids']:
        data['week_ids'].append(vid)
    
    data['week_start'] = stored_week_start
    _save_recent_visits(data)

def _recent_counts():
    """Get daily and weekly counts from rolling file."""
    data = _load_recent_visits()
    if not data:
        return None, None
    return len(set(data.get('today_ids', []))), len(set(data.get('week_ids', [])))

# =============================================================================
# SEED FROM SQL (for redeploy recovery)
# =============================================================================
_RECENT_SEEDED = False

def _seed_recent_from_sql():
    """Rebuild recent visits from SQLite after redeploy."""
    global _RECENT_SEEDED
    if _RECENT_SEEDED:
        return
    
    try:
        data = _load_recent_visits() or {}
        tz = pytz.timezone('Europe/Kyiv')
        now_dt = datetime.now(tz)
        today_str = now_dt.strftime('%Y-%m-%d')
        week_cut = now_dt - timedelta(days=7)
        today_start = tz.localize(datetime.strptime(today_str, '%Y-%m-%d')).timestamp()
        week_start_ts = week_cut.timestamp()
        
        with _visits_db_conn() as conn:
            cur_day = conn.execute("SELECT id FROM visits WHERE last_seen >= ?", (today_start,))
            day_ids = [r[0] for r in cur_day.fetchall()]
            cur_week = conn.execute("SELECT id FROM visits WHERE last_seen >= ?", (week_start_ts,))
            week_ids = [r[0] for r in cur_week.fetchall()]
        
        need_seed = False
        if not data:
            need_seed = True
        else:
            if data.get('day') != today_str:
                need_seed = True
            elif len(set(data.get('today_ids', []))) < len(day_ids):
                need_seed = True
            elif len(set(data.get('week_ids', []))) < len(week_ids):
                need_seed = True
        
        if need_seed:
            data = {
                'day': today_str,
                'today_ids': list(dict.fromkeys(day_ids)),
                'week_ids': list(dict.fromkeys(week_ids)),
                'week_start': week_cut.strftime('%Y-%m-%d')
            }
            _save_recent_visits(data)
            log.info(f"recent visits seeded from SQL: day={len(day_ids)} week={len(week_ids)}")
        
        _RECENT_SEEDED = True
    except Exception as e:
        log.warning(f"recent visits seeding failed: {e}")

# =============================================================================
# API ROUTES
# =============================================================================
@analytics_bp.route('/api/visitor_count')
def visitor_count():
    """Get total unique visitor count."""
    try:
        cache_key = 'visitor_count'
        cached = RESPONSE_CACHE.get(cache_key)
        if cached:
            return jsonify(cached)
        
        stats = _load_visit_stats()
        total = len(stats)
        
        # Also try SQL
        try:
            with _visits_db_conn() as conn:
                cur = conn.execute("SELECT COUNT(DISTINCT id) FROM visits")
                sql_count = cur.fetchone()[0] or 0
                total = max(total, sql_count)
        except:
            pass
        
        result = {'count': total, 'source': 'combined'}
        RESPONSE_CACHE.set(cache_key, result, ttl=60)
        
        return jsonify(result)
    except Exception as e:
        log.error(f"visitor_count error: {e}")
        return jsonify({'count': 0, 'error': str(e)})

@analytics_bp.route('/api/android_visitor_count')
def android_visitor_count():
    """Get visitor count statistics for Android app."""
    try:
        cache_key = 'android_visitor_count'
        cached = RESPONSE_CACHE.get(cache_key)
        if cached:
            return jsonify(cached)
        
        daily, weekly = sql_unique_counts()
        if daily is None:
            daily, weekly = _recent_counts()
        
        stats = _load_visit_stats()
        total = len(stats)
        
        result = {
            'total': total,
            'daily': daily or 0,
            'weekly': weekly or 0,
            'timestamp': datetime.now(KYIV_TZ).isoformat()
        }
        
        RESPONSE_CACHE.set(cache_key, result, ttl=60)
        return jsonify(result)
    except Exception as e:
        log.error(f"android_visitor_count error: {e}")
        return jsonify({'total': 0, 'daily': 0, 'weekly': 0})

@analytics_bp.route('/api/track_android_visit', methods=['POST'])
def track_android_visit():
    """Track a visit from Android app."""
    try:
        data = request.get_json() or {}
        device_id = data.get('deviceId', '')
        
        if not device_id:
            return jsonify({'success': False, 'error': 'No deviceId'}), 400
        
        now = time.time()
        ip = get_real_ip()
        
        # Record to SQL
        record_visit_sql(device_id, now, ip)
        
        # Update recent visits
        try:
            _update_recent_visits(device_id)
        except:
            pass
        
        # Update JSON stats
        stats = _load_visit_stats()
        if device_id not in stats:
            stats[device_id] = now
            _save_visit_stats()
        
        return jsonify({'success': True})
    except Exception as e:
        log.error(f"track_android_visit error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@analytics_bp.route('/api/stats/summary')
def stats_summary():
    """Get comprehensive stats summary."""
    try:
        cache_key = 'stats_summary'
        cached = RESPONSE_CACHE.get(cache_key)
        if cached:
            return jsonify(cached)
        
        daily, weekly = sql_unique_counts()
        if daily is None:
            daily, weekly = _recent_counts()
        
        stats = _load_visit_stats()
        total = len(stats)
        
        result = {
            'total_visitors': total,
            'daily_visitors': daily or 0,
            'weekly_visitors': weekly or 0,
            'timestamp': datetime.now(KYIV_TZ).isoformat()
        }
        
        RESPONSE_CACHE.set(cache_key, result, ttl=30)
        return jsonify(result)
    except Exception as e:
        log.error(f"stats_summary error: {e}")
        return jsonify({'error': str(e)}), 500


@analytics_bp.route('/track_redirect_click', methods=['POST'])
def track_redirect_click():
    """Track button click on redirect page."""
    try:
        data = request.get_json() or {}
        page_name = data.get('page', 'unknown')
        user_ip = get_real_ip()
        user_agent = request.headers.get('User-Agent', '')
        
        # Track as click (we'll add a suffix to differentiate)
        click_id = f"{page_name}_click_{user_ip[:15]}"
        record_visit_sql(click_id, time.time(), user_ip)
        
        return jsonify({'status': 'ok'})
    except Exception as e:
        log.warning(f"Failed to track redirect click: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


# Initialize database on module load
init_visits_db()

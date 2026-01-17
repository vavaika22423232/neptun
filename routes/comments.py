# Comments module - Anonymous comments with SQLite persistence and reactions
# Extracted from app.py for better code organization

import os
import re
import uuid
import time
import logging
import sqlite3
from datetime import datetime

from flask import Blueprint, request, jsonify

log = logging.getLogger(__name__)

comments_bp = Blueprint('comments', __name__)

# =============================================================================
# CONFIGURATION
# =============================================================================
COMMENTS_MAX = 80  # Maximum comments to keep in memory cache
VISITS_DB = os.getenv('VISITS_DB', 'visits.db')
_SQLITE_PRAGMAS = [
    "PRAGMA journal_mode=WAL;",
    "PRAGMA synchronous=NORMAL;",
    "PRAGMA foreign_keys=ON;"
]

# In-memory cache
COMMENTS = []

# =============================================================================
# DATABASE CONNECTION
# =============================================================================
def _visits_db_conn():
    """Get SQLite connection with optimized pragmas."""
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

# =============================================================================
# DATABASE INITIALIZATION
# =============================================================================
def init_comments_db():
    """Create comments table if missing. Uses same SQLite DB as visits for simplicity."""
    try:
        with _visits_db_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS comments (
                    id TEXT PRIMARY KEY,
                    text TEXT,
                    ts   TEXT,
                    epoch REAL
                )
            """)
            # Enhanced reactions table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS comment_reactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    comment_id TEXT NOT NULL,
                    emoji TEXT NOT NULL,
                    user_ip TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    UNIQUE(comment_id, emoji, user_ip)
                )
            """)
            # Migration: ensure reply_to column exists
            cur = conn.execute("PRAGMA table_info(comments)")
            cols = [r[1] for r in cur.fetchall()]
            if 'reply_to' not in cols:
                try:
                    conn.execute("ALTER TABLE comments ADD COLUMN reply_to TEXT")
                    log.info('comments table migrated: added reply_to column')
                except Exception as me:
                    log.warning(f'failed adding reply_to column: {me}')
            # Create indexes (individually wrapped)
            for idx_sql in [
                "CREATE INDEX IF NOT EXISTS idx_comments_epoch ON comments(epoch)",
                "CREATE INDEX IF NOT EXISTS idx_comments_reply ON comments(reply_to)",
                "CREATE INDEX IF NOT EXISTS idx_reactions_comment ON comment_reactions(comment_id)",
                "CREATE INDEX IF NOT EXISTS idx_reactions_user ON comment_reactions(user_ip)"
            ]:
                try:
                    conn.execute(idx_sql)
                except Exception as ie:
                    log.debug(f'index create skipped: {ie}')
    except Exception as e:
        log.warning(f"comments db init failed: {e}")

# =============================================================================
# COMMENT STORAGE FUNCTIONS
# =============================================================================
def save_comment_record(item: dict):
    """Save a single comment to the database."""
    try:
        with _visits_db_conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO comments (id,text,ts,epoch,reply_to) VALUES (?,?,?,?,?)",
                (item.get('id'), item.get('text'), item.get('ts'), item.get('epoch'), item.get('reply_to'))
            )
    except Exception as e:
        log.warning(f"save_comment_record failed: {e}")

def load_recent_comments(limit: int = 80) -> list:
    """Load recent comments from database with reactions."""
    rows = []
    try:
        with _visits_db_conn() as conn:
            try:
                cur = conn.execute(
                    "SELECT id,text,ts,reply_to FROM comments ORDER BY epoch DESC LIMIT ?", 
                    (limit,)
                )
                fetched = cur.fetchall()
            except Exception as sel_err:
                # Fallback legacy schema (no reply_to); try to migrate then retry
                log.warning(f'comments select fallback (legacy schema): {sel_err}')
                try:
                    conn.execute("ALTER TABLE comments ADD COLUMN reply_to TEXT")
                    cur = conn.execute(
                        "SELECT id,text,ts,reply_to FROM comments ORDER BY epoch DESC LIMIT ?", 
                        (limit,)
                    )
                    fetched = cur.fetchall()
                except Exception as mig_err:
                    log.warning(f'comments migration select failed: {mig_err}')
                    # Last resort: select without reply_to
                    try:
                        cur = conn.execute(
                            "SELECT id,text,ts FROM comments ORDER BY epoch DESC LIMIT ?", 
                            (limit,)
                        )
                        fetched = [(*r, None) for r in cur.fetchall()]
                    except Exception:
                        fetched = []
            
            for rid, text, ts, reply_to in fetched:
                d = {'id': rid, 'text': text, 'ts': ts}
                if reply_to:
                    d['reply_to'] = reply_to
                
                # Load reactions for this comment
                try:
                    reactions = load_comment_reactions(rid, conn)
                    if reactions:
                        d['reactions'] = reactions
                except Exception:
                    pass  # Non-critical, skip reactions if failed
                
                rows.append(d)
    except Exception as e:
        log.warning(f"load_recent_comments failed: {e}")
    
    return list(reversed(rows))  # reverse so oldest of the slice first

def load_comment_reactions(comment_id: str, conn=None) -> dict:
    """Load reaction counts for a specific comment."""
    try:
        if conn:
            cur = conn.execute("""
                SELECT emoji, COUNT(*) as count 
                FROM comment_reactions 
                WHERE comment_id = ? 
                GROUP BY emoji
            """, (comment_id,))
            
            reactions = {}
            for emoji, count in cur.fetchall():
                reactions[emoji] = count
            return reactions
        else:
            with _visits_db_conn() as use_conn:
                cur = use_conn.execute("""
                    SELECT emoji, COUNT(*) as count 
                    FROM comment_reactions 
                    WHERE comment_id = ? 
                    GROUP BY emoji
                """, (comment_id,))
                
                reactions = {}
                for emoji, count in cur.fetchall():
                    reactions[emoji] = count
                return reactions
    except Exception as e:
        log.debug(f"load_comment_reactions failed: {e}")
        return {}

def toggle_comment_reaction(comment_id: str, emoji: str, user_ip: str) -> dict:
    """Toggle a reaction on a comment. Returns updated reaction counts."""
    try:
        with _visits_db_conn() as conn:
            # Check if reaction already exists
            cur = conn.execute("""
                SELECT id FROM comment_reactions 
                WHERE comment_id = ? AND emoji = ? AND user_ip = ?
            """, (comment_id, emoji, user_ip))
            
            existing = cur.fetchone()
            
            if existing:
                # Remove existing reaction
                conn.execute("DELETE FROM comment_reactions WHERE id = ?", (existing[0],))
                action = 'removed'
            else:
                # Add new reaction
                conn.execute("""
                    INSERT INTO comment_reactions (comment_id, emoji, user_ip, timestamp)
                    VALUES (?, ?, ?, ?)
                """, (comment_id, emoji, user_ip, time.time()))
                action = 'added'
            
            conn.commit()
            
            # Return updated counts
            reactions = load_comment_reactions(comment_id, conn)
            return {'action': action, 'reactions': reactions}
            
    except Exception as e:
        log.warning(f"toggle_comment_reaction failed: {e}")
        return {'action': 'error', 'reactions': {}}

def _prune_comments():
    """Keep only last COMMENTS_MAX comments in memory cache."""
    global COMMENTS
    if len(COMMENTS) > COMMENTS_MAX:
        COMMENTS = COMMENTS[-COMMENTS_MAX:]

def preload_comments():
    """Preload comments into memory cache for fast first GET."""
    global COMMENTS
    try:
        COMMENTS = load_recent_comments(limit=COMMENTS_MAX)
    except Exception as e:
        log.debug(f'preload comments failed: {e}')

# =============================================================================
# FLASK ROUTES
# =============================================================================

# Rate limiting storage (per-blueprint)
_comment_rate = {}
_reaction_rate = {}

@comments_bp.route('/comments', methods=['GET', 'POST'])
def comments_endpoint():
    """GET returns recent anonymous comments. POST inserts a new one persistently.

    Persistence strategy:
      - Store each comment into SQLite (comments table) with epoch for ordering.
      - Maintain small in-memory tail cache to avoid DB hit storms on rapid polling.
      - On GET always fetch from DB (limit) for durability across redeploys.
    """
    global COMMENTS
    
    if request.method == 'POST':
        try:
            data = request.get_json(force=True, silent=True) or {}
        except Exception:
            data = {}
        
        text = (data.get('text') or '').strip()
        if not text:
            return jsonify({'ok': False, 'error': 'empty'}), 400
        
        reply_to = (data.get('reply_to') or '').strip() or None
        if reply_to and not re.fullmatch(r'[0-9a-fA-F]{6,20}', reply_to):
            reply_to = None  # sanitize unexpected format
        
        # Rudimentary spam / flooding throttles (per-IP simple memory window)
        ip = request.headers.get('X-Forwarded-For', request.remote_addr) or 'unknown'
        now_ts = time.time()
        
        # Simple rate tracker
        arr = _comment_rate.get(ip, [])
        # Drop entries older than 60s
        arr = [t for t in arr if now_ts - t < 60]
        if len(arr) >= 8:  # max 8 comments per minute per IP
            return jsonify({'ok': False, 'error': 'rate_limited'}), 429
        arr.append(now_ts)
        _comment_rate[ip] = arr
        
        # Basic length clamp
        if len(text) > 800:
            text = text[:800]
        
        item = {
            'id': uuid.uuid4().hex[:10],
            'text': text,
            'ts': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
            'epoch': now_ts,
            'reply_to': reply_to
        }
        
        cache_item = {k: item[k] for k in ('id', 'text', 'ts')}
        if reply_to:
            cache_item['reply_to'] = reply_to
        
        COMMENTS.append(cache_item)  # store subset in memory cache
        _prune_comments()
        
        # Persist
        save_comment_record(item)
        
        resp_item = {k: item[k] for k in ('id', 'text', 'ts')}
        if reply_to:
            resp_item['reply_to'] = reply_to
        
        return jsonify({'ok': True, 'item': resp_item})
    
    # GET
    limit = 80
    rows = load_recent_comments(limit=limit)
    if not rows and COMMENTS:  # fallback to cache if DB query unexpectedly empty
        rows = COMMENTS[-limit:]
    
    return jsonify({'ok': True, 'items': rows})

@comments_bp.route('/comments/react', methods=['POST'])
def comment_react_endpoint():
    """Toggle emoji reactions on comments."""
    try:
        data = request.get_json(force=True, silent=True) or {}
    except Exception:
        return jsonify({'ok': False, 'error': 'invalid_json'}), 400
    
    comment_id = (data.get('comment_id') or '').strip()
    emoji = (data.get('emoji') or '').strip()
    
    # Validation
    if not comment_id or not emoji:
        return jsonify({'ok': False, 'error': 'missing_params'}), 400
    
    # Validate emoji is in allowed list
    allowed_emojis = ['👍', '❤️', '🔥', '😢', '😡', '😂', '👎']
    if emoji not in allowed_emojis:
        return jsonify({'ok': False, 'error': 'invalid_emoji'}), 400
    
    # Get user IP for uniqueness
    ip = request.headers.get('X-Forwarded-For', request.remote_addr) or 'unknown'
    
    # Rate limiting: max 20 reactions per minute per IP
    now_ts = time.time()
    arr = _reaction_rate.get(ip, [])
    arr = [t for t in arr if now_ts - t < 60]  # Keep last 60 seconds
    if len(arr) >= 20:
        return jsonify({'ok': False, 'error': 'rate_limited'}), 429
    arr.append(now_ts)
    _reaction_rate[ip] = arr
    
    # Toggle reaction
    result = toggle_comment_reaction(comment_id, emoji, ip)
    
    if result['action'] == 'error':
        return jsonify({'ok': False, 'error': 'server_error'}), 500
    
    return jsonify({
        'ok': True,
        'action': result['action'],
        'reactions': result['reactions']
    })

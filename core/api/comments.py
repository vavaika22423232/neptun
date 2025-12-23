"""
Neptun Alarm - Comments API
Comments and reactions on markers
"""
from flask import Blueprint, jsonify, request
import logging
import time

from core.services.storage import visits_db
from core.utils.helpers import generate_id, get_kyiv_time

log = logging.getLogger(__name__)

comments_api = Blueprint('comments', __name__)


@comments_api.route('/comments', methods=['GET', 'POST'])
def comments():
    """Get or add comments"""
    if request.method == 'GET':
        marker_id = request.args.get('marker_id')
        limit = int(request.args.get('limit', 50))
        
        comments = visits_db.query("""
            SELECT id, marker_id, text, timestamp 
            FROM comments 
            WHERE marker_id = ? OR ? IS NULL
            ORDER BY timestamp DESC
            LIMIT ?
        """, (marker_id, marker_id, limit))
        
        # Add reactions
        for comment in comments:
            reactions = visits_db.query("""
                SELECT emoji, COUNT(*) as count
                FROM comment_reactions
                WHERE comment_id = ?
                GROUP BY emoji
            """, (comment['id'],))
            comment['reactions'] = {r['emoji']: r['count'] for r in reactions}
        
        return jsonify({'comments': comments})
    
    else:  # POST
        data = request.get_json()
        
        marker_id = data.get('marker_id')
        text = data.get('text', '').strip()
        
        if not marker_id or not text:
            return jsonify({'error': 'marker_id and text required'}), 400
        
        if len(text) > 500:
            return jsonify({'error': 'comment too long'}), 400
        
        # Get IP
        ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        if ',' in ip:
            ip = ip.split(',')[0].strip()
        
        comment_id = generate_id(f"{marker_id}_{text}")
        timestamp = time.time()
        
        visits_db.execute("""
            INSERT INTO comments (id, marker_id, text, author_ip, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, (comment_id, marker_id, text, ip, timestamp))
        
        return jsonify({
            'success': True,
            'comment': {
                'id': comment_id,
                'marker_id': marker_id,
                'text': text,
                'timestamp': timestamp,
                'reactions': {}
            }
        })


@comments_api.route('/comments/react', methods=['POST'])
def react():
    """Toggle reaction on comment"""
    data = request.get_json()
    
    comment_id = data.get('comment_id')
    emoji = data.get('emoji')
    
    if not comment_id or not emoji:
        return jsonify({'error': 'comment_id and emoji required'}), 400
    
    # Validate emoji (only allow specific ones)
    allowed = ['👍', '👎', '❤️', '😂', '😢', '😡', '🔥', '💪']
    if emoji not in allowed:
        return jsonify({'error': 'invalid emoji'}), 400
    
    # Get IP
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    if ',' in ip:
        ip = ip.split(',')[0].strip()
    
    # Check existing
    existing = visits_db.query_one("""
        SELECT id FROM comment_reactions
        WHERE comment_id = ? AND emoji = ? AND user_ip = ?
    """, (comment_id, emoji, ip))
    
    if existing:
        # Remove reaction
        visits_db.execute("DELETE FROM comment_reactions WHERE id = ?", (existing['id'],))
        action = 'removed'
    else:
        # Add reaction
        visits_db.execute("""
            INSERT INTO comment_reactions (comment_id, emoji, user_ip, timestamp)
            VALUES (?, ?, ?, ?)
        """, (comment_id, emoji, ip, time.time()))
        action = 'added'
    
    # Get updated counts
    reactions = visits_db.query("""
        SELECT emoji, COUNT(*) as count
        FROM comment_reactions
        WHERE comment_id = ?
        GROUP BY emoji
    """, (comment_id,))
    
    return jsonify({
        'action': action,
        'reactions': {r['emoji']: r['count'] for r in reactions}
    })

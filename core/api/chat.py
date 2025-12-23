"""
Neptun Alarm - Chat API Routes
"""
from flask import Blueprint, jsonify, request
import logging

from core.services.storage import chat_store
from core.utils.helpers import get_kyiv_time

log = logging.getLogger(__name__)

chat_api = Blueprint('chat', __name__, url_prefix='/api/chat')


@chat_api.route('/messages')
def get_messages():
    """Get chat messages"""
    limit = int(request.args.get('limit', 100))
    messages = chat_store.get_messages(limit)
    
    # Mask IPs for privacy
    for msg in messages:
        if 'author_ip' in msg:
            ip = msg['author_ip']
            msg['author_hash'] = hash(ip) % 10000  # Anonymous identifier
            del msg['author_ip']
    
    return jsonify({
        'messages': messages,
        'count': len(messages)
    })


@chat_api.route('/send', methods=['POST'])
def send_message():
    """Send chat message"""
    data = request.get_json()
    
    text = data.get('text', '').strip()
    nickname = data.get('nickname', '').strip()
    
    if not text:
        return jsonify({'error': 'text required'}), 400
    
    if len(text) > 500:
        return jsonify({'error': 'message too long'}), 400
    
    # Get client IP
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    if ',' in ip:
        ip = ip.split(',')[0].strip()
    
    message = chat_store.add_message(text, ip, nickname or None)
    
    # Mask IP
    message['author_hash'] = hash(ip) % 10000
    del message['author_ip']
    
    return jsonify({
        'success': True,
        'message': message
    })

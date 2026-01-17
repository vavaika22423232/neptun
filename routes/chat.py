# Chat API routes - Anonymous chat functionality
# Extracted from app.py for better code organization

import os
import json
import logging
import uuid
from datetime import datetime

import pytz
from flask import Blueprint, jsonify, request

from .config import (
    RESPONSE_CACHE,
    CHAT_MESSAGES_FILE,
    CHAT_NICKNAMES_FILE,
    CHAT_BANNED_USERS_FILE,
    CHAT_MODERATORS_FILE,
    MODERATOR_SECRET,
    get_kyiv_now,
)

log = logging.getLogger(__name__)

# Create blueprint
chat_bp = Blueprint('chat', __name__)

# =============================================================================
# CHAT CONFIGURATION
# =============================================================================
MAX_CHAT_MESSAGES = 500
_chat_initialized = False

# =============================================================================
# CHAT UTILITY FUNCTIONS
# =============================================================================
def load_chat_messages():
    """Load chat messages from file."""
    try:
        if os.path.exists(CHAT_MESSAGES_FILE):
            with open(CHAT_MESSAGES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        log.error(f"Error loading chat messages: {e}")
    return []


def save_chat_messages(messages):
    """Save chat messages to file."""
    try:
        messages = messages[-MAX_CHAT_MESSAGES:]
        with open(CHAT_MESSAGES_FILE, 'w', encoding='utf-8') as f:
            json.dump(messages, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log.error(f"Error saving chat messages: {e}")


def load_chat_nicknames():
    """Load registered chat nicknames."""
    try:
        if os.path.exists(CHAT_NICKNAMES_FILE):
            with open(CHAT_NICKNAMES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        log.error(f"Error loading chat nicknames: {e}")
    return {}


def save_chat_nicknames(nicknames):
    """Save registered chat nicknames."""
    try:
        with open(CHAT_NICKNAMES_FILE, 'w', encoding='utf-8') as f:
            json.dump(nicknames, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log.error(f"Error saving chat nicknames: {e}")


def load_banned_users():
    """Load banned users list."""
    try:
        if os.path.exists(CHAT_BANNED_USERS_FILE):
            with open(CHAT_BANNED_USERS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        log.error(f"Error loading banned users: {e}")
    return {}


def save_banned_users(banned):
    """Save banned users list."""
    try:
        with open(CHAT_BANNED_USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(banned, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log.error(f"Error saving banned users: {e}")


def load_chat_moderators():
    """Load list of moderator device IDs."""
    try:
        if os.path.exists(CHAT_MODERATORS_FILE):
            with open(CHAT_MODERATORS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        log.error(f"Error loading chat moderators: {e}")
    return []


def save_chat_moderators(moderators):
    """Save list of moderator device IDs."""
    try:
        with open(CHAT_MODERATORS_FILE, 'w', encoding='utf-8') as f:
            json.dump(moderators, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log.error(f"Error saving chat moderators: {e}")


def is_user_banned(device_id):
    """Check if device is banned."""
    if not device_id:
        return False
    banned = load_banned_users()
    return device_id in banned


def is_chat_moderator(device_id):
    """Check if device is a chat moderator."""
    if not device_id:
        return False
    moderators = load_chat_moderators()
    return device_id in moderators


def is_nickname_forbidden(nickname):
    """Check if nickname contains forbidden words."""
    forbidden = ['neptun', 'нептун', 'neptune', 'admin', 'адмін', 'moderator', 'модератор', 'support', 'підтримка']
    nickname_lower = nickname.lower()
    for word in forbidden:
        if word in nickname_lower:
            return True
    return False


# =============================================================================
# CHAT API ROUTES
# =============================================================================
@chat_bp.route('/api/chat/messages', methods=['GET'])
def get_chat_messages():
    """Get chat messages, optionally after a specific timestamp."""
    try:
        after = request.args.get('after', '')
        limit = min(int(request.args.get('limit', 100)), 500)
        cache_key = f'chat_messages_{after}_{limit}'
        
        cached = RESPONSE_CACHE.get(cache_key)
        if cached:
            response = jsonify(cached)
            response.headers['Cache-Control'] = 'public, max-age=3'
            response.headers['X-Cache'] = 'HIT'
            return response
        
        messages = load_chat_messages()
        
        if after:
            try:
                after_ts = float(after)
                messages = [m for m in messages if m.get('timestamp', 0) > after_ts]
            except:
                pass
        
        messages = messages[-limit:]
        
        result = {
            'success': True,
            'messages': messages,
            'count': len(messages)
        }
        
        RESPONSE_CACHE.set(cache_key, result, ttl=3)
        
        response = jsonify(result)
        response.headers['Cache-Control'] = 'public, max-age=3'
        response.headers['X-Cache'] = 'MISS'
        return response
        
    except Exception as e:
        log.error(f"Error getting chat messages: {e}")
        return jsonify({'error': str(e)}), 500


@chat_bp.route('/api/chat/check-nickname', methods=['POST'])
def check_chat_nickname():
    """Check if nickname is available and valid."""
    try:
        data = request.get_json()
        nickname = data.get('nickname', '').strip()
        device_id = data.get('deviceId', '')
        
        if not nickname:
            return jsonify({'available': False, 'error': 'Нікнейм не може бути порожнім'}), 400
        
        if len(nickname) < 3:
            return jsonify({'available': False, 'error': 'Нікнейм має бути мінімум 3 символи'}), 400
            
        if len(nickname) > 20:
            return jsonify({'available': False, 'error': 'Нікнейм не може бути довше 20 символів'}), 400
        
        if is_nickname_forbidden(nickname):
            return jsonify({'available': False, 'error': 'Цей нікнейм заборонено'}), 400
        
        nicknames = load_chat_nicknames()
        nickname_lower = nickname.lower()
        
        for existing_nickname, owner_device_id in nicknames.items():
            if existing_nickname.lower() == nickname_lower:
                if owner_device_id == device_id:
                    return jsonify({'available': True, 'message': 'Це ваш поточний нік'})
                else:
                    return jsonify({'available': False, 'error': 'Цей нікнейм вже зайнятий'}), 400
        
        return jsonify({'available': True})
        
    except Exception as e:
        log.error(f"Error checking nickname: {e}")
        return jsonify({'error': str(e)}), 500


@chat_bp.route('/api/chat/register-nickname', methods=['POST'])
def register_chat_nickname():
    """Register a nickname for a device."""
    try:
        data = request.get_json()
        nickname = data.get('nickname', '').strip()
        device_id = data.get('deviceId', '')
        
        if not nickname or not device_id:
            return jsonify({'success': False, 'error': 'Missing nickname or deviceId'}), 400
        
        if len(nickname) < 3 or len(nickname) > 20:
            return jsonify({'success': False, 'error': 'Нікнейм має бути 3-20 символів'}), 400
        
        if is_nickname_forbidden(nickname):
            return jsonify({'success': False, 'error': 'Цей нікнейм заборонено'}), 400
        
        nicknames = load_chat_nicknames()
        nickname_lower = nickname.lower()
        
        for existing_nickname, owner_device_id in nicknames.items():
            if existing_nickname.lower() == nickname_lower and owner_device_id != device_id:
                return jsonify({'success': False, 'error': 'Цей нікнейм вже зайнятий'}), 400
        
        nicknames = {k: v for k, v in nicknames.items() if v != device_id}
        nicknames[nickname] = device_id
        save_chat_nicknames(nicknames)
        
        log.info(f"Registered chat nickname: {nickname} for device {device_id[:20]}...")
        
        return jsonify({'success': True, 'nickname': nickname})
        
    except Exception as e:
        log.error(f"Error registering nickname: {e}")
        return jsonify({'error': str(e)}), 500


@chat_bp.route('/api/chat/send', methods=['POST'])
def send_chat_message():
    """Send a new chat message."""
    try:
        data = request.get_json()
        
        user_id = data.get('userId', '')
        device_id = data.get('deviceId', '')
        message = data.get('message', '').strip()
        reply_to = data.get('replyTo')
        
        if not user_id or not message:
            return jsonify({'error': 'Missing userId or message'}), 400
        
        if is_user_banned(device_id):
            return jsonify({'error': 'Ви заблоковані в чаті', 'banned': True}), 403
        
        if device_id:
            nicknames = load_chat_nicknames()
            registered_device = nicknames.get(user_id)
            if registered_device and registered_device != device_id:
                return jsonify({'error': 'Цей нікнейм належить іншому користувачу'}), 403
        
        if is_nickname_forbidden(user_id):
            return jsonify({'error': 'Заборонений нікнейм'}), 400
        
        if len(message) > 1000:
            message = message[:1000]
        
        now = get_kyiv_now()
        sender_is_moderator = is_chat_moderator(device_id)
        
        new_message = {
            'id': str(uuid.uuid4()),
            'userId': user_id,
            'deviceId': device_id,
            'message': message,
            'timestamp': now.timestamp(),
            'time': now.strftime('%H:%M'),
            'date': now.strftime('%d.%m.%Y'),
            'isModerator': sender_is_moderator
        }
        
        if reply_to:
            messages = load_chat_messages()
            original_msg = next((m for m in messages if m.get('id') == reply_to), None)
            if original_msg:
                new_message['replyTo'] = {
                    'id': original_msg.get('id'),
                    'userId': original_msg.get('userId'),
                    'message': original_msg.get('message', '')[:100]
                }
        
        messages = load_chat_messages()
        messages.append(new_message)
        save_chat_messages(messages)
        
        log.info(f"Chat message from {user_id[:20]}: {message[:50]}...")
        
        return jsonify({
            'success': True,
            'message': new_message
        })
        
    except Exception as e:
        log.error(f"Error sending chat message: {e}")
        return jsonify({'error': str(e)}), 500


@chat_bp.route('/api/chat/message/<message_id>', methods=['DELETE'])
def delete_chat_message(message_id):
    """Delete a chat message (moderator only)."""
    try:
        data = request.get_json() or {}
        device_id = data.get('deviceId', '')
        is_moderator = data.get('isModerator', False)
        
        messages = load_chat_messages()
        message_to_delete = next((m for m in messages if m.get('id') == message_id), None)
        
        if not message_to_delete:
            return jsonify({'error': 'Повідомлення не знайдено'}), 404
        
        if is_moderator:
            pass
        elif device_id:
            nicknames = load_chat_nicknames()
            message_user = message_to_delete.get('userId')
            user_device = nicknames.get(message_user)
            if user_device != device_id:
                return jsonify({'error': 'Немає прав для видалення'}), 403
        else:
            return jsonify({'error': 'Немає прав для видалення'}), 403
        
        messages = [m for m in messages if m.get('id') != message_id]
        save_chat_messages(messages)
        
        log.info(f"Chat message {message_id} deleted by {'moderator' if is_moderator else device_id[:20]}")
        
        return jsonify({
            'success': True,
            'message': 'Повідомлення видалено'
        })
        
    except Exception as e:
        log.error(f"Error deleting chat message: {e}")
        return jsonify({'error': str(e)}), 500


@chat_bp.route('/api/chat/ban-user', methods=['POST'])
def ban_chat_user():
    """Ban a user from chat (moderator only)."""
    try:
        data = request.get_json() or {}
        target_nickname = data.get('nickname', '')
        is_moderator = data.get('isModerator', False)
        reason = data.get('reason', 'Порушення правил чату')
        
        if not is_moderator:
            return jsonify({'error': 'Тільки модератори можуть блокувати'}), 403
        
        if not target_nickname:
            return jsonify({'error': 'Вкажіть нікнейм'}), 400
        
        nicknames = load_chat_nicknames()
        target_device_id = nicknames.get(target_nickname)
        
        if not target_device_id:
            return jsonify({'error': 'Користувача не знайдено'}), 404
        
        banned = load_banned_users()
        now = get_kyiv_now()
        
        banned[target_device_id] = {
            'nickname': target_nickname,
            'reason': reason,
            'bannedAt': now.isoformat(),
            'bannedAtTimestamp': now.timestamp()
        }
        save_banned_users(banned)
        
        log.info(f"User banned: {target_nickname} (device: {target_device_id[:20]}...) - Reason: {reason}")
        
        return jsonify({
            'success': True,
            'message': f'Користувач {target_nickname} заблокований'
        })
        
    except Exception as e:
        log.error(f"Error banning user: {e}")
        return jsonify({'error': str(e)}), 500


@chat_bp.route('/api/chat/unban-user', methods=['POST'])
def unban_chat_user():
    """Unban a user from chat (moderator only)."""
    try:
        data = request.get_json() or {}
        target_nickname = data.get('nickname', '')
        is_moderator = data.get('isModerator', False)
        
        if not is_moderator:
            return jsonify({'error': 'Тільки модератори можуть розблоковувати'}), 403
        
        if not target_nickname:
            return jsonify({'error': 'Вкажіть нікнейм'}), 400
        
        nicknames = load_chat_nicknames()
        target_device_id = nicknames.get(target_nickname)
        
        banned = load_banned_users()
        removed = False
        
        if target_device_id and target_device_id in banned:
            del banned[target_device_id]
            removed = True
        
        for device_id, info in list(banned.items()):
            if info.get('nickname') == target_nickname:
                del banned[device_id]
                removed = True
        
        if not removed:
            return jsonify({'error': 'Користувач не заблокований'}), 404
        
        save_banned_users(banned)
        log.info(f"User unbanned: {target_nickname}")
        
        return jsonify({
            'success': True,
            'message': f'Користувач {target_nickname} розблокований'
        })
        
    except Exception as e:
        log.error(f"Error unbanning user: {e}")
        return jsonify({'error': str(e)}), 500


@chat_bp.route('/api/chat/check-ban', methods=['POST'])
def check_user_ban():
    """Check if current user is banned."""
    try:
        data = request.get_json() or {}
        device_id = data.get('deviceId', '')
        
        if not device_id:
            return jsonify({'banned': False})
        
        banned = load_banned_users()
        ban_info = banned.get(device_id)
        
        if ban_info:
            return jsonify({
                'banned': True,
                'reason': ban_info.get('reason', 'Порушення правил'),
                'bannedAt': ban_info.get('bannedAt', '')
            })
        
        return jsonify({'banned': False})
        
    except Exception as e:
        log.error(f"Error checking ban: {e}")
        return jsonify({'banned': False})


@chat_bp.route('/api/chat/banned-users', methods=['GET'])
def get_banned_users():
    """Get list of banned users (moderator only)."""
    try:
        is_mod = request.args.get('isModerator', 'false').lower() == 'true'
        if not is_mod:
            return jsonify({'error': 'Доступ заборонено'}), 403
        
        banned = load_banned_users()
        users = []
        for device_id, info in banned.items():
            users.append({
                'deviceId': device_id[:20] + '...',
                'nickname': info.get('nickname', 'Unknown'),
                'reason': info.get('reason', ''),
                'bannedAt': info.get('bannedAt', '')
            })
        
        return jsonify({'users': users, 'count': len(users)})
        
    except Exception as e:
        log.error(f"Error getting banned users: {e}")
        return jsonify({'error': str(e)}), 500


@chat_bp.route('/api/chat/add-moderator', methods=['POST'])
def add_chat_moderator():
    """Add a device as chat moderator (requires admin secret)."""
    try:
        data = request.get_json() or {}
        secret = data.get('secret', '')
        device_id = data.get('deviceId', '')
        
        if secret != MODERATOR_SECRET:
            return jsonify({'error': 'Невірний секрет'}), 403
        
        if not device_id:
            return jsonify({'error': 'deviceId обовʼязковий'}), 400
        
        moderators = load_chat_moderators()
        if device_id not in moderators:
            moderators.append(device_id)
            save_chat_moderators(moderators)
            log.info(f"Added chat moderator: {device_id[:20]}...")
        
        return jsonify({'success': True, 'message': 'Модератора додано'})
        
    except Exception as e:
        log.error(f"Error adding moderator: {e}")
        return jsonify({'error': str(e)}), 500


@chat_bp.route('/api/chat/remove-moderator', methods=['POST'])
def remove_chat_moderator():
    """Remove a device from chat moderators (requires admin secret)."""
    try:
        data = request.get_json() or {}
        secret = data.get('secret', '')
        device_id = data.get('deviceId', '')
        
        if secret != MODERATOR_SECRET:
            return jsonify({'error': 'Невірний секрет'}), 403
        
        if not device_id:
            return jsonify({'error': 'deviceId обовʼязковий'}), 400
        
        moderators = load_chat_moderators()
        if device_id in moderators:
            moderators.remove(device_id)
            save_chat_moderators(moderators)
            log.info(f"Removed chat moderator: {device_id[:20]}...")
        
        return jsonify({'success': True, 'message': 'Модератора видалено'})
        
    except Exception as e:
        log.error(f"Error removing moderator: {e}")
        return jsonify({'error': str(e)}), 500


@chat_bp.route('/api/chat/user-profile', methods=['POST'])
def get_chat_user_profile():
    """Get user profile info - basic info for all, detailed for moderators."""
    try:
        data = request.get_json() or {}
        requester_device_id = data.get('requesterDeviceId', '')
        target_device_id = data.get('targetDeviceId', '')
        target_user_id = data.get('targetUserId', '')
        
        is_requester_mod = is_chat_moderator(requester_device_id)
        
        if not target_device_id and target_user_id:
            nicknames = load_chat_nicknames()
            target_device_id = nicknames.get(target_user_id, '')
        
        is_target_mod = is_chat_moderator(target_device_id) if target_device_id else False
        is_banned = is_user_banned(target_device_id) if target_device_id else False
        
        response_data = {
            'userId': target_user_id,
            'isModerator': is_target_mod,
            'isBanned': is_banned,
        }
        
        if is_requester_mod and target_device_id:
            response_data['deviceId'] = target_device_id[:20] + '...' if len(target_device_id) > 20 else target_device_id
            response_data['regions'] = []  # Would need device_store access
        else:
            response_data['regions'] = []
            response_data['message'] = 'Детальна інформація доступна тільки модераторам'
        
        return jsonify(response_data)
        
    except Exception as e:
        log.error(f"Error getting user profile: {e}")
        return jsonify({'error': str(e)}), 500

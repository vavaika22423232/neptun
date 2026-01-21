"""
Chat API endpoints.

Blueprint for anonymous chat functionality.
"""
import logging

from flask import Blueprint, current_app, jsonify, request

log = logging.getLogger(__name__)

chat_bp = Blueprint('chat', __name__, url_prefix='/api/chat')


def get_chat_store():
    """Get chat store from app extensions."""
    return current_app.extensions.get('chat_store')


def get_chat_moderator():
    """Get chat moderator from app extensions."""
    return current_app.extensions.get('chat_moderator')


@chat_bp.route('/messages', methods=['GET'])
def get_messages():
    """
    Get chat messages.

    Query params:
        after: Only messages after this timestamp
        limit: Max messages to return (default 100, max 500)
    """
    store = get_chat_store()
    if not store:
        # Return empty messages if chat not configured
        return jsonify({
            'success': True,
            'messages': [],
            'count': 0,
        })

    try:
        after = request.args.get('after', '')
        limit = min(int(request.args.get('limit', 100)), 500)

        after_ts = float(after) if after else None
        messages = store.get_messages(after=after_ts, limit=limit)

        result = {
            'success': True,
            'messages': messages,
            'count': len(messages),
        }

        response = jsonify(result)
        response.headers['Cache-Control'] = 'public, max-age=3'
        return response

    except Exception as e:
        log.error(f"Error getting chat messages: {e}")
        return jsonify({'error': str(e)}), 500


@chat_bp.route('/send', methods=['POST'])
def send_message():
    """
    Send a new chat message.

    Body:
        userId: Nickname
        deviceId: Device identifier
        message: Message text
        replyTo: Optional message ID to reply to
    """
    store = get_chat_store()
    moderator = get_chat_moderator()

    if not store:
        return jsonify({'error': 'Chat not configured'}), 503

    try:
        data = request.get_json() or {}

        user_id = data.get('userId', '').strip()
        device_id = data.get('deviceId', '')
        message = data.get('message', '').strip()
        reply_to = data.get('replyTo')

        if not user_id or not message:
            return jsonify({'error': 'Missing userId or message'}), 400

        # Check if banned
        if moderator and moderator.is_banned(device_id):
            return jsonify({'error': 'Ви заблоковані в чаті', 'banned': True}), 403

        # Validate nickname ownership
        if device_id and not store.validate_nickname_ownership(user_id, device_id):
            return jsonify({'error': 'Цей нікнейм належить іншому користувачу'}), 403

        # Check forbidden nickname
        if moderator and moderator.is_nickname_forbidden(user_id):
            return jsonify({'error': 'Заборонений нікнейм'}), 400

        # Check if sender is moderator
        is_mod = moderator.is_moderator(device_id) if moderator else False

        # Add message
        new_message = store.add_message(
            user_id=user_id,
            message=message,
            device_id=device_id,
            reply_to=reply_to,
            is_moderator=is_mod,
        )

        return jsonify({
            'success': True,
            'message': new_message,
        })

    except Exception as e:
        log.error(f"Error sending chat message: {e}")
        return jsonify({'error': str(e)}), 500


@chat_bp.route('/check-nickname', methods=['POST'])
def check_nickname():
    """
    Check if nickname is available.

    Body:
        nickname: Nickname to check
        deviceId: Current device ID
    """
    store = get_chat_store()
    moderator = get_chat_moderator()

    if not store:
        return jsonify({'error': 'Chat not configured'}), 503

    try:
        data = request.get_json() or {}
        nickname = data.get('nickname', '').strip()
        device_id = data.get('deviceId', '')

        # Validate nickname format
        if moderator:
            error = moderator.validate_nickname(nickname)
            if error:
                return jsonify({'available': False, 'error': error}), 400

        # Check availability
        if store.check_nickname_available(nickname, device_id):
            return jsonify({'available': True})
        else:
            return jsonify({'available': False, 'error': 'Цей нікнейм вже зайнятий'}), 400

    except Exception as e:
        log.error(f"Error checking nickname: {e}")
        return jsonify({'error': str(e)}), 500


@chat_bp.route('/register-nickname', methods=['POST'])
def register_nickname():
    """
    Register a nickname for a device.

    Body:
        nickname: Nickname to register
        deviceId: Device ID
    """
    store = get_chat_store()
    moderator = get_chat_moderator()

    if not store:
        return jsonify({'error': 'Chat not configured'}), 503

    try:
        data = request.get_json() or {}
        nickname = data.get('nickname', '').strip()
        device_id = data.get('deviceId', '')

        if not nickname or not device_id:
            return jsonify({'success': False, 'error': 'Missing nickname or deviceId'}), 400

        # Validate nickname format
        if moderator:
            error = moderator.validate_nickname(nickname)
            if error:
                return jsonify({'success': False, 'error': error}), 400

        # Register
        if store.register_nickname(nickname, device_id):
            log.info(f"Registered chat nickname: {nickname}")
            return jsonify({'success': True, 'nickname': nickname})
        else:
            return jsonify({'success': False, 'error': 'Цей нікнейм вже зайнятий'}), 400

    except Exception as e:
        log.error(f"Error registering nickname: {e}")
        return jsonify({'error': str(e)}), 500


@chat_bp.route('/message/<message_id>', methods=['DELETE'])
def delete_message(message_id: str):
    """
    Delete a chat message.

    Body:
        deviceId: Requesting device
        isModerator: Whether requester is moderator
    """
    store = get_chat_store()
    moderator = get_chat_moderator()

    if not store:
        return jsonify({'error': 'Chat not configured'}), 503

    try:
        data = request.get_json() or {}
        device_id = data.get('deviceId', '')
        is_mod = data.get('isModerator', False)

        message = store.get_message(message_id)
        if not message:
            return jsonify({'error': 'Повідомлення не знайдено'}), 404

        # Check permissions
        can_delete = False

        if is_mod and moderator and moderator.is_moderator(device_id):
            can_delete = True
        elif device_id:
            # Regular user can delete own messages
            if store.validate_nickname_ownership(message.get('userId'), device_id):
                can_delete = True

        if not can_delete:
            return jsonify({'error': 'Немає прав для видалення'}), 403

        if store.delete_message(message_id):
            log.info(f"Chat message {message_id} deleted")
            return jsonify({'success': True, 'message': 'Повідомлення видалено'})
        else:
            return jsonify({'error': 'Failed to delete'}), 500

    except Exception as e:
        log.error(f"Error deleting message: {e}")
        return jsonify({'error': str(e)}), 500


@chat_bp.route('/check-ban', methods=['POST'])
def check_ban():
    """
    Check if device is banned.

    Body:
        deviceId: Device to check
    """
    moderator = get_chat_moderator()

    try:
        data = request.get_json() or {}
        device_id = data.get('deviceId', '')

        is_banned = moderator.is_banned(device_id) if moderator else False

        return jsonify({
            'banned': is_banned,
        })

    except Exception as e:
        log.error(f"Error checking ban: {e}")
        return jsonify({'error': str(e)}), 500


@chat_bp.route('/ban-user', methods=['POST'])
def ban_user():
    """
    Ban a user (moderator only).

    Body:
        nickname: Nickname to ban
        deviceId: Moderator's device ID
        isModerator: Must be true
        reason: Ban reason
    """
    store = get_chat_store()
    moderator = get_chat_moderator()

    if not store or not moderator:
        return jsonify({'error': 'Chat not configured'}), 503

    try:
        data = request.get_json() or {}
        target_nickname = data.get('nickname', '')
        device_id = data.get('deviceId', '')
        is_mod = data.get('isModerator', False)
        reason = data.get('reason', 'Порушення правил чату')

        if not is_mod or not moderator.is_moderator(device_id):
            return jsonify({'error': 'Тільки модератори можуть блокувати'}), 403

        if not target_nickname:
            return jsonify({'error': 'Вкажіть нікнейм'}), 400

        # Find device for nickname
        target_device = store.get_device_for_nickname(target_nickname)
        if not target_device:
            return jsonify({'error': 'Користувача не знайдено'}), 404

        moderator.ban_user(
            device_id=target_device,
            reason=reason,
            banned_by=device_id,
            nickname=target_nickname,
        )

        return jsonify({
            'success': True,
            'message': f'Користувач {target_nickname} заблокований',
        })

    except Exception as e:
        log.error(f"Error banning user: {e}")
        return jsonify({'error': str(e)}), 500


@chat_bp.route('/unban-user', methods=['POST'])
def unban_user():
    """
    Unban a user (moderator only).

    Body:
        deviceId: Device to unban OR nickname
        moderatorDeviceId: Moderator's device
        isModerator: Must be true
    """
    store = get_chat_store()
    moderator = get_chat_moderator()

    if not moderator:
        return jsonify({'error': 'Chat not configured'}), 503

    try:
        data = request.get_json() or {}
        target = data.get('deviceId') or data.get('nickname', '')
        mod_device = data.get('moderatorDeviceId', '')
        is_mod = data.get('isModerator', False)

        if not is_mod or not moderator.is_moderator(mod_device):
            return jsonify({'error': 'Тільки модератори можуть розблоковувати'}), 403

        # If nickname provided, find device
        if store and not target.startswith('{'):  # Not a device ID
            device = store.get_device_for_nickname(target)
            if device:
                target = device

        if moderator.unban_user(target):
            return jsonify({'success': True, 'message': 'Користувач розблокований'})
        else:
            return jsonify({'error': 'Користувача не знайдено в списку заблокованих'}), 404

    except Exception as e:
        log.error(f"Error unbanning user: {e}")
        return jsonify({'error': str(e)}), 500

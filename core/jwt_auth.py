"""
JWT Authentication Module for Neptun API
=========================================
Provides JWT-based authentication while maintaining backward compatibility with Device ID.

Migration Strategy:
1. Phase 1 (Current): Accept both JWT and Device ID, prefer JWT when available
2. Phase 2 (Future): Require JWT for sensitive operations, Device ID for read-only
3. Phase 3 (Final): Deprecate Device ID completely

Usage:
    from core.jwt_auth import create_token, verify_token, jwt_required, jwt_optional
    
    # Create token for user
    token = create_token(device_id='xxx', nickname='User123')
    
    # Protect endpoint (requires valid JWT)
    @app.route('/api/protected')
    @jwt_required
    def protected_endpoint():
        user = get_current_user()
        return jsonify({'user': user})
    
    # Optional JWT (falls back to Device ID)
    @app.route('/api/chat/send')
    @jwt_optional
    def send_message():
        user = get_current_user()  # Returns JWT user or Device ID
        ...
"""

import os
import time
import logging
from functools import wraps
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta

try:
    import jwt
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False
    print("WARNING: PyJWT not installed. JWT auth disabled.")

from flask import request, jsonify, g

log = logging.getLogger(__name__)

# ============================================================================
# Configuration
# ============================================================================

# Secret key for signing JWTs (MUST be set in production via environment)
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'neptun-dev-secret-change-in-production-2024')
JWT_ALGORITHM = 'HS256'

# Token expiration settings
JWT_ACCESS_TOKEN_EXPIRES = int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES', 86400 * 7))  # 7 days
JWT_REFRESH_TOKEN_EXPIRES = int(os.getenv('JWT_REFRESH_TOKEN_EXPIRES', 86400 * 30))  # 30 days

# Backward compatibility mode: accept Device ID when JWT not provided
JWT_BACKWARD_COMPAT = os.getenv('JWT_BACKWARD_COMPAT', 'true').lower() == 'true'

# Revoked tokens storage (in-memory, consider Redis for production)
_revoked_tokens: set = set()
_revoked_tokens_max_size = 10000


# ============================================================================
# Token Creation
# ============================================================================

def create_token(
    device_id: str,
    nickname: Optional[str] = None,
    is_moderator: bool = False,
    token_type: str = 'access',
    extra_claims: Optional[Dict] = None
) -> str:
    """
    Create a JWT token for a user.
    
    Args:
        device_id: Unique device identifier (kept for compatibility)
        nickname: User's chat nickname
        is_moderator: Whether user has moderator privileges
        token_type: 'access' or 'refresh'
        extra_claims: Additional claims to include
        
    Returns:
        Encoded JWT token string
    """
    if not JWT_AVAILABLE:
        raise RuntimeError("PyJWT not installed")
    
    now = datetime.utcnow()
    
    # Determine expiration based on token type
    if token_type == 'refresh':
        expires_delta = timedelta(seconds=JWT_REFRESH_TOKEN_EXPIRES)
    else:
        expires_delta = timedelta(seconds=JWT_ACCESS_TOKEN_EXPIRES)
    
    payload = {
        # Standard claims
        'sub': device_id,  # Subject (device_id for compatibility)
        'iat': now,        # Issued at
        'exp': now + expires_delta,  # Expiration
        'nbf': now,        # Not before
        
        # Custom claims
        'type': token_type,
        'device_id': device_id,  # Explicit device_id for backward compat
        'nickname': nickname,
        'is_moderator': is_moderator,
        'iss': 'neptun.in.ua',  # Issuer
    }
    
    # Add extra claims if provided
    if extra_claims:
        payload.update(extra_claims)
    
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    
    log.info(f"Created {token_type} token for device {device_id[:20]}...")
    return token


def create_token_pair(
    device_id: str,
    nickname: Optional[str] = None,
    is_moderator: bool = False
) -> Tuple[str, str]:
    """
    Create both access and refresh tokens.
    
    Returns:
        Tuple of (access_token, refresh_token)
    """
    access_token = create_token(
        device_id=device_id,
        nickname=nickname,
        is_moderator=is_moderator,
        token_type='access'
    )
    
    refresh_token = create_token(
        device_id=device_id,
        nickname=nickname,
        is_moderator=is_moderator,
        token_type='refresh'
    )
    
    return access_token, refresh_token


# ============================================================================
# Token Verification
# ============================================================================

def verify_token(token: str, expected_type: str = 'access') -> Tuple[bool, Optional[Dict], Optional[str]]:
    """
    Verify and decode a JWT token.
    
    Args:
        token: The JWT token to verify
        expected_type: Expected token type ('access' or 'refresh')
        
    Returns:
        Tuple of (is_valid, payload, error_message)
    """
    if not JWT_AVAILABLE:
        return False, None, "JWT not available"
    
    if not token:
        return False, None, "No token provided"
    
    # Check if token is revoked
    if token in _revoked_tokens:
        return False, None, "Token has been revoked"
    
    try:
        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
            options={
                'require': ['exp', 'iat', 'sub'],
                'verify_exp': True,
                'verify_iat': True,
            }
        )
        
        # Verify token type
        token_type = payload.get('type', 'access')
        if token_type != expected_type:
            return False, None, f"Invalid token type: expected {expected_type}, got {token_type}"
        
        return True, payload, None
        
    except jwt.ExpiredSignatureError:
        return False, None, "Token has expired"
    except jwt.InvalidTokenError as e:
        return False, None, f"Invalid token: {str(e)}"
    except Exception as e:
        log.error(f"Token verification error: {e}")
        return False, None, "Token verification failed"


def revoke_token(token: str) -> bool:
    """
    Revoke a token (add to blacklist).
    
    Note: In production, use Redis or database for persistence.
    """
    global _revoked_tokens
    
    # Prevent memory overflow
    if len(_revoked_tokens) >= _revoked_tokens_max_size:
        # Remove oldest half (approximate LRU)
        _revoked_tokens = set(list(_revoked_tokens)[_revoked_tokens_max_size // 2:])
    
    _revoked_tokens.add(token)
    log.info(f"Token revoked. Total revoked: {len(_revoked_tokens)}")
    return True


def refresh_access_token(refresh_token: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Use a refresh token to get a new access token.
    
    Returns:
        Tuple of (new_access_token, error_message)
    """
    is_valid, payload, error = verify_token(refresh_token, expected_type='refresh')
    
    if not is_valid:
        return None, error
    
    # Create new access token with same claims
    new_token = create_token(
        device_id=payload.get('device_id', payload.get('sub')),
        nickname=payload.get('nickname'),
        is_moderator=payload.get('is_moderator', False),
        token_type='access'
    )
    
    return new_token, None


# ============================================================================
# Request Helpers
# ============================================================================

def get_token_from_request() -> Optional[str]:
    """
    Extract JWT token from request.
    
    Looks in:
    1. Authorization header (Bearer token)
    2. X-Auth-Token header
    3. 'token' query parameter
    """
    # Check Authorization header
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        return auth_header[7:]
    
    # Check X-Auth-Token header
    token_header = request.headers.get('X-Auth-Token')
    if token_header:
        return token_header
    
    # Check query parameter (less secure, use only for SSE)
    token_param = request.args.get('token')
    if token_param:
        return token_param
    
    return None


def get_device_id_from_request() -> Optional[str]:
    """
    Extract Device ID from request (backward compatibility).
    
    Looks in:
    1. Request JSON body (deviceId)
    2. X-Device-ID header
    3. Query parameter
    """
    # Check JSON body
    try:
        data = request.get_json(silent=True) or {}
        if data.get('deviceId'):
            return data['deviceId']
    except Exception:
        pass
    
    # Check header
    device_header = request.headers.get('X-Device-ID')
    if device_header:
        return device_header
    
    # Check query parameter
    device_param = request.args.get('deviceId')
    if device_param:
        return device_param
    
    return None


def get_current_user() -> Optional[Dict[str, Any]]:
    """
    Get current authenticated user from request context.
    
    Returns user dict with at minimum:
    - device_id: str
    - nickname: Optional[str]
    - is_moderator: bool
    - auth_method: 'jwt' or 'device_id'
    """
    return getattr(g, 'current_user', None)


# ============================================================================
# Decorators
# ============================================================================

def jwt_required(f):
    """
    Decorator that requires valid JWT token.
    
    If JWT_BACKWARD_COMPAT is True, falls back to Device ID.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        # Try JWT first
        token = get_token_from_request()
        
        if token:
            is_valid, payload, error = verify_token(token)
            if is_valid:
                g.current_user = {
                    'device_id': payload.get('device_id', payload.get('sub')),
                    'nickname': payload.get('nickname'),
                    'is_moderator': payload.get('is_moderator', False),
                    'auth_method': 'jwt',
                    'token_payload': payload
                }
                return f(*args, **kwargs)
            else:
                # Invalid JWT provided
                if not JWT_BACKWARD_COMPAT:
                    return jsonify({'error': error, 'code': 'invalid_token'}), 401
                log.debug(f"JWT invalid ({error}), trying device_id fallback")
        
        # Fallback to Device ID if backward compat enabled
        if JWT_BACKWARD_COMPAT:
            device_id = get_device_id_from_request()
            if device_id:
                g.current_user = {
                    'device_id': device_id,
                    'nickname': None,
                    'is_moderator': False,
                    'auth_method': 'device_id'
                }
                return f(*args, **kwargs)
        
        # No valid auth
        return jsonify({
            'error': 'Authentication required',
            'code': 'auth_required',
            'hint': 'Provide JWT token in Authorization header or deviceId in request body'
        }), 401
    
    return decorated


def jwt_optional(f):
    """
    Decorator that accepts but doesn't require authentication.
    
    Sets g.current_user if authenticated, None otherwise.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        g.current_user = None
        
        # Try JWT first
        token = get_token_from_request()
        if token:
            is_valid, payload, _ = verify_token(token)
            if is_valid:
                g.current_user = {
                    'device_id': payload.get('device_id', payload.get('sub')),
                    'nickname': payload.get('nickname'),
                    'is_moderator': payload.get('is_moderator', False),
                    'auth_method': 'jwt',
                    'token_payload': payload
                }
                return f(*args, **kwargs)
        
        # Try Device ID
        device_id = get_device_id_from_request()
        if device_id:
            g.current_user = {
                'device_id': device_id,
                'nickname': None,
                'is_moderator': False,
                'auth_method': 'device_id'
            }
        
        return f(*args, **kwargs)
    
    return decorated


def moderator_required(f):
    """
    Decorator that requires moderator privileges.
    
    Must be used after @jwt_required or @jwt_optional.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user()
        
        if not user:
            return jsonify({'error': 'Authentication required'}), 401
        
        if not user.get('is_moderator'):
            return jsonify({'error': 'Moderator privileges required'}), 403
        
        return f(*args, **kwargs)
    
    return decorated


# ============================================================================
# API Endpoints (to be registered with Flask app)
# ============================================================================

def register_jwt_routes(app):
    """
    Register JWT-related API routes.
    
    Call this from your Flask app initialization:
        from core.jwt_auth import register_jwt_routes
        register_jwt_routes(app)
    """
    
    @app.route('/api/auth/token', methods=['POST'])
    def auth_get_token():
        """
        Get JWT token for a device.
        
        Request body:
        {
            "deviceId": "device_xxx",
            "nickname": "User123" (optional)
        }
        
        Response:
        {
            "access_token": "eyJ...",
            "refresh_token": "eyJ...",
            "expires_in": 604800,
            "token_type": "Bearer"
        }
        """
        if not JWT_AVAILABLE:
            return jsonify({'error': 'JWT not available on this server'}), 503
        
        try:
            data = request.get_json() or {}
            device_id = data.get('deviceId', '').strip()
            nickname = data.get('nickname', '').strip() or None
            
            if not device_id:
                return jsonify({'error': 'deviceId is required'}), 400
            
            # Check if this is a moderator (you'd check your moderators list here)
            # For now, just pass False - moderator status is set separately
            is_moderator = False
            
            access_token, refresh_token = create_token_pair(
                device_id=device_id,
                nickname=nickname,
                is_moderator=is_moderator
            )
            
            return jsonify({
                'access_token': access_token,
                'refresh_token': refresh_token,
                'expires_in': JWT_ACCESS_TOKEN_EXPIRES,
                'token_type': 'Bearer',
                'device_id': device_id
            })
            
        except Exception as e:
            log.error(f"Error creating token: {e}")
            return jsonify({'error': str(e)}), 500
    
    
    @app.route('/api/auth/refresh', methods=['POST'])
    def auth_refresh_token():
        """
        Refresh an access token using a refresh token.
        
        Request body:
        {
            "refresh_token": "eyJ..."
        }
        
        Response:
        {
            "access_token": "eyJ...",
            "expires_in": 604800,
            "token_type": "Bearer"
        }
        """
        if not JWT_AVAILABLE:
            return jsonify({'error': 'JWT not available on this server'}), 503
        
        try:
            data = request.get_json() or {}
            refresh_token = data.get('refresh_token', '')
            
            if not refresh_token:
                return jsonify({'error': 'refresh_token is required'}), 400
            
            new_token, error = refresh_access_token(refresh_token)
            
            if error:
                return jsonify({'error': error, 'code': 'refresh_failed'}), 401
            
            return jsonify({
                'access_token': new_token,
                'expires_in': JWT_ACCESS_TOKEN_EXPIRES,
                'token_type': 'Bearer'
            })
            
        except Exception as e:
            log.error(f"Error refreshing token: {e}")
            return jsonify({'error': str(e)}), 500
    
    
    @app.route('/api/auth/revoke', methods=['POST'])
    @jwt_required
    def auth_revoke_token():
        """
        Revoke the current access token (logout).
        """
        token = get_token_from_request()
        if token:
            revoke_token(token)
        
        return jsonify({'success': True, 'message': 'Token revoked'})
    
    
    @app.route('/api/auth/verify', methods=['GET'])
    def auth_verify_token():
        """
        Verify if the provided token is valid.
        
        Returns user info if valid.
        """
        token = get_token_from_request()
        
        if not token:
            return jsonify({
                'valid': False,
                'error': 'No token provided'
            }), 401
        
        is_valid, payload, error = verify_token(token)
        
        if not is_valid:
            return jsonify({
                'valid': False,
                'error': error
            }), 401
        
        return jsonify({
            'valid': True,
            'user': {
                'device_id': payload.get('device_id', payload.get('sub')),
                'nickname': payload.get('nickname'),
                'is_moderator': payload.get('is_moderator', False),
            },
            'expires_at': payload.get('exp')
        })
    
    log.info("JWT auth routes registered")


# ============================================================================
# Module initialization check
# ============================================================================

if not JWT_AVAILABLE:
    log.warning("PyJWT not installed. JWT authentication is disabled.")
    log.warning("Install with: pip install PyJWT>=2.8.0")

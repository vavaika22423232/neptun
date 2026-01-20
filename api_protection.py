"""
API PROTECTION MODULE - Production-grade hardening for Neptune backend.
Prevents server crashes from:
- Large response payloads (23+ GB traffic spike)
- Polling abuse (high request frequency)
- Memory exhaustion (2GB limit)
- CPU overload (100% utilization)

This module is internet-facing, unauthenticated, and must survive hostile usage.
"""

import hashlib
import json
import logging
import os
import threading
import time
from collections import defaultdict
from functools import wraps

from flask import Response, g, jsonify, request

log = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION - Production-safe defaults
# ============================================================================

# Maximum response size in bytes (5MB default - prevents 23GB incidents)
MAX_RESPONSE_SIZE_BYTES = int(os.getenv('MAX_RESPONSE_SIZE', 5 * 1024 * 1024))

# Rate limiting windows
RATE_LIMIT_WINDOW_SECONDS = 60  # 1 minute window
RATE_LIMIT_STRICT_WINDOW = 10   # 10 second window for burst protection

# Per-endpoint rate limits (requests per minute per IP)
ENDPOINT_RATE_LIMITS = {
    # Heavy data endpoints - strict limits
    '/data': {'rpm': 30, 'burst': 5},
    '/api/messages': {'rpm': 30, 'burst': 5},
    '/api/events': {'rpm': 30, 'burst': 5},
    '/api/alarm-status': {'rpm': 60, 'burst': 10},
    '/api/alarm-history': {'rpm': 20, 'burst': 3},
    '/api/alarms': {'rpm': 60, 'burst': 10},
    '/api/alarms/all': {'rpm': 60, 'burst': 10},
    '/api/alarms/proxy': {'rpm': 60, 'burst': 10},

    # Medium endpoints
    '/presence': {'rpm': 20, 'burst': 3},
    '/stream': {'rpm': 5, 'burst': 2},
    '/comments': {'rpm': 30, 'burst': 5},

    # Light endpoints
    '/api/visitor_count': {'rpm': 60, 'burst': 10},
    '/active_alarms': {'rpm': 60, 'burst': 10},
    '/alarms_stats': {'rpm': 30, 'burst': 5},
    '/raion_alarms': {'rpm': 60, 'burst': 10},

    # Default for unlisted endpoints
    'default': {'rpm': 120, 'burst': 20},
}

# Pagination limits
MAX_PAGE_SIZE = 100  # Maximum items per page
DEFAULT_PAGE_SIZE = 50  # Default items per page
MAX_TOTAL_ITEMS = 500  # Maximum items to return even with pagination

# Concurrency limits
MAX_CONCURRENT_REQUESTS_PER_IP = 5  # Prevent parallel polling abuse
MAX_GLOBAL_CONCURRENT_HEAVY = 20   # Max concurrent heavy requests server-wide

# Abuse detection thresholds
ABUSE_THRESHOLD_RPM = 200  # Mark as abusive if exceeds this
ABUSE_BAN_DURATION = 300   # Ban duration in seconds (5 minutes)
ABUSE_STRIKE_THRESHOLD = 3 # Number of violations before temp ban

# Request timeout (for monitoring)
REQUEST_TIMEOUT_WARNING = 5.0  # Log warning if request takes longer


# ============================================================================
# STORAGE - Thread-safe counters and state
# ============================================================================

_lock = threading.RLock()

# Rate limiting storage: {ip: [(timestamp, endpoint), ...]}
_request_history = defaultdict(list)

# Concurrent request tracking: {ip: count}
_concurrent_requests = defaultdict(int)
_global_heavy_count = 0

# Abuse tracking: {ip: {'strikes': N, 'banned_until': timestamp}}
_abuse_tracker = defaultdict(lambda: {'strikes': 0, 'banned_until': 0})

# Response size tracking for observability: {endpoint: [sizes]}
_response_sizes = defaultdict(list)

# Slow request tracking: {endpoint: [(duration, timestamp), ...]}
_slow_requests = defaultdict(list)


# ============================================================================
# CORE RATE LIMITING
# ============================================================================

def _get_client_ip():
    """Get real client IP, handling proxies."""
    # Render.com sets X-Forwarded-For
    forwarded = request.headers.get('X-Forwarded-For', '')
    if forwarded:
        # First IP in chain is original client
        return forwarded.split(',')[0].strip()
    return request.remote_addr or 'unknown'


def _cleanup_old_entries(ip):
    """Remove entries older than rate limit window."""
    cutoff = time.time() - RATE_LIMIT_WINDOW_SECONDS
    with _lock:
        _request_history[ip] = [
            (ts, ep) for ts, ep in _request_history[ip]
            if ts > cutoff
        ]


def _get_rate_limit_for_endpoint(endpoint):
    """Get rate limits for specific endpoint or default."""
    # Exact match
    if endpoint in ENDPOINT_RATE_LIMITS:
        return ENDPOINT_RATE_LIMITS[endpoint]

    # Prefix match (e.g., /api/family/* -> /api/family)
    for pattern, limits in ENDPOINT_RATE_LIMITS.items():
        if endpoint.startswith(pattern):
            return limits

    return ENDPOINT_RATE_LIMITS['default']


def check_rate_limit(endpoint=None):
    """
    Check if request should be rate limited.
    Returns (allowed: bool, retry_after: int or None, reason: str or None)
    """
    ip = _get_client_ip()
    now = time.time()
    endpoint = endpoint or request.path

    # Check if IP is banned
    with _lock:
        abuse_info = _abuse_tracker[ip]
        if abuse_info['banned_until'] > now:
            return False, int(abuse_info['banned_until'] - now), 'temporarily_banned'

    # Cleanup old entries
    _cleanup_old_entries(ip)

    # Get limits for this endpoint
    limits = _get_rate_limit_for_endpoint(endpoint)
    rpm_limit = limits['rpm']
    burst_limit = limits['burst']

    with _lock:
        # Count requests in last minute to this endpoint
        endpoint_requests = [
            (ts, ep) for ts, ep in _request_history[ip]
            if ep == endpoint and now - ts < RATE_LIMIT_WINDOW_SECONDS
        ]

        # Count burst requests (last 10 seconds)
        burst_requests = [
            (ts, ep) for ts, ep in _request_history[ip]
            if ep == endpoint and now - ts < RATE_LIMIT_STRICT_WINDOW
        ]

        # Count all requests for abuse detection
        all_requests = len(_request_history[ip])

    # Check burst limit first (stricter)
    if len(burst_requests) >= burst_limit:
        _record_abuse_strike(ip, 'burst_limit')
        return False, RATE_LIMIT_STRICT_WINDOW, 'burst_rate_exceeded'

    # Check RPM limit
    if len(endpoint_requests) >= rpm_limit:
        _record_abuse_strike(ip, 'rpm_limit')
        return False, 30, 'rate_limit_exceeded'

    # Check if this client is being abusive overall
    if all_requests >= ABUSE_THRESHOLD_RPM:
        _record_abuse_strike(ip, 'abuse_threshold')
        return False, 60, 'too_many_requests'

    # Record this request
    with _lock:
        _request_history[ip].append((now, endpoint))

    return True, None, None


def _record_abuse_strike(ip, reason):
    """Record an abuse strike and potentially ban the IP."""
    with _lock:
        _abuse_tracker[ip]['strikes'] += 1
        strikes = _abuse_tracker[ip]['strikes']

        if strikes >= ABUSE_STRIKE_THRESHOLD:
            _abuse_tracker[ip]['banned_until'] = time.time() + ABUSE_BAN_DURATION
            log.warning(f"[ABUSE] IP {ip} BANNED for {ABUSE_BAN_DURATION}s - reason: {reason}, strikes: {strikes}")
        else:
            log.info(f"[ABUSE] IP {ip} strike {strikes}/{ABUSE_STRIKE_THRESHOLD} - reason: {reason}")


# ============================================================================
# CONCURRENCY LIMITING
# ============================================================================

def acquire_request_slot(is_heavy=False):
    """
    Acquire a slot for concurrent request tracking.
    Returns True if slot acquired, False if should reject.
    """
    global _global_heavy_count
    ip = _get_client_ip()

    with _lock:
        # Check per-IP limit
        if _concurrent_requests[ip] >= MAX_CONCURRENT_REQUESTS_PER_IP:
            log.warning(f"[CONCURRENCY] IP {ip} exceeded concurrent limit ({MAX_CONCURRENT_REQUESTS_PER_IP})")
            return False

        # Check global heavy request limit
        if is_heavy and _global_heavy_count >= MAX_GLOBAL_CONCURRENT_HEAVY:
            log.warning(f"[CONCURRENCY] Global heavy request limit reached ({MAX_GLOBAL_CONCURRENT_HEAVY})")
            return False

        # Acquire slot
        _concurrent_requests[ip] += 1
        if is_heavy:
            _global_heavy_count += 1

        return True


def release_request_slot(is_heavy=False):
    """Release a concurrent request slot."""
    global _global_heavy_count
    ip = _get_client_ip()

    with _lock:
        _concurrent_requests[ip] = max(0, _concurrent_requests[ip] - 1)
        if is_heavy:
            _global_heavy_count = max(0, _global_heavy_count - 1)


# ============================================================================
# RESPONSE SIZE GUARDS
# ============================================================================

def check_response_size(data, max_size=None):
    """
    Check if response data exceeds size limit.
    Returns (ok: bool, size: int, truncated_data: any)
    """
    max_size = max_size or MAX_RESPONSE_SIZE_BYTES

    # Serialize to check size
    if isinstance(data, (dict, list)):
        serialized = json.dumps(data, separators=(',', ':'))
    elif isinstance(data, str):
        serialized = data
    else:
        serialized = str(data)

    size = len(serialized.encode('utf-8'))

    if size > max_size:
        log.error(f"[RESPONSE SIZE] Response exceeds limit: {size} > {max_size} bytes")
        return False, size, None

    return True, size, data


def truncate_response(data, field_name, max_items):
    """Truncate a list field in response data."""
    if isinstance(data, dict) and field_name in data:
        if isinstance(data[field_name], list):
            original_len = len(data[field_name])
            if original_len > max_items:
                data[field_name] = data[field_name][:max_items]
                log.info(f"[TRUNCATE] {field_name}: {original_len} -> {max_items} items")
                data[f'{field_name}_truncated'] = True
                data[f'{field_name}_total'] = original_len
    return data


# ============================================================================
# CACHING HELPERS
# ============================================================================

def compute_etag(data):
    """Compute ETag for response data."""
    if isinstance(data, (dict, list)):
        content = json.dumps(data, sort_keys=True, separators=(',', ':'))
    else:
        content = str(data)
    return f'"{hashlib.md5(content.encode()).hexdigest()[:16]}"'


def check_etag_match(etag):
    """Check if client's If-None-Match header matches ETag."""
    client_etag = request.headers.get('If-None-Match')
    return client_etag == etag


# ============================================================================
# PAGINATION HELPERS
# ============================================================================

def get_pagination_params():
    """Extract and validate pagination parameters from request."""
    try:
        page = max(1, int(request.args.get('page', 1)))
        per_page = min(MAX_PAGE_SIZE, max(1, int(request.args.get('per_page', DEFAULT_PAGE_SIZE))))
    except (ValueError, TypeError):
        page = 1
        per_page = DEFAULT_PAGE_SIZE

    return page, per_page


def paginate_list(items, page=None, per_page=None, max_total=None):
    """
    Paginate a list of items.
    Returns (paginated_items, pagination_info)
    """
    if page is None or per_page is None:
        page, per_page = get_pagination_params()

    max_total = max_total or MAX_TOTAL_ITEMS
    total = len(items)

    # Apply max total limit first
    if total > max_total:
        items = items[:max_total]
        total = max_total

    # Calculate pagination
    start = (page - 1) * per_page
    end = start + per_page
    paginated = items[start:end]

    total_pages = (total + per_page - 1) // per_page

    pagination_info = {
        'page': page,
        'per_page': per_page,
        'total': total,
        'total_pages': total_pages,
        'has_next': page < total_pages,
        'has_prev': page > 1,
    }

    return paginated, pagination_info


# ============================================================================
# OBSERVABILITY
# ============================================================================

def record_response_size(endpoint, size):
    """Record response size for monitoring."""
    with _lock:
        _response_sizes[endpoint].append(size)
        # Keep only last 100 entries per endpoint
        if len(_response_sizes[endpoint]) > 100:
            _response_sizes[endpoint] = _response_sizes[endpoint][-100:]


def record_slow_request(endpoint, duration):
    """Record slow request for monitoring."""
    if duration > REQUEST_TIMEOUT_WARNING:
        with _lock:
            _slow_requests[endpoint].append((duration, time.time()))
            # Keep only last 50 entries per endpoint
            if len(_slow_requests[endpoint]) > 50:
                _slow_requests[endpoint] = _slow_requests[endpoint][-50:]
        log.warning(f"[SLOW REQUEST] {endpoint}: {duration:.2f}s")


def get_protection_stats():
    """Get current protection statistics for admin dashboard."""
    with _lock:
        # Response size stats
        size_stats = {}
        for endpoint, sizes in _response_sizes.items():
            if sizes:
                size_stats[endpoint] = {
                    'avg': sum(sizes) / len(sizes),
                    'max': max(sizes),
                    'count': len(sizes)
                }

        # Slow request stats
        slow_stats = {}
        for endpoint, requests in _slow_requests.items():
            if requests:
                durations = [d for d, _ in requests]
                slow_stats[endpoint] = {
                    'avg': sum(durations) / len(durations),
                    'max': max(durations),
                    'count': len(requests)
                }

        # Abuse stats
        banned_ips = [
            ip for ip, info in _abuse_tracker.items()
            if info['banned_until'] > time.time()
        ]

        return {
            'response_sizes': size_stats,
            'slow_requests': slow_stats,
            'banned_ips': len(banned_ips),
            'concurrent_requests': dict(_concurrent_requests),
            'global_heavy_count': _global_heavy_count,
        }


# ============================================================================
# DECORATORS
# ============================================================================

def rate_limited(func):
    """Decorator to apply rate limiting to an endpoint."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        allowed, retry_after, reason = check_rate_limit()
        if not allowed:
            log.info(f"[RATE LIMIT] {_get_client_ip()} -> {request.path}: {reason}")
            response = jsonify({
                'error': reason,
                'retry_after': retry_after,
                'message': f'Rate limit exceeded. Try again in {retry_after} seconds.'
            })
            response.status_code = 429
            response.headers['Retry-After'] = str(retry_after)
            return response
        return func(*args, **kwargs)
    return wrapper


def protected_endpoint(is_heavy=False, max_response_size=None):
    """
    Comprehensive protection decorator combining:
    - Rate limiting
    - Concurrency control
    - Response size checking
    - Timing/observability
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            endpoint = request.path

            # Rate limiting
            allowed, retry_after, reason = check_rate_limit(endpoint)
            if not allowed:
                return jsonify({
                    'error': reason,
                    'retry_after': retry_after
                }), 429

            # Concurrency check
            if not acquire_request_slot(is_heavy):
                return jsonify({
                    'error': 'too_many_concurrent_requests',
                    'message': 'Server is busy. Please try again shortly.'
                }), 503

            try:
                # Execute the endpoint
                result = func(*args, **kwargs)

                # Record timing
                duration = time.time() - start_time
                record_slow_request(endpoint, duration)

                # If result is a Response, try to check its size
                if isinstance(result, Response):
                    size = result.content_length or len(result.get_data())
                    record_response_size(endpoint, size)

                    # Check max response size
                    max_size = max_response_size or MAX_RESPONSE_SIZE_BYTES
                    if size > max_size:
                        log.error(f"[RESPONSE TOO LARGE] {endpoint}: {size} bytes")
                        return jsonify({
                            'error': 'response_too_large',
                            'message': 'Response exceeds maximum allowed size.'
                        }), 500

                return result

            finally:
                release_request_slot(is_heavy)

        return wrapper
    return decorator


def size_guarded(max_items=100, list_field='items'):
    """
    Decorator to enforce response size limits with truncation.
    Applied to endpoints that return lists of items.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)

            # If it's a tuple (data, status_code)
            if isinstance(result, tuple):
                data, status = result[0], result[1] if len(result) > 1 else 200
                if hasattr(data, 'get_json'):
                    json_data = data.get_json()
                    json_data = truncate_response(json_data, list_field, max_items)
                    return jsonify(json_data), status
                return result

            # If it's a Response with JSON
            if isinstance(result, Response) and result.content_type.startswith('application/json'):
                try:
                    json_data = result.get_json()
                    if json_data:
                        json_data = truncate_response(json_data, list_field, max_items)
                        new_response = jsonify(json_data)
                        new_response.status_code = result.status_code
                        # Copy headers
                        for key, value in result.headers:
                            if key.lower() != 'content-length':
                                new_response.headers[key] = value
                        return new_response
                except Exception:
                    pass

            return result
        return wrapper
    return decorator


# ============================================================================
# DIFF-BASED UPDATE HELPERS
# ============================================================================

def supports_since_param():
    """Check if request includes 'since' parameter for incremental updates."""
    return request.args.get('since') is not None


def get_since_timestamp():
    """Get 'since' timestamp from request, with validation."""
    since = request.args.get('since')
    if not since:
        return None

    try:
        # Accept Unix timestamp (seconds)
        ts = float(since)
        # Sanity check: not too old (max 24h) and not in future
        now = time.time()
        if ts > now:
            return now
        if ts < now - 86400:  # 24 hours max
            return now - 86400
        return ts
    except (ValueError, TypeError):
        return None


def filter_by_since(items, timestamp_field='timestamp', since=None):
    """Filter items to only those newer than 'since' timestamp."""
    if since is None:
        since = get_since_timestamp()
    if since is None:
        return items

    filtered = []
    for item in items:
        item_ts = item.get(timestamp_field)
        if item_ts is None:
            continue

        # Handle different timestamp formats
        try:
            if isinstance(item_ts, (int, float)):
                ts = item_ts
            elif isinstance(item_ts, str):
                # Try ISO format
                from datetime import datetime
                dt = datetime.fromisoformat(item_ts.replace('Z', '+00:00'))
                ts = dt.timestamp()
            else:
                continue

            if ts > since:
                filtered.append(item)
        except Exception:
            # Include items we can't parse
            filtered.append(item)

    return filtered


# ============================================================================
# INITIALIZATION
# ============================================================================

def init_protection(app):
    """
    Initialize API protection on Flask app.
    Call this after creating the Flask app.
    """
    # Add before_request handler
    @app.before_request
    def before_request_protection():
        g.request_start_time = time.time()
        g.client_ip = _get_client_ip()

    # Add after_request handler for observability
    @app.after_request
    def after_request_protection(response):
        # Record request timing
        if hasattr(g, 'request_start_time'):
            duration = time.time() - g.request_start_time
            if duration > REQUEST_TIMEOUT_WARNING:
                log.warning(f"[SLOW] {request.path}: {duration:.2f}s from {getattr(g, 'client_ip', 'unknown')}")

        # Record response size for API endpoints
        if request.path.startswith('/api/') or request.path in ['/data', '/presence', '/stream']:
            size = response.content_length or 0
            if size > 0:
                record_response_size(request.path, size)

        return response

    log.info("[PROTECTION] API protection module initialized")
    log.info(f"[PROTECTION] Max response size: {MAX_RESPONSE_SIZE_BYTES / 1024 / 1024:.1f}MB")
    log.info(f"[PROTECTION] Abuse ban duration: {ABUSE_BAN_DURATION}s")

    return True


# ============================================================================
# ADMIN ENDPOINT (add to app separately)
# ============================================================================

def get_protection_status_endpoint():
    """
    Returns a Flask route handler for protection status.
    Usage: app.route('/admin/protection_status')(get_protection_status_endpoint())
    """
    def protection_status():
        stats = get_protection_stats()
        return jsonify({
            'protection': 'active',
            'max_response_size_mb': MAX_RESPONSE_SIZE_BYTES / 1024 / 1024,
            'rate_limits': ENDPOINT_RATE_LIMITS,
            'stats': stats
        })
    return protection_status

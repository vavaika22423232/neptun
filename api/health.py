"""
Health check API blueprint.

Endpoints для моніторингу стану сервісу.
"""
import logging
import os
import time

from flask import Blueprint, jsonify

log = logging.getLogger(__name__)

health_bp = Blueprint('health', __name__)

# Track startup time
_startup_time = time.time()

# Dependencies (set via init)
_track_store = None
_telegram_status = None
_alarm_status = None


def init_health_api(track_store=None, telegram_status_fn=None, alarm_status_fn=None):
    """Initialize health API with dependencies."""
    global _track_store, _telegram_status, _alarm_status
    _track_store = track_store
    _telegram_status = telegram_status_fn
    _alarm_status = alarm_status_fn


@health_bp.route('/health')
def health():
    """
    Basic health check.

    Returns 200 if service is running.
    """
    return jsonify({
        'status': 'ok',
        'uptime': int(time.time() - _startup_time),
    })


@health_bp.route('/health/detailed')
def health_detailed():
    """
    Detailed health check with component status.

    Returns comprehensive status for monitoring.
    """
    try:
        status = {
            'status': 'ok',
            'uptime_seconds': int(time.time() - _startup_time),
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'components': {},
        }

        # Track store status
        if _track_store:
            try:
                count = _track_store.count()
                pending = len(_track_store.get_ungeocodeded())
                status['components']['tracks'] = {
                    'status': 'ok',
                    'count': count,
                    'pending_geocode': pending,
                }
            except Exception as e:
                status['components']['tracks'] = {
                    'status': 'error',
                    'error': str(e),
                }

        # Telegram status
        if _telegram_status:
            try:
                tg_status = _telegram_status()
                status['components']['telegram'] = {
                    'status': 'ok' if tg_status.get('connected') else 'disconnected',
                    **tg_status,
                }
            except Exception as e:
                status['components']['telegram'] = {
                    'status': 'error',
                    'error': str(e),
                }

        # Alarm API status
        if _alarm_status:
            try:
                alarm_status = _alarm_status()
                status['components']['alarms'] = {
                    'status': 'ok' if alarm_status.get('configured') else 'not_configured',
                    **alarm_status,
                }
            except Exception as e:
                status['components']['alarms'] = {
                    'status': 'error',
                    'error': str(e),
                }

        # Storage status
        persistent_dir = os.getenv('PERSISTENT_DATA_DIR', '/data')
        status['components']['storage'] = {
            'status': 'ok' if os.path.isdir(persistent_dir) else 'fallback',
            'persistent_available': os.path.isdir(persistent_dir),
            'persistent_dir': persistent_dir,
        }

        # Memory status
        try:
            import psutil  # type: ignore[import-not-found]
            process = psutil.Process(os.getpid())
            mem_info = process.memory_info()
            status['components']['memory'] = {
                'status': 'ok',
                'rss_mb': round(mem_info.rss / 1024 / 1024, 1),
                'vms_mb': round(mem_info.vms / 1024 / 1024, 1),
            }
        except ImportError:
            status['components']['memory'] = {
                'status': 'unknown',
                'error': 'psutil not installed',
            }
        except Exception as e:
            status['components']['memory'] = {
                'status': 'error',
                'error': str(e),
            }

        # Set overall status based on components
        component_statuses = [
            c.get('status', 'unknown')
            for c in status['components'].values()
        ]
        if 'error' in component_statuses:
            status['status'] = 'degraded'

        return jsonify(status)

    except Exception as e:
        log.error(f"Error in /health/detailed: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e),
        }), 500


@health_bp.route('/ready')
def ready():
    """
    Readiness probe.

    Returns 200 when service is ready to accept traffic.
    Used by load balancers and orchestrators.
    """
    # Check if we have essential data loaded
    ready_checks = []

    if _track_store:
        ready_checks.append(True)
    else:
        ready_checks.append(False)

    # Service is ready if all checks pass
    is_ready = all(ready_checks) if ready_checks else True

    if is_ready:
        return jsonify({'ready': True})
    else:
        return jsonify({'ready': False}), 503


@health_bp.route('/live')
def live():
    """
    Liveness probe.

    Returns 200 if service is alive.
    Should not check dependencies - only that the process is responding.
    """
    return jsonify({'alive': True})

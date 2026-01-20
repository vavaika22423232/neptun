"""
API Blueprint for Server-Sent Events (SSE).

Real-time streaming endpoints.
"""
import uuid

from flask import Blueprint, Response, current_app, request

sse_bp = Blueprint('sse', __name__, url_prefix='/api/sse')


@sse_bp.route('/tracks')
def tracks_stream():
    """
    SSE stream for track updates.

    Usage:
        const evtSource = new EventSource('/api/sse/tracks');
        evtSource.addEventListener('track', (e) => {
            const track = JSON.parse(e.data);
            console.log('New track:', track);
        });
    """
    realtime = current_app.extensions.get('realtime')
    if not realtime:
        return Response('Realtime service not configured', status=503)

    subscriber_id = request.args.get('client_id', str(uuid.uuid4()))

    def generate():
        yield from realtime.event_stream(realtime.tracks, subscriber_id)

    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no',  # Disable nginx buffering
        },
    )


@sse_bp.route('/alarms')
def alarms_stream():
    """
    SSE stream for alarm state changes.

    Usage:
        const evtSource = new EventSource('/api/sse/alarms');
        evtSource.addEventListener('alarm', (e) => {
            const alarm = JSON.parse(e.data);
            console.log('Alarm:', alarm);
        });
    """
    realtime = current_app.extensions.get('realtime')
    if not realtime:
        return Response('Realtime service not configured', status=503)

    subscriber_id = request.args.get('client_id', str(uuid.uuid4()))

    def generate():
        yield from realtime.event_stream(realtime.alarms, subscriber_id)

    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no',
        },
    )


@sse_bp.route('/system')
def system_stream():
    """
    SSE stream for system events.

    Includes health status, maintenance notifications, etc.
    """
    realtime = current_app.extensions.get('realtime')
    if not realtime:
        return Response('Realtime service not configured', status=503)

    subscriber_id = request.args.get('client_id', str(uuid.uuid4()))

    def generate():
        yield from realtime.event_stream(realtime.system, subscriber_id)

    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no',
        },
    )


@sse_bp.route('/stats')
def sse_stats():
    """Get SSE channel statistics."""
    realtime = current_app.extensions.get('realtime')
    if not realtime:
        return {'error': 'Realtime service not configured'}, 503

    return realtime.stats()

"""
WebSocket support for real-time updates.

Модуль для real-time оновлень через Server-Sent Events (SSE)
та WebSocket (якщо потрібно).

SSE простіший для односторонньої комунікації (сервер → клієнт).
"""
import json
import queue
import threading
import time
import logging
from datetime import datetime, timezone
from typing import Generator, Dict, Any, Optional, List, Callable
from dataclasses import dataclass

from domain.models import Track

log = logging.getLogger(__name__)


@dataclass
class Event:
    """Server-sent event."""
    event_type: str
    data: Dict[str, Any]
    timestamp: datetime
    id: Optional[str] = None


class SSEChannel:
    """
    Server-Sent Events channel.
    
    Керує підписниками та розсилкою подій.
    Thread-safe.
    """
    
    def __init__(self, max_queue_size: int = 100):
        self._subscribers: Dict[str, queue.Queue] = {}
        self._lock = threading.Lock()
        self._max_queue_size = max_queue_size
        self._event_counter = 0
        
        # Stats
        self._total_events = 0
        self._total_subscribers = 0
    
    def subscribe(self, subscriber_id: str) -> queue.Queue:
        """
        Subscribe to events.
        
        Returns:
            Queue to receive events from
        """
        with self._lock:
            if subscriber_id in self._subscribers:
                # Already subscribed, return existing queue
                return self._subscribers[subscriber_id]
            
            q = queue.Queue(maxsize=self._max_queue_size)
            self._subscribers[subscriber_id] = q
            self._total_subscribers += 1
            log.debug(f"New subscriber: {subscriber_id}, total: {len(self._subscribers)}")
            return q
    
    def unsubscribe(self, subscriber_id: str) -> None:
        """Unsubscribe from events."""
        with self._lock:
            if subscriber_id in self._subscribers:
                del self._subscribers[subscriber_id]
                log.debug(f"Unsubscribed: {subscriber_id}, total: {len(self._subscribers)}")
    
    def publish(self, event_type: str, data: Dict[str, Any]) -> None:
        """
        Publish event to all subscribers.
        
        Drops messages if queue is full (non-blocking).
        """
        self._event_counter += 1
        event = Event(
            event_type=event_type,
            data=data,
            timestamp=datetime.now(timezone.utc),
            id=str(self._event_counter),
        )
        
        with self._lock:
            self._total_events += 1
            dead_subscribers = []
            
            for sub_id, q in self._subscribers.items():
                try:
                    q.put_nowait(event)
                except queue.Full:
                    # Queue full, subscriber too slow
                    log.warning(f"Queue full for subscriber {sub_id}")
                    dead_subscribers.append(sub_id)
            
            # Remove dead subscribers
            for sub_id in dead_subscribers:
                del self._subscribers[sub_id]
    
    def subscriber_count(self) -> int:
        """Get current subscriber count."""
        with self._lock:
            return len(self._subscribers)
    
    def stats(self) -> Dict[str, Any]:
        """Get channel statistics."""
        return {
            'current_subscribers': self.subscriber_count(),
            'total_subscribers': self._total_subscribers,
            'total_events': self._total_events,
            'event_counter': self._event_counter,
        }


class RealtimeService:
    """
    Service for real-time updates.
    
    Координує SSE канали та нотифікації.
    """
    
    def __init__(self):
        # Channels for different event types
        self._tracks_channel = SSEChannel()
        self._alarms_channel = SSEChannel()
        self._system_channel = SSEChannel()
        
        # Keep-alive interval
        self._keepalive_interval = 30  # seconds
    
    @property
    def tracks(self) -> SSEChannel:
        return self._tracks_channel
    
    @property
    def alarms(self) -> SSEChannel:
        return self._alarms_channel
    
    @property
    def system(self) -> SSEChannel:
        return self._system_channel
    
    def publish_track(self, track: Track) -> None:
        """Publish new track event."""
        self._tracks_channel.publish('track', {
            'id': track.id,
            'coordinates': {
                'lat': track.coordinates.lat,
                'lng': track.coordinates.lon,
            },
            'threat_type': track.threat_type.type_id,
            'timestamp': track.timestamp.isoformat(),
            'location': track.place,
            'direction': track.course_direction,
        })
    
    def publish_alarm(self, region_id: str, is_active: bool, alarm_type: str = 'air') -> None:
        """Publish alarm state change."""
        self._alarms_channel.publish('alarm', {
            'region_id': region_id,
            'is_active': is_active,
            'alarm_type': alarm_type,
            'timestamp': datetime.now(timezone.utc).isoformat(),
        })
    
    def publish_system(self, event_type: str, data: Dict[str, Any]) -> None:
        """Publish system event."""
        self._system_channel.publish(event_type, data)
    
    def event_stream(
        self,
        channel: SSEChannel,
        subscriber_id: str,
    ) -> Generator[str, None, None]:
        """
        Generate SSE event stream.
        
        Yields:
            Formatted SSE messages
        """
        q = channel.subscribe(subscriber_id)
        last_keepalive = time.time()
        
        try:
            while True:
                try:
                    # Wait for event with timeout
                    event = q.get(timeout=self._keepalive_interval)
                    
                    # Format as SSE
                    yield self._format_sse(event)
                    
                except queue.Empty:
                    # Send keepalive
                    if time.time() - last_keepalive >= self._keepalive_interval:
                        yield ": keepalive\n\n"
                        last_keepalive = time.time()
                        
        finally:
            channel.unsubscribe(subscriber_id)
    
    def _format_sse(self, event: Event) -> str:
        """Format event as SSE message."""
        lines = []
        
        if event.id:
            lines.append(f"id: {event.id}")
        
        lines.append(f"event: {event.event_type}")
        lines.append(f"data: {json.dumps(event.data)}")
        
        return "\n".join(lines) + "\n\n"
    
    def stats(self) -> Dict[str, Any]:
        """Get realtime service statistics."""
        return {
            'tracks_channel': self._tracks_channel.stats(),
            'alarms_channel': self._alarms_channel.stats(),
            'system_channel': self._system_channel.stats(),
        }


def create_marker_callback(realtime: RealtimeService) -> Callable[[Track], None]:
    """Create callback function for publishing tracks to realtime service."""
    def callback(track: Track) -> None:
        realtime.publish_track(track)
    return callback

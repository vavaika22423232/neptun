"""
Message processing pipeline.

Центральний модуль для обробки повідомлень з Telegram.
Координує парсинг, геокодинг та збереження.
"""
import logging
import threading
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from domain.models import Coordinates, Track, TrackStatus
from domain.threat_types import ThreatType
from services.geocoding.base import GeocoderInterface
from services.telegram.parser import MessageParser, ParsedMessage
from services.tracks.store import TrackStore
from utils.threading import AtomicValue, ThreadSafeDict

# Alias for compatibility
Marker = Track

log = logging.getLogger(__name__)


@dataclass
class ProcessingResult:
    """Result of processing a single message."""
    message_id: int
    channel_id: int
    success: bool
    markers_created: int = 0
    error: Optional[str] = None


class MessagePipeline:
    """
    Pipeline for processing Telegram messages.

    Потік обробки:
    1. Отримання сирих повідомлень
    2. Парсинг через MessageParser
    3. Геокодинг локацій
    4. Створення маркерів
    5. Збереження в TrackStore
    6. Нотифікації (callbacks)

    Thread-safe для конкурентного доступу.
    """

    def __init__(
        self,
        parser: MessageParser,
        geocoder: GeocoderInterface,
        track_store: TrackStore,
        max_history: int = 1000,
    ):
        self._parser = parser
        self._geocoder = geocoder
        self._track_store = track_store
        self._max_history = max_history

        # Callbacks for new markers
        self._callbacks: list[Callable[[Marker], None]] = []
        self._lock = threading.Lock()

        # Processing history (для дедуплікації)
        self._processed_ids: deque = deque(maxlen=max_history)

        # Stats
        self._total_processed = AtomicValue(0)
        self._total_markers = AtomicValue(0)
        self._total_errors = AtomicValue(0)
        self._last_process_time = AtomicValue(None)

        # Per-channel stats
        self._channel_stats: ThreadSafeDict[int, dict] = ThreadSafeDict()

    def add_callback(self, callback: Callable[[Marker], None]) -> None:
        """Add callback for new markers."""
        with self._lock:
            self._callbacks.append(callback)

    def remove_callback(self, callback: Callable[[Marker], None]) -> None:
        """Remove callback."""
        with self._lock:
            if callback in self._callbacks:
                self._callbacks.remove(callback)

    def _notify_callbacks(self, marker: Marker) -> None:
        """Notify all callbacks about new marker."""
        with self._lock:
            callbacks = list(self._callbacks)

        for callback in callbacks:
            try:
                callback(marker)
            except Exception as e:
                log.warning(f"Callback error: {e}")

    def process_message(
        self,
        message_id: int,
        channel_id: int,
        text: str,
        timestamp: Optional[datetime] = None,
        media_info: Optional[dict[str, Any]] = None,
    ) -> ProcessingResult:
        """
        Process a single message.

        Returns:
            ProcessingResult with status and created markers count
        """
        # Check if already processed
        msg_key = (channel_id, message_id)
        if msg_key in self._processed_ids:
            return ProcessingResult(
                message_id=message_id,
                channel_id=channel_id,
                success=True,
                markers_created=0,
            )

        try:
            # Parse message
            parsed = self._parser.parse(text, channel_id)

            if not parsed.locations and not parsed.threat_types:
                # Nothing to process
                self._processed_ids.append(msg_key)
                return ProcessingResult(
                    message_id=message_id,
                    channel_id=channel_id,
                    success=True,
                    markers_created=0,
                )

            markers_created = 0

            # Process each location
            for location in parsed.locations:
                marker = self._create_marker(
                    location=location,
                    parsed=parsed,
                    message_id=message_id,
                    channel_id=channel_id,
                    timestamp=timestamp,
                    media_info=media_info,
                )

                if marker:
                    # Store and notify
                    self._track_store.add(marker)
                    self._notify_callbacks(marker)
                    markers_created += 1

            # Update stats
            self._total_processed.set(self._total_processed.get() + 1)
            self._total_markers.set(self._total_markers.get() + markers_created)
            self._last_process_time.set(datetime.now(timezone.utc))
            self._update_channel_stats(channel_id, markers_created)

            # Mark as processed
            self._processed_ids.append(msg_key)

            return ProcessingResult(
                message_id=message_id,
                channel_id=channel_id,
                success=True,
                markers_created=markers_created,
            )

        except Exception as e:
            log.error(f"Error processing message {message_id}: {e}")
            self._total_errors.set(self._total_errors.get() + 1)

            return ProcessingResult(
                message_id=message_id,
                channel_id=channel_id,
                success=False,
                error=str(e),
            )

    def _create_marker(
        self,
        location: str,
        parsed: ParsedMessage,
        message_id: int,
        channel_id: int,
        timestamp: Optional[datetime],
        media_info: Optional[dict[str, Any]],
    ) -> Optional[Marker]:
        """Create marker from parsed data with geocoding."""
        # Extract region if available
        region = None
        if parsed.regions:
            region = parsed.regions[0]

        # Try to geocode
        result = self._geocoder.geocode(location, region)

        if not result:
            log.debug(f"Could not geocode: {location}")
            return None

        # Determine threat type
        threat_type = ThreatType.UNKNOWN
        if parsed.threat_types:
            threat_type = parsed.threat_types[0]

        # Get timestamp
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)

        # Create unique ID
        marker_id = f"{channel_id}_{message_id}_{location[:20]}"

        # Create marker (Track)
        return Track(
            id=marker_id,
            threat_type=threat_type,
            coordinates=Coordinates(
                lat=result.coordinates[0],
                lon=result.coordinates[1],
            ),
            place=result.place_name or location,
            text=parsed.raw_text[:500] if parsed.raw_text else '',
            timestamp=timestamp,
            source_channel=f"channel_{channel_id}",
            course_direction=parsed.direction,
            status=TrackStatus.ACTIVE,
        )

    def _update_channel_stats(self, channel_id: int, markers: int) -> None:
        """Update per-channel statistics."""
        stats = self._channel_stats.get(channel_id)
        if stats is None:
            stats = {
                'messages': 0,
                'markers': 0,
                'last_message': None,
            }

        stats['messages'] += 1
        stats['markers'] += markers
        stats['last_message'] = datetime.now(timezone.utc).isoformat()

        self._channel_stats.set(channel_id, stats)

    def process_batch(
        self,
        messages: list[dict[str, Any]],
    ) -> list[ProcessingResult]:
        """
        Process multiple messages.

        Args:
            messages: List of dicts with keys:
                - message_id: int
                - channel_id: int
                - text: str
                - timestamp: Optional[datetime]
                - media_info: Optional[dict]

        Returns:
            List of ProcessingResults
        """
        results = []

        for msg in messages:
            result = self.process_message(
                message_id=msg['message_id'],
                channel_id=msg['channel_id'],
                text=msg.get('text', ''),
                timestamp=msg.get('timestamp'),
                media_info=msg.get('media_info'),
            )
            results.append(result)

        return results

    def stats(self) -> dict[str, Any]:
        """Get pipeline statistics."""
        last_time = self._last_process_time.get()

        return {
            'total_processed': self._total_processed.get(),
            'total_markers': self._total_markers.get(),
            'total_errors': self._total_errors.get(),
            'last_process_time': last_time.isoformat() if last_time else None,
            'processed_ids_count': len(self._processed_ids),
            'callbacks_count': len(self._callbacks),
            'channel_stats': dict(self._channel_stats.items()),
        }

    def clear_history(self) -> None:
        """Clear processing history."""
        self._processed_ids.clear()


class PipelineBuilder:
    """Builder for MessagePipeline with default configurations."""

    def __init__(self):
        self._parser: Optional[MessageParser] = None
        self._geocoder: Optional[GeocoderInterface] = None
        self._track_store: Optional[TrackStore] = None
        self._max_history: int = 1000
        self._callbacks: list[Callable] = []

    def with_parser(self, parser: MessageParser) -> 'PipelineBuilder':
        self._parser = parser
        return self

    def with_geocoder(self, geocoder: GeocoderInterface) -> 'PipelineBuilder':
        self._geocoder = geocoder
        return self

    def with_track_store(self, store: TrackStore) -> 'PipelineBuilder':
        self._track_store = store
        return self

    def with_max_history(self, max_history: int) -> 'PipelineBuilder':
        self._max_history = max_history
        return self

    def with_callback(self, callback: Callable[[Marker], None]) -> 'PipelineBuilder':
        self._callbacks.append(callback)
        return self

    def build(self) -> MessagePipeline:
        if self._parser is None:
            raise ValueError("Parser is required")
        if self._geocoder is None:
            raise ValueError("Geocoder is required")
        if self._track_store is None:
            raise ValueError("TrackStore is required")

        pipeline = MessagePipeline(
            parser=self._parser,
            geocoder=self._geocoder,
            track_store=self._track_store,
            max_history=self._max_history,
        )

        for callback in self._callbacks:
            pipeline.add_callback(callback)

        return pipeline

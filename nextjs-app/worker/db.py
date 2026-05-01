"""
Lightweight in-memory database for the worker.

The worker runs on the VPS as a separate service WITHOUT Redis.
It only needs deduplication (to avoid processing the same Telegram message twice).
Actual marker persistence goes through POST /api/ingest on the web service.

Deduplication uses an in-memory set with automatic cleanup to avoid unbounded growth.
"""

import logging
import time
import threading
import hashlib

log = logging.getLogger(__name__)

# Max dedup entries before cleanup (oldest half gets dropped)
MAX_DEDUP_SIZE = 10_000
# How long to remember a processed message (seconds)
DEDUP_TTL = 3600 * 6  # 6 hours


class InMemoryDB:
    """Drop-in replacement for the Redis-backed Database class."""

    def __init__(self) -> None:
        self._processed: dict[str, float] = {}  # key → timestamp
        self._lock = threading.Lock()
        log.info("In-memory DB initialized (no Redis required)")

    def is_connected(self) -> bool:
        return True  # always "connected"

    # ── Deduplication ─────────────────────────────────────────────────────

    def is_message_processed(self, channel_id: int, msg_id: int) -> bool:
        key = f"{channel_id}:{msg_id}"
        with self._lock:
            ts = self._processed.get(key)
            if ts is None:
                return False
            # Expired?
            if time.time() - ts > DEDUP_TTL:
                del self._processed[key]
                return False
            return True

    def is_message_content_processed(self, channel_id: int, msg_id: int, text: str) -> bool:
        """Return True when the exact current content for this Telegram message was already handled."""
        digest = hashlib.sha1((text or '').strip().encode('utf-8')).hexdigest()[:16]
        key = f"{channel_id}:{msg_id}:content:{digest}"
        with self._lock:
            ts = self._processed.get(key)
            if ts is None:
                return False
            if time.time() - ts > DEDUP_TTL:
                del self._processed[key]
                return False
            return True

    def mark_message_processed(self, channel_id: int, msg_id: int) -> None:
        key = f"{channel_id}:{msg_id}"
        with self._lock:
            self._processed[key] = time.time()
            # Cleanup if too large
            if len(self._processed) > MAX_DEDUP_SIZE:
                self._cleanup()

    def mark_message_content_processed(self, channel_id: int, msg_id: int, text: str) -> None:
        """Remember the exact text version of a message, including edited messages."""
        digest = hashlib.sha1((text or '').strip().encode('utf-8')).hexdigest()[:16]
        key = f"{channel_id}:{msg_id}:content:{digest}"
        with self._lock:
            self._processed[key] = time.time()
            if len(self._processed) > MAX_DEDUP_SIZE:
                self._cleanup()

    def _cleanup(self) -> None:
        """Remove oldest half of entries."""
        items = sorted(self._processed.items(), key=lambda x: x[1])
        cutoff = len(items) // 2
        for k, _ in items[:cutoff]:
            del self._processed[k]
        log.info(f"Dedup cleanup: removed {cutoff} old entries, {len(self._processed)} remaining")

    # ── Threat storage (no-ops — persistence goes via /api/ingest) ────────

    def save_threat(self, threat_id: str, data: dict, ttl: int = 3600) -> None:
        """No-op: markers are persisted via HTTP POST to /api/ingest."""
        pass

    def publish_update(self, channel: str, data: dict) -> None:
        """No-op: real-time updates not supported without Redis pub/sub."""
        pass


# Singleton instance
db = InMemoryDB()

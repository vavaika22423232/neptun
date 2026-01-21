"""
Thread-safe track storage.

Зберігає треки загроз з автоматичним видаленням застарілих,
резервним копіюванням та відновленням.
"""
import json
import os
import threading
import time
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Optional


def utcnow() -> datetime:
    """Get current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


@dataclass
class TrackEntry:
    """Single track entry."""
    id: str
    text: str
    timestamp: datetime
    channel: Optional[str] = None

    # Geocoded data
    lat: Optional[float] = None
    lng: Optional[float] = None
    place: Optional[str] = None
    oblast: Optional[str] = None

    # Threat info
    threat_type: Optional[str] = None
    count: int = 1
    is_all_clear: bool = False

    # Course info
    source: Optional[str] = None
    target: Optional[str] = None
    direction: Optional[str] = None

    # Metadata
    geocoded: bool = False
    manual: bool = False  # Manual entries survive pruning
    hidden: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            'id': self.id,
            'text': self.text,
            'date': self.timestamp.strftime('%Y-%m-%d %H:%M:%S') if self.timestamp else None,
            'channel': self.channel,
            'lat': self.lat,
            'lng': self.lng,
            'place': self.place,
            'oblast': self.oblast,
            'threat_type': self.threat_type,
            'count': self.count,
            'is_all_clear': self.is_all_clear,
            'source': self.source,
            'target': self.target,
            'direction': self.direction,
            'geocoded': self.geocoded,
            'manual': self.manual,
            'hidden': self.hidden,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'TrackEntry':
        """Create from dict."""
        # Parse timestamp
        ts = data.get('date') or data.get('timestamp')
        if isinstance(ts, str):
            try:
                ts = datetime.strptime(ts, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                ts = utcnow()
        elif not isinstance(ts, datetime):
            ts = utcnow()

        return cls(
            id=data.get('id', ''),
            text=data.get('text') or data.get('message', ''),
            timestamp=ts,
            channel=data.get('channel'),
            lat=data.get('lat'),
            lng=data.get('lng'),
            place=data.get('place') or data.get('location'),
            oblast=data.get('oblast'),
            threat_type=data.get('threat_type') or data.get('type'),
            count=data.get('count', 1),
            is_all_clear=data.get('is_all_clear', False),
            source=data.get('source'),
            target=data.get('target'),
            direction=data.get('direction'),
            geocoded=data.get('geocoded', False),
            manual=data.get('manual', False),
            hidden=data.get('hidden', False),
        )


class TrackStore:
    """
    Thread-safe storage for track entries.

    Features:
    - Automatic TTL-based pruning
    - Max count limiting
    - Persistent file storage with atomic writes
    - Backup rotation
    - Manual entries preserved
    """

    def __init__(
        self,
        file_path: str,
        retention_minutes: int = 1440,  # 24 hours
        max_count: int = 500,
        backup_count: int = 3,
        auto_save_interval: float = 60.0,  # seconds
    ):
        self._file_path = file_path
        self._retention_minutes = retention_minutes
        self._max_count = max_count
        self._backup_count = backup_count
        self._auto_save_interval = auto_save_interval

        self._tracks: dict[str, TrackEntry] = {}
        self._lock = threading.RLock()
        self._dirty = False
        self._last_save = time.time()

        # Load from file
        self._load()

    def add(self, entry: TrackEntry) -> bool:
        """
        Add a track entry.

        Returns:
            True if added, False if duplicate
        """
        with self._lock:
            if entry.id in self._tracks:
                return False

            self._tracks[entry.id] = entry
            self._dirty = True

            # Enforce max count
            if len(self._tracks) > self._max_count:
                self._enforce_max_count_locked()

            self._maybe_auto_save()
            return True

    def _enforce_max_count_locked(self) -> None:
        """Enforce max count limit. Call with lock held."""
        if len(self._tracks) <= self._max_count:
            return

        # Separate manual and auto
        manual = {k: v for k, v in self._tracks.items() if v.manual}
        auto = {k: v for k, v in self._tracks.items() if not v.manual}

        # How many auto can we keep?
        auto_limit = max(0, self._max_count - len(manual))

        if len(auto) > auto_limit:
            # Sort by timestamp, keep newest
            sorted_auto = sorted(
                auto.items(),
                key=lambda x: x[1].timestamp if x[1].timestamp else utcnow(),
                reverse=True
            )

            # Remove oldest
            for track_id, _ in sorted_auto[auto_limit:]:
                del self._tracks[track_id]

    def add_batch(self, entries: list[TrackEntry]) -> int:
        """
        Add multiple entries.

        Returns:
            Count of entries actually added (not duplicates)
        """
        added = 0
        with self._lock:
            for entry in entries:
                if entry.id not in self._tracks:
                    self._tracks[entry.id] = entry
                    added += 1

            if added > 0:
                self._dirty = True
                self._maybe_auto_save()

        return added

    def get(self, track_id: str) -> Optional[TrackEntry]:
        """Get track by ID."""
        with self._lock:
            return deepcopy(self._tracks.get(track_id))

    def get_all(self, include_hidden: bool = False) -> list[TrackEntry]:
        """
        Get all tracks.

        Args:
            include_hidden: Include hidden tracks

        Returns:
            List of track entries (copies)
        """
        with self._lock:
            tracks = list(self._tracks.values())
            if not include_hidden:
                tracks = [t for t in tracks if not t.hidden]
            return [deepcopy(t) for t in tracks]

    def get_recent(
        self,
        minutes: int = 60,
        include_hidden: bool = False,
        limit: Optional[int] = None,
        since: Optional[datetime] = None,
    ) -> list[TrackEntry]:
        """
        Get tracks from last N minutes.

        Args:
            minutes: Time window (ignored if since is provided)
            include_hidden: Include hidden tracks
            limit: Maximum number of results
            since: Cutoff timestamp (overrides minutes)
        """
        if since:
            cutoff = since
        else:
            cutoff = utcnow() - timedelta(minutes=minutes)

        with self._lock:
            tracks = []
            for t in self._tracks.values():
                if t.timestamp and t.timestamp >= cutoff:
                    if include_hidden or not t.hidden:
                        tracks.append(deepcopy(t))

            sorted_tracks = sorted(tracks, key=lambda x: x.timestamp, reverse=True)

            if limit:
                return sorted_tracks[:limit]
            return sorted_tracks

    def get_by_oblast(self, oblast: str) -> list[TrackEntry]:
        """Get all tracks for an oblast."""
        oblast_lower = oblast.lower()

        with self._lock:
            return [
                deepcopy(t) for t in self._tracks.values()
                if t.oblast and oblast_lower in t.oblast.lower()
            ]

    def get_ungeocodeded(self) -> list[TrackEntry]:
        """Get tracks that need geocoding."""
        with self._lock:
            return [
                deepcopy(t) for t in self._tracks.values()
                if not t.geocoded and t.lat is None and not t.is_all_clear
            ]

    def update(self, track_id: str, **kwargs) -> bool:
        """
        Update track fields.

        Args:
            track_id: Track to update
            **kwargs: Fields to update (lat, lng, place, etc.)

        Returns:
            True if updated, False if not found
        """
        with self._lock:
            track = self._tracks.get(track_id)
            if not track:
                return False

            for key, value in kwargs.items():
                if hasattr(track, key):
                    setattr(track, key, value)

            self._dirty = True
            return True

    def hide(self, track_id: str) -> bool:
        """Hide a track (soft delete)."""
        return self.update(track_id, hidden=True)

    def unhide(self, track_id: str) -> bool:
        """Unhide a track."""
        return self.update(track_id, hidden=False)

    def remove(self, track_id: str) -> bool:
        """
        Remove a track (hard delete).

        Returns:
            True if removed
        """
        with self._lock:
            if track_id in self._tracks:
                del self._tracks[track_id]
                self._dirty = True
                return True
            return False

    def prune(self) -> int:
        """
        Remove expired tracks.

        Returns:
            Count of removed tracks
        """
        cutoff = utcnow() - timedelta(minutes=self._retention_minutes)

        with self._lock:
            # Find expired (but preserve manual)
            to_remove = []
            for track_id, track in self._tracks.items():
                # Make timestamp timezone-aware if naive
                ts = track.timestamp
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                if ts < cutoff and not track.manual:
                    to_remove.append(track_id)

            for track_id in to_remove:
                del self._tracks[track_id]

            # Enforce max count
            if len(self._tracks) > self._max_count:
                # Separate manual and auto
                manual = {k: v for k, v in self._tracks.items() if v.manual}
                auto = {k: v for k, v in self._tracks.items() if not v.manual}

                # How many auto can we keep?
                auto_limit = max(0, self._max_count - len(manual))

                if len(auto) > auto_limit:
                    # Sort by timestamp, keep newest
                    sorted_auto = sorted(
                        auto.items(),
                        key=lambda x: x[1].timestamp,
                        reverse=True
                    )

                    # Remove oldest
                    for track_id, _ in sorted_auto[auto_limit:]:
                        del self._tracks[track_id]
                        to_remove.append(track_id)

            if to_remove:
                self._dirty = True

            return len(to_remove)

    def count(self, include_hidden: bool = True) -> int:
        """Get track count."""
        with self._lock:
            if include_hidden:
                return len(self._tracks)
            return sum(1 for t in self._tracks.values() if not t.hidden)

    def save(self, force: bool = False) -> bool:
        """
        Save to file.

        Args:
            force: Save even if not dirty

        Returns:
            True if saved
        """
        with self._lock:
            if not force and not self._dirty:
                return False

            # Prepare data
            data = [track.to_dict() for track in self._tracks.values()]

            # Atomic write with backup
            try:
                self._rotate_backups()

                # Write to temp file first
                temp_path = self._file_path + '.tmp'
                with open(temp_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)

                # Atomic rename
                os.replace(temp_path, self._file_path)

                self._dirty = False
                self._last_save = time.time()
                return True

            except Exception as e:
                # Clean up temp file
                try:
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                except Exception:
                    pass
                raise e

    def _load(self) -> None:
        """Load from file."""
        if not os.path.exists(self._file_path):
            return

        try:
            with open(self._file_path, encoding='utf-8') as f:
                data = json.load(f)

            for item in data:
                try:
                    entry = TrackEntry.from_dict(item)
                    if entry.id:
                        self._tracks[entry.id] = entry
                except Exception:
                    continue  # Skip malformed entries

        except json.JSONDecodeError:
            # Try loading from backup
            self._load_from_backup()
        except Exception:
            pass

    def _load_from_backup(self) -> None:
        """Try to load from backup files."""
        for i in range(1, self._backup_count + 1):
            backup_path = f"{self._file_path}.bak{i}"
            if not os.path.exists(backup_path):
                continue

            try:
                with open(backup_path, encoding='utf-8') as f:
                    data = json.load(f)

                for item in data:
                    try:
                        entry = TrackEntry.from_dict(item)
                        if entry.id:
                            self._tracks[entry.id] = entry
                    except Exception:
                        continue

                # Successfully loaded from backup
                return

            except Exception:
                continue

    def _rotate_backups(self) -> None:
        """Rotate backup files."""
        if not os.path.exists(self._file_path):
            return

        # Rotate existing backups
        for i in range(self._backup_count, 0, -1):
            old_path = f"{self._file_path}.bak{i-1}" if i > 1 else self._file_path
            new_path = f"{self._file_path}.bak{i}"

            if os.path.exists(old_path):
                try:
                    if i == 1:
                        # Copy main file to .bak1
                        import shutil
                        shutil.copy2(old_path, new_path)
                    else:
                        # Rename .bak(i-1) to .bak(i)
                        os.replace(old_path, new_path)
                except Exception:
                    pass

    def _maybe_auto_save(self) -> None:
        """Save if enough time has passed."""
        if time.time() - self._last_save > self._auto_save_interval:
            try:
                self.save()
            except Exception:
                pass  # Will retry on next operation

    def stats(self) -> dict[str, Any]:
        """
        Get statistics about stored tracks.

        Returns:
            Dict with count, by_type breakdown, by_oblast breakdown
        """
        with self._lock:
            visible = [t for t in self._tracks.values() if not t.hidden]

            # Count by type
            by_type: dict[str, int] = {}
            for track in visible:
                ttype = track.threat_type or 'unknown'
                by_type[ttype] = by_type.get(ttype, 0) + 1

            # Count by oblast
            by_oblast: dict[str, int] = {}
            for track in visible:
                oblast = track.oblast or 'unknown'
                by_oblast[oblast] = by_oblast.get(oblast, 0) + 1

            return {
                'count': len(visible),
                'by_type': by_type,
                'by_oblast': by_oblast,
                'total': len(self._tracks),
                'hidden': len(self._tracks) - len(visible),
            }

    def get_active(self, since: datetime) -> list[TrackEntry]:
        """
        Get active tracks since given timestamp.

        Args:
            since: Cutoff timestamp

        Returns:
            List of tracks newer than since
        """
        with self._lock:
            tracks = []
            for t in self._tracks.values():
                if t.timestamp and t.timestamp >= since and not t.hidden:
                    tracks.append(deepcopy(t))

            return sorted(tracks, key=lambda x: x.timestamp, reverse=True)

    def to_api_format(self, include_hidden: bool = False) -> list[dict[str, Any]]:
        """
        Convert all tracks to API response format.

        Compatible with existing /data endpoint format.
        """
        tracks = self.get_all(include_hidden=include_hidden)

        result = []
        for track in tracks:
            if track.lat is not None and track.lng is not None:
                result.append({
                    'id': track.id,
                    'lat': track.lat,
                    'lng': track.lng,
                    'place': track.place or '',
                    'text': track.text[:500] if track.text else '',
                    'date': track.timestamp.strftime('%Y-%m-%d %H:%M:%S') if track.timestamp else '',
                    'type': track.threat_type or 'unknown',
                    'channel': track.channel or '',
                    'oblast': track.oblast or '',
                    'source': track.source,
                    'target': track.target,
                    'direction': track.direction,
                    'count': track.count,
                    'manual': track.manual,
                })

        return result

"""
Track processor - geocoding and enrichment.

Обробляє треки: геокодинг локацій, визначення напрямків,
об'єднання дублікатів тощо.
"""
import time
import threading
import logging
from typing import Optional, List, Dict, Any, Callable
from datetime import datetime

from services.tracks.store import TrackStore, TrackEntry
from services.geocoding.chain import GeocoderChain

log = logging.getLogger(__name__)


class TrackProcessor:
    """
    Background track processor.
    
    Features:
    - Async geocoding of new tracks
    - Rate limiting to avoid API throttling
    - Batch processing for efficiency
    - Thread-safe operation
    """
    
    def __init__(
        self,
        store: TrackStore,
        geocoder: Optional[GeocoderChain] = None,
        batch_size: int = 10,
        batch_delay: float = 2.0,  # seconds between batches
        geocode_delay: float = 0.5,  # seconds between individual geocodes
    ):
        self._store = store
        self._geocoder = geocoder
        self._batch_size = batch_size
        self._batch_delay = batch_delay
        self._geocode_delay = geocode_delay
        
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        
        # Stats
        self._processed_count = 0
        self._geocoded_count = 0
        self._failed_count = 0
        self._last_process_time: Optional[float] = None
    
    def start(self) -> None:
        """Start background processing thread."""
        with self._lock:
            if self._running:
                return
            
            self._running = True
            self._thread = threading.Thread(
                target=self._process_loop,
                daemon=True,
                name='TrackProcessor',
            )
            self._thread.start()
            log.info("TrackProcessor started")
    
    def stop(self) -> None:
        """Stop background processing."""
        with self._lock:
            self._running = False
        
        if self._thread:
            self._thread.join(timeout=5.0)
            self._thread = None
        
        log.info("TrackProcessor stopped")
    
    def process_now(self, max_items: int = 50) -> int:
        """
        Process ungeocodeded tracks synchronously.
        
        Args:
            max_items: Maximum items to process
            
        Returns:
            Count of successfully geocoded tracks
        """
        if not self._geocoder:
            log.warning("No geocoder configured, skipping")
            return 0
        
        ungeocodeded = self._store.get_ungeocodeded()
        if not ungeocodeded:
            return 0
        
        # Limit batch
        to_process = ungeocodeded[:max_items]
        geocoded = 0
        
        for track in to_process:
            success = self._geocode_track(track)
            if success:
                geocoded += 1
            
            # Rate limiting
            time.sleep(self._geocode_delay)
        
        return geocoded
    
    def add_and_process(self, entry: TrackEntry) -> bool:
        """
        Add track and immediately try to geocode.
        
        Returns:
            True if geocoded successfully
        """
        # Add to store
        added = self._store.add(entry)
        if not added:
            return False
        
        # Try to geocode immediately
        if self._geocoder and not entry.geocoded:
            return self._geocode_track(entry)
        
        return False
    
    def stats(self) -> Dict[str, Any]:
        """Get processing statistics."""
        return {
            'processed': self._processed_count,
            'geocoded': self._geocoded_count,
            'failed': self._failed_count,
            'pending': len(self._store.get_ungeocodeded()),
            'last_process': self._last_process_time,
            'running': self._running,
        }
    
    def is_running(self) -> bool:
        """Check if processor is running."""
        return self._running
    
    def add_pending(self, entry: TrackEntry) -> bool:
        """
        Add track to pending queue for later geocoding.
        
        Args:
            entry: Track entry to add
            
        Returns:
            True if added successfully
        """
        # Simply add to store - it will be picked up by background processor
        return self._store.add(entry)
    
    def _process_loop(self) -> None:
        """Background processing loop."""
        while self._running:
            try:
                processed = self.process_now(max_items=self._batch_size)
                
                if processed > 0:
                    self._last_process_time = time.time()
                    # Save after processing batch
                    try:
                        self._store.save()
                    except Exception as e:
                        log.warning(f"Failed to save after processing: {e}")
                
                # Wait before next batch
                time.sleep(self._batch_delay)
                
            except Exception as e:
                log.error(f"TrackProcessor error: {e}")
                time.sleep(5.0)  # Longer delay on error
    
    def _geocode_track(self, track: TrackEntry) -> bool:
        """
        Geocode a single track.
        
        Args:
            track: Track to geocode
            
        Returns:
            True if successfully geocoded
        """
        if not self._geocoder:
            return False
        
        self._processed_count += 1
        
        # Build query from available location info
        query = self._build_query(track)
        if not query:
            log.debug(f"No geocode query for track {track.id}")
            self._failed_count += 1
            return False
        
        # Try geocoding
        result = self._geocoder.geocode(query, region=track.oblast)
        
        if result and result.coordinates:
            # Update track
            self._store.update(
                track.id,
                lat=result.coordinates[0],
                lng=result.coordinates[1],
                place=result.place_name or query,
                geocoded=True,
            )
            self._geocoded_count += 1
            log.debug(f"Geocoded track {track.id}: {result.coordinates}")
            return True
        else:
            # Mark as attempted (so we don't retry forever)
            self._store.update(track.id, geocoded=True)
            self._failed_count += 1
            log.debug(f"Failed to geocode track {track.id}: {query}")
            return False
    
    def _build_query(self, track: TrackEntry) -> Optional[str]:
        """
        Build geocoding query from track data.
        
        Priority:
        1. Target city (from course)
        2. City (from location)
        3. Place (if already partially geocoded)
        4. District + Oblast
        """
        # Course target has priority (most specific)
        if track.target:
            return track.target
        
        # Source is fallback if no target
        if track.source:
            return track.source
        
        # Direct place/city
        if track.place:
            return track.place
        
        # Try to extract from text
        text = track.text or ''
        
        # Look for city names in text (after "біля", "над", etc.)
        import re
        city_patterns = [
            r'біля\s+([А-ЯІЇЄа-яіїє][а-яіїє\'\-]+)',
            r'над\s+([А-ЯІЇЄа-яіїє][а-яіїє\'\-]+)',
            r'поблизу\s+([А-ЯІЇЄа-яіїє][а-яіїє\'\-]+)',
            r'в\s+район[іу]\s+([А-ЯІЇЄа-яіїє][а-яіїє\'\-]+)',
        ]
        
        for pattern in city_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        # Fall back to district + oblast
        if track.oblast:
            # Use oblast center as fallback
            return track.oblast
        
        return None


class TrackMerger:
    """
    Merge duplicate tracks.
    
    Detects and merges tracks that refer to the same threat
    based on time proximity and location similarity.
    """
    
    def __init__(
        self,
        time_window_seconds: int = 300,  # 5 minutes
        distance_threshold_km: float = 10.0,
    ):
        self._time_window = time_window_seconds
        self._distance_threshold = distance_threshold_km
    
    def find_duplicates(self, tracks: List[TrackEntry]) -> List[List[TrackEntry]]:
        """
        Find groups of duplicate tracks.
        
        Returns:
            List of duplicate groups
        """
        from domain.geo import haversine
        
        # Sort by timestamp
        sorted_tracks = sorted(tracks, key=lambda t: t.timestamp)
        
        groups: List[List[TrackEntry]] = []
        used: set = set()
        
        for i, track1 in enumerate(sorted_tracks):
            if track1.id in used:
                continue
            
            group = [track1]
            used.add(track1.id)
            
            for j in range(i + 1, len(sorted_tracks)):
                track2 = sorted_tracks[j]
                if track2.id in used:
                    continue
                
                # Check time proximity
                time_diff = abs((track2.timestamp - track1.timestamp).total_seconds())
                if time_diff > self._time_window:
                    break  # No more possible duplicates (sorted by time)
                
                # Check same threat type
                if track1.threat_type != track2.threat_type:
                    continue
                
                # Check location proximity (if both have coords)
                if track1.lat and track1.lng and track2.lat and track2.lng:
                    dist = haversine(
                        track1.lat, track1.lng,
                        track2.lat, track2.lng
                    )
                    if dist > self._distance_threshold:
                        continue
                
                # Consider as duplicate
                group.append(track2)
                used.add(track2.id)
            
            if len(group) > 1:
                groups.append(group)
        
        return groups
    
    def merge_group(self, group: List[TrackEntry]) -> TrackEntry:
        """
        Merge a group of duplicates into single entry.
        
        Keeps the most complete information.
        """
        if not group:
            raise ValueError("Empty group")
        
        if len(group) == 1:
            return group[0]
        
        # Sort by information completeness
        def completeness(t: TrackEntry) -> int:
            score = 0
            if t.lat and t.lng:
                score += 10
            if t.place:
                score += 5
            if t.target:
                score += 3
            if t.source:
                score += 2
            if t.oblast:
                score += 1
            return score
        
        # Use most complete as base
        sorted_group = sorted(group, key=completeness, reverse=True)
        base = sorted_group[0]
        
        # Merge info from others
        for other in sorted_group[1:]:
            if not base.lat and other.lat:
                base.lat = other.lat
                base.lng = other.lng
            if not base.place and other.place:
                base.place = other.place
            if not base.target and other.target:
                base.target = other.target
            if not base.source and other.source:
                base.source = other.source
            if not base.oblast and other.oblast:
                base.oblast = other.oblast
            
            # Sum counts
            base.count = max(base.count, other.count)
        
        return base

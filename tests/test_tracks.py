"""
Tests for track store and processor.
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch
import tempfile
import os
import threading

from services.tracks.store import TrackStore, TrackEntry
from services.tracks.processor import TrackProcessor
from domain.threat_types import ThreatType


class TestTrackEntry:
    """Tests for TrackEntry dataclass."""
    
    def test_create_entry(self):
        entry = TrackEntry(
            id="test_1",
            text="Test message",
            timestamp=datetime.now(timezone.utc),
            lat=50.45,
            lng=30.52,
            place="Київ",
            oblast="Київська",
            threat_type="shahed",
        )
        
        assert entry.id == "test_1"
        assert entry.place == "Київ"
        assert entry.lat == 50.45
    
    def test_entry_to_dict(self):
        now = datetime.now(timezone.utc)
        entry = TrackEntry(
            id="test_1",
            text="Test",
            timestamp=now,
            lat=50.45,
            lng=30.52,
            place="Test",
        )
        
        data = entry.to_dict()
        assert data['id'] == "test_1"
        assert data['lat'] == 50.45
    
    def test_entry_from_dict(self):
        data = {
            'id': 'test_1',
            'text': 'Test message',
            'timestamp': '2024-01-01T12:00:00+00:00',
            'lat': 50.45,
            'lng': 30.52,
            'place': 'Київ',
            'oblast': 'Київська',
            'threat_type': 'shahed',
        }
        
        entry = TrackEntry.from_dict(data)
        assert entry.id == 'test_1'
        assert entry.place == 'Київ'


class TestTrackStore:
    """Tests for TrackStore."""
    
    @pytest.fixture
    def store(self, tmp_path):
        return TrackStore(
            file_path=str(tmp_path / "tracks.json"),
            retention_minutes=60,
            max_count=100,
        )
    
    @pytest.fixture
    def sample_entry(self):
        return TrackEntry(
            id="test_track_1",
            text="Test track message",
            timestamp=datetime.now(timezone.utc),
            lat=50.45,
            lng=30.52,
            place="Київ",
            oblast="Київська",
            threat_type="shahed",
            channel="test_channel",
        )
    
    def test_add_track(self, store, sample_entry):
        store.add(sample_entry)
        assert store.count() == 1
    
    def test_get_track(self, store, sample_entry):
        store.add(sample_entry)
        retrieved = store.get(sample_entry.id)
        
        assert retrieved is not None
        assert retrieved.id == sample_entry.id
        assert retrieved.place == "Київ"
    
    def test_get_nonexistent(self, store):
        result = store.get("nonexistent_id")
        assert result is None
    
    def test_remove_track(self, store, sample_entry):
        store.add(sample_entry)
        assert store.count() == 1
        
        result = store.remove(sample_entry.id)
        assert result is True
        assert store.count() == 0
    
    def test_remove_nonexistent(self, store):
        result = store.remove("nonexistent_id")
        assert result is False
    
    def test_get_all(self, store):
        entries = [
            TrackEntry(
                id=f"track_{i}",
                text=f"Text {i}",
                timestamp=datetime.now(timezone.utc),
                lat=50.0 + i * 0.1,
                lng=30.0 + i * 0.1,
                place=f"Place {i}",
                threat_type="shahed",
            )
            for i in range(5)
        ]
        
        for entry in entries:
            store.add(entry)
        
        all_entries = store.get_all()
        assert len(all_entries) == 5
    
    def test_get_active(self, store):
        now = datetime.now(timezone.utc)
        
        # Add recent track
        recent = TrackEntry(
            id="recent",
            text="Recent",
            timestamp=now,
            lat=50.45,
            lng=30.52,
            place="Recent",
            threat_type="shahed",
        )
        store.add(recent)
        
        # Add old track
        old = TrackEntry(
            id="old",
            text="Old",
            timestamp=now - timedelta(hours=2),
            lat=50.45,
            lng=30.52,
            place="Old",
            threat_type="shahed",
        )
        store.add(old)
        
        # Get active (last hour)
        active = store.get_active(since=now - timedelta(hours=1))
        assert len(active) == 1
        assert active[0].id == "recent"
    
    def test_get_recent(self, store):
        now = datetime.now(timezone.utc)
        
        for i in range(10):
            entry = TrackEntry(
                id=f"track_{i}",
                text=f"Text {i}",
                timestamp=now - timedelta(minutes=i * 10),
                lat=50.0,
                lng=30.0,
                place=f"Place {i}",
            )
            store.add(entry)
        
        # Get recent tracks
        recent = store.get_recent(limit=5)
        assert len(recent) == 5
        # Should be sorted by timestamp (newest first)
        assert recent[0].id == "track_0"
    
    def test_prune_expired(self, store):
        now = datetime.now(timezone.utc)
        
        # Add expired track
        expired = TrackEntry(
            id="expired",
            text="Expired",
            timestamp=now - timedelta(hours=2),  # Older than retention
            lat=50.45,
            lng=30.52,
            place="Expired",
            threat_type="shahed",
        )
        store.add(expired)
        
        # Add fresh track
        fresh = TrackEntry(
            id="fresh",
            text="Fresh",
            timestamp=now,
            lat=50.45,
            lng=30.52,
            place="Fresh",
            threat_type="shahed",
        )
        store.add(fresh)
        
        # Prune
        pruned = store.prune()
        assert pruned >= 1
        assert store.get("fresh") is not None
        assert store.get("expired") is None
    
    def test_max_count_enforcement(self, tmp_path):
        # Create store with small max
        small_store = TrackStore(
            file_path=str(tmp_path / "small.json"),
            retention_minutes=60,
            max_count=5,
        )
        
        # Add more than max
        for i in range(10):
            entry = TrackEntry(
                id=f"track_{i}",
                text=f"Text {i}",
                timestamp=datetime.now(timezone.utc) + timedelta(seconds=i),
                lat=50.0,
                lng=30.0,
                place=f"Place {i}",
            )
            small_store.add(entry)
        
        # Should only keep max_count
        assert small_store.count() <= 5
    
    def test_save_and_load(self, tmp_path):
        file_path = str(tmp_path / "tracks.json")
        
        # Create and populate store
        store1 = TrackStore(file_path=file_path)
        entry = TrackEntry(
            id="persistent",
            text="Test",
            timestamp=datetime.now(timezone.utc),
            lat=50.45,
            lng=30.52,
            place="Test",
            threat_type="shahed",
        )
        store1.add(entry)
        store1.save(force=True)
        
        # Create new store and load
        store2 = TrackStore(file_path=file_path)
        loaded = store2.get("persistent")
        
        assert loaded is not None
        assert loaded.place == "Test"
    
    def test_stats(self, store, sample_entry):
        store.add(sample_entry)
        stats = store.stats()
        
        assert stats['count'] == 1
        assert 'by_type' in stats
        assert 'shahed' in stats['by_type']
        assert stats['by_type']['shahed'] == 1
    
    def test_stats_by_oblast(self, store):
        # Add entries with different oblasts
        for i, oblast in enumerate(['Київська', 'Харківська', 'Київська']):
            entry = TrackEntry(
                id=f"track_{i}",
                text=f"Text {i}",
                timestamp=datetime.now(timezone.utc),
                lat=50.0,
                lng=30.0,
                oblast=oblast,
            )
            store.add(entry)
        
        stats = store.stats()
        assert stats['by_oblast']['Київська'] == 2
        assert stats['by_oblast']['Харківська'] == 1
    
    def test_update_track(self, store, sample_entry):
        store.add(sample_entry)
        
        # Update the track
        store.update(sample_entry.id, place="Updated Place", lat=51.0)
        
        updated = store.get(sample_entry.id)
        assert updated.place == "Updated Place"
        assert updated.lat == 51.0
    
    def test_hide_track(self, store, sample_entry):
        store.add(sample_entry)
        
        # Hide the track
        store.hide(sample_entry.id)
        
        # Should not appear in get_all
        all_entries = store.get_all(include_hidden=False)
        assert len(all_entries) == 0
        
        # But should appear with include_hidden=True
        all_entries = store.get_all(include_hidden=True)
        assert len(all_entries) == 1
    
    def test_thread_safety(self, store):
        """Test concurrent access."""
        errors = []
        
        def add_tracks():
            try:
                for i in range(100):
                    entry = TrackEntry(
                        id=f"thread_{threading.current_thread().name}_{i}",
                        text="Test",
                        timestamp=datetime.now(timezone.utc),
                        lat=50.0,
                        lng=30.0,
                        place="Test",
                    )
                    store.add(entry)
            except Exception as e:
                errors.append(e)
        
        threads = [threading.Thread(target=add_tracks) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert len(errors) == 0
    
    def test_to_api_format(self, store, sample_entry):
        store.add(sample_entry)
        
        api_data = store.to_api_format()
        assert len(api_data) == 1
        
        item = api_data[0]
        assert item['id'] == sample_entry.id
        assert item['lat'] == 50.45
        assert item['lng'] == 30.52
        assert item['place'] == "Київ"


class TestTrackProcessor:
    """Tests for TrackProcessor."""
    
    @pytest.fixture
    def temp_store(self, tmp_path):
        return TrackStore(
            file_path=str(tmp_path / "processor_tracks.json"),
            retention_minutes=60,
        )
    
    @pytest.fixture
    def mock_geocoder(self):
        geocoder = Mock()
        geocoder.geocode.return_value = None
        return geocoder
    
    @pytest.fixture
    def processor(self, temp_store, mock_geocoder):
        return TrackProcessor(
            store=temp_store,
            geocoder=mock_geocoder,
            batch_size=10,
        )
    
    def test_start_stop(self, processor):
        processor.start()
        assert processor.is_running()
        
        processor.stop()
        assert not processor.is_running()
    
    def test_is_running_false_initially(self, processor):
        assert not processor.is_running()
    
    def test_add_pending(self, processor, temp_store):
        entry = TrackEntry(
            id="pending_1",
            text="Test",
            timestamp=datetime.now(timezone.utc),
            lat=None,
            lng=None,
            place="Unknown",
            geocoded=False,
        )
        
        result = processor.add_pending(entry)
        assert result is True
        
        # Should be in store
        assert temp_store.get("pending_1") is not None
    
    def test_stats(self, processor):
        stats = processor.stats()
        
        assert 'processed' in stats
        assert 'geocoded' in stats
        assert 'failed' in stats
        assert 'pending' in stats
        assert 'running' in stats
    
    def test_add_and_process(self, processor, mock_geocoder, temp_store):
        from services.geocoding.base import GeocodingResult
        
        # Setup mock to return coordinates
        mock_geocoder.geocode.return_value = GeocodingResult(
            coordinates=(50.45, 30.52),
            place_name="Київ",
            source="mock",
        )
        
        entry = TrackEntry(
            id="to_process",
            text="Test біля Києва",
            timestamp=datetime.now(timezone.utc),
            lat=None,
            lng=None,
            place="Київ",
            geocoded=False,
        )
        
        result = processor.add_and_process(entry)
        
        # Should have geocoded
        if result:
            updated = temp_store.get("to_process")
            assert updated.lat == 50.45
            assert updated.lng == 30.52
    
    def test_process_now_with_no_pending(self, processor, temp_store):
        # No ungeocodeded entries
        processed = processor.process_now(max_items=10)
        assert processed == 0
    
    def test_process_now_with_pending(self, processor, temp_store, mock_geocoder):
        from services.geocoding.base import GeocodingResult
        
        # Add ungeocodeded entry directly to store
        entry = TrackEntry(
            id="ungeo_1",
            text="Test біля Києва",
            timestamp=datetime.now(timezone.utc),
            lat=None,
            lng=None,
            place="Київ",
            geocoded=False,
        )
        temp_store.add(entry)
        
        # Setup mock
        mock_geocoder.geocode.return_value = GeocodingResult(
            coordinates=(50.45, 30.52),
            place_name="Київ",
            source="mock",
        )
        
        processed = processor.process_now(max_items=10)
        
        # Should have attempted to process
        assert mock_geocoder.geocode.called


class TestTrackStoreFiltering:
    """Tests for advanced filtering."""
    
    @pytest.fixture
    def populated_store(self, tmp_path):
        store = TrackStore(
            file_path=str(tmp_path / "filter_test.json"),
        )
        
        now = datetime.now(timezone.utc)
        
        entries = [
            TrackEntry(id="1", text="Shahed над Київ", timestamp=now,
                      lat=50.45, lng=30.52, oblast="Київська", threat_type="shahed"),
            TrackEntry(id="2", text="Ракета", timestamp=now - timedelta(hours=1),
                      lat=49.98, lng=36.25, oblast="Харківська", threat_type="rocket"),
            TrackEntry(id="3", text="Shahed над Одеса", timestamp=now,
                      lat=46.48, lng=30.73, oblast="Одеська", threat_type="shahed"),
            TrackEntry(id="4", text="Дрон", timestamp=now - timedelta(hours=2),
                      lat=50.45, lng=30.52, oblast="Київська", threat_type="drone"),
        ]
        
        for e in entries:
            store.add(e)
        
        return store
    
    def test_get_by_oblast(self, populated_store):
        kyiv_entries = populated_store.get_by_oblast("Київська")
        assert len(kyiv_entries) == 2
        
        kharkiv_entries = populated_store.get_by_oblast("Харківська")
        assert len(kharkiv_entries) == 1
    
    def test_get_recent_with_since(self, populated_store):
        now = datetime.now(timezone.utc)
        recent = populated_store.get_recent(since=now - timedelta(minutes=30))
        
        # Should only get the 2 recent ones
        assert len(recent) == 2


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

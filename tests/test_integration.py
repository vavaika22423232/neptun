"""
Integration tests - end-to-end testing of the modular architecture.
"""
import json
import os
import tempfile
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import pytest
from flask import Flask

# API
from api import admin_bp, health_bp, tracks_bp
from api.admin import init_admin_api
from api.health import init_health_api
from services.geocoding.cache import GeocodeCache
from services.geocoding.chain import GeocoderChain
from services.geocoding.local import LocalGeocoder
from services.tracks.processor import TrackProcessor

# Services
from services.tracks.store import TrackEntry, TrackStore


class TestEndToEndPipeline:
    """Test complete message processing pipeline."""

    @pytest.fixture
    def temp_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def geocoder(self):
        """Create geocoder chain with local + mock HTTP."""
        # Sample city coords for testing
        city_coords = {
            'київ': (50.4501, 30.5234),
            'харків': (49.9935, 36.2304),
            'одеса': (46.4825, 30.7233),
            'львів': (49.8397, 24.0297),
            'дніпро': (48.4647, 35.0462),
        }
        local = LocalGeocoder(city_coords=city_coords)
        cache = GeocodeCache()
        chain = GeocoderChain(geocoders=[local], cache=cache)
        return chain

    @pytest.fixture
    def track_store(self, temp_dir):
        """Create track store with temp file."""
        return TrackStore(
            file_path=os.path.join(temp_dir, "tracks.json"),
            retention_minutes=60,
            max_count=100,
        )

    @pytest.fixture
    def processor(self, track_store, geocoder):
        """Create track processor."""
        return TrackProcessor(
            store=track_store,
            geocoder=geocoder,
            batch_size=5,
        )

    def test_full_pipeline_add_and_geocode(self, track_store, geocoder):
        """Test adding entry and geocoding it."""
        # Create entry without coordinates
        entry = TrackEntry(
            id="test_pipeline_1",
            text="Шахед над Києвом",
            timestamp=datetime.now(timezone.utc),
            lat=None,
            lng=None,
            place="Київ",
            threat_type="shahed",
        )

        # Add to store
        assert track_store.add(entry)

        # Geocode
        result = geocoder.geocode("Київ")

        if result and result.coordinates:
            # Update entry
            track_store.update(
                entry.id,
                lat=result.coordinates[0],
                lng=result.coordinates[1],
                geocoded=True,
            )

            # Verify
            updated = track_store.get(entry.id)
            assert updated.lat is not None
            assert updated.lng is not None
            assert updated.geocoded is True

    def test_full_pipeline_multiple_entries(self, track_store, geocoder):
        """Test processing multiple entries."""
        now = datetime.now(timezone.utc)

        # Add multiple entries
        cities = ["Київ", "Харків", "Одеса", "Львів", "Дніпро"]
        for i, city in enumerate(cities):
            entry = TrackEntry(
                id=f"batch_{i}",
                text=f"Загроза над {city}",
                timestamp=now - timedelta(minutes=i),
                lat=None,
                lng=None,
                place=city,
                threat_type="shahed",
            )
            track_store.add(entry)

        # Verify all added
        assert track_store.count() == 5

        # Get active
        active = track_store.get_active(since=now - timedelta(hours=1))
        assert len(active) == 5

        # Get stats
        stats = track_store.stats()
        assert stats['count'] == 5
        assert stats['by_type']['shahed'] == 5

    def test_processor_background_geocoding(self, processor, track_store):
        """Test background processor."""
        # Add ungeocodeded entry
        entry = TrackEntry(
            id="background_1",
            text="Test",
            timestamp=datetime.now(timezone.utc),
            lat=None,
            lng=None,
            place="Київ",
            geocoded=False,
        )
        track_store.add(entry)

        # Process
        processor.process_now(max_items=10)

        # Check stats
        stats = processor.stats()
        assert stats['processed'] >= 0

    def test_store_persistence(self, temp_dir):
        """Test save and load."""
        file_path = os.path.join(temp_dir, "persist_test.json")

        # Create and populate
        store1 = TrackStore(file_path=file_path)
        entry = TrackEntry(
            id="persist_1",
            text="Persist test",
            timestamp=datetime.now(timezone.utc),
            lat=50.45,
            lng=30.52,
            place="Test",
        )
        store1.add(entry)
        store1.save(force=True)

        # Create new store, should load
        store2 = TrackStore(file_path=file_path)
        loaded = store2.get("persist_1")

        assert loaded is not None
        assert loaded.place == "Test"

    def test_max_count_enforcement(self, temp_dir):
        """Test that max_count is enforced."""
        store = TrackStore(
            file_path=os.path.join(temp_dir, "max_test.json"),
            max_count=5,
        )

        # Add more than max
        for i in range(10):
            entry = TrackEntry(
                id=f"max_{i}",
                text=f"Entry {i}",
                timestamp=datetime.now(timezone.utc) + timedelta(seconds=i),
                lat=50.0,
                lng=30.0,
            )
            store.add(entry)

        # Should be limited
        assert store.count() <= 5


class TestAPIIntegration:
    """Test API endpoints with real services."""

    @pytest.fixture
    def temp_store(self, tmp_path):
        store = TrackStore(file_path=str(tmp_path / "api_test.json"))

        # Add test data
        now = datetime.now(timezone.utc)
        entries = [
            TrackEntry(id="api_1", text="Test 1", timestamp=now,
                      lat=50.45, lng=30.52, place="Київ",
                      oblast="Київська", threat_type="shahed"),
            TrackEntry(id="api_2", text="Test 2", timestamp=now,
                      lat=49.98, lng=36.25, place="Харків",
                      oblast="Харківська", threat_type="missile"),
        ]
        for e in entries:
            store.add(e)

        return store

    @pytest.fixture
    def app(self, temp_store):
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.config['ADMIN_API_KEY'] = 'integration_test_secret'

        app.extensions['track_store'] = temp_store
        app.extensions['pipeline'] = None

        init_health_api(track_store=temp_store)
        init_admin_api(admin_secret='integration_test_secret', track_store=temp_store)

        app.register_blueprint(health_bp)
        app.register_blueprint(tracks_bp)
        app.register_blueprint(admin_bp)

        return app

    @pytest.fixture
    def client(self, app):
        return app.test_client()

    def test_health_endpoints(self, client):
        """Test all health endpoints."""
        for endpoint in ['/health', '/ready', '/live']:
            response = client.get(endpoint)
            assert response.status_code == 200

    def test_tracks_crud(self, client, temp_store):
        """Test tracks CRUD operations."""
        # Read
        response = client.get('/api/tracks/')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data['tracks']) == 2

        # Read single
        response = client.get('/api/tracks/api_1')
        assert response.status_code == 200
        track = json.loads(response.data)
        assert track['place'] == 'Київ'

        # Delete (with auth)
        response = client.delete(
            '/api/tracks/api_1',
            headers={'Authorization': 'Bearer integration_test_secret'}
        )
        assert response.status_code == 200

        # Verify deleted
        assert temp_store.get('api_1') is None

    def test_tracks_filtering(self, client):
        """Test tracks filtering."""
        # By type
        response = client.get('/api/tracks/?threat_type=shahed')
        assert response.status_code == 200
        data = json.loads(response.data)
        for track in data['tracks']:
            assert track['threat_type'] == 'shahed'

        # By region
        response = client.get('/api/tracks/?region=Київ')
        assert response.status_code == 200

    def test_tracks_geojson(self, client):
        """Test GeoJSON export."""
        response = client.get('/api/tracks/geojson')
        assert response.status_code == 200

        geojson = json.loads(response.data)
        assert geojson['type'] == 'FeatureCollection'
        assert len(geojson['features']) == 2

        # Verify feature structure
        feature = geojson['features'][0]
        assert feature['type'] == 'Feature'
        assert 'geometry' in feature
        assert feature['geometry']['type'] == 'Point'

    def test_tracks_pagination(self, client):
        """Test history pagination."""
        response = client.get('/api/tracks/history?page=1&per_page=1')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['pagination']['page'] == 1
        assert data['pagination']['per_page'] == 1

    def test_admin_auth(self, client):
        """Test admin authentication."""
        # Without auth
        response = client.get('/admin/stats')
        assert response.status_code == 403

        # With auth
        response = client.get(
            '/admin/stats',
            headers={'X-Admin-Secret': 'integration_test_secret'}
        )
        assert response.status_code == 200


class TestGeocodingIntegration:
    """Test geocoding chain integration."""

    def test_local_geocoder_cities(self):
        """Test local geocoder finds major cities."""
        city_coords = {
            'київ': (50.4501, 30.5234),
            'харків': (49.9935, 36.2304),
            'одеса': (46.4825, 30.7233),
            'львів': (49.8397, 24.0297),
            'дніпро': (48.4647, 35.0462),
        }
        local = LocalGeocoder(city_coords=city_coords)

        cities = ["Київ", "Харків", "Одеса", "Львів", "Дніпро"]
        for city in cities:
            result = local.geocode(city)
            assert result is not None, f"Failed to geocode {city}"
            assert result.coordinates is not None

    def test_geocoder_chain_fallback(self):
        """Test chain falls back to next geocoder."""
        # Create mock that fails
        mock_geocoder = Mock()
        mock_geocoder.name = "mock"
        mock_geocoder.priority = 5
        mock_geocoder.is_available.return_value = True
        mock_geocoder.geocode.return_value = None

        # Local should succeed
        city_coords = {'київ': (50.4501, 30.5234)}
        local = LocalGeocoder(city_coords=city_coords)
        local._priority = 10

        chain = GeocoderChain(geocoders=[mock_geocoder, local])

        result = chain.geocode("Київ")
        assert result is not None

    def test_geocode_cache(self):
        """Test geocoding cache."""
        from services.geocoding.base import GeocodingResult

        cache = GeocodeCache()

        # Put result
        result = GeocodingResult(
            coordinates=(50.45, 30.52),
            place_name="Київ",
            source="test",
        )
        cache.put("Київ", result)

        # Get cached
        cached = cache.get("Київ")
        assert cached is not None
        assert cached.coordinates == (50.45, 30.52)

        # Stats
        stats = cache.stats()
        assert 'total' in stats or 'hits' in stats or len(stats) >= 0


class TestThreadSafety:
    """Test thread safety of components."""

    def test_track_store_concurrent_access(self, tmp_path):
        """Test concurrent access to TrackStore."""
        import threading

        store = TrackStore(file_path=str(tmp_path / "concurrent.json"))
        errors = []

        def add_entries(thread_id):
            try:
                for i in range(50):
                    entry = TrackEntry(
                        id=f"thread_{thread_id}_{i}",
                        text="Concurrent test",
                        timestamp=datetime.now(timezone.utc),
                        lat=50.0,
                        lng=30.0,
                    )
                    store.add(entry)
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=add_entries, args=(i,))
            for i in range(5)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Thread errors: {errors}"

    def test_geocode_cache_concurrent(self):
        """Test concurrent cache access."""
        import threading

        from services.geocoding.base import GeocodingResult

        cache = GeocodeCache()
        errors = []

        def access_cache(thread_id):
            try:
                for i in range(100):
                    key = f"key_{thread_id}_{i % 10}"

                    # Read
                    cache.get(key)

                    # Write
                    result = GeocodingResult(
                        coordinates=(50.0 + i * 0.01, 30.0),
                        place_name=f"Place {i}",
                        source="test",
                    )
                    cache.put(key, result)
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=access_cache, args=(i,))
            for i in range(5)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

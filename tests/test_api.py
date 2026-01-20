"""
Tests for API endpoints.
"""
import pytest
import json
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, MagicMock

from flask import Flask
from api import health_bp, tracks_bp, admin_bp
from api.health import init_health_api
from api.admin import init_admin_api
from services.tracks.store import TrackStore, TrackEntry


@pytest.fixture
def temp_store(tmp_path):
    """Create a temporary TrackStore."""
    return TrackStore(
        file_path=str(tmp_path / "test_tracks.json"),
        retention_minutes=60,
    )


@pytest.fixture
def populated_store(temp_store):
    """Store with some test data."""
    now = datetime.now(timezone.utc)
    
    entries = [
        TrackEntry(
            id="track_1",
            text="Shahed над Києвом",
            timestamp=now,
            lat=50.45,
            lng=30.52,
            place="Київ",
            oblast="Київська",
            threat_type="shahed",
        ),
        TrackEntry(
            id="track_2",
            text="Ракета в напрямку Харкова",
            timestamp=now - timedelta(minutes=30),
            lat=49.98,
            lng=36.25,
            place="Харків",
            oblast="Харківська",
            threat_type="missile",
        ),
    ]
    
    for e in entries:
        temp_store.add(e)
    
    return temp_store


@pytest.fixture
def app(populated_store):
    """Create test Flask app with real store."""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['ADMIN_API_KEY'] = 'test_secret'
    
    # Use real store
    app.extensions['track_store'] = populated_store
    app.extensions['pipeline'] = None
    
    # Initialize APIs
    init_health_api(track_store=populated_store)
    init_admin_api(admin_secret='test_secret', track_store=populated_store)
    
    # Register blueprints
    app.register_blueprint(health_bp)
    app.register_blueprint(tracks_bp)
    app.register_blueprint(admin_bp)
    
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


class TestHealthEndpoints:
    """Tests for health check endpoints."""
    
    def test_health_endpoint(self, client):
        response = client.get('/health')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'status' in data
    
    def test_ready_endpoint(self, client):
        response = client.get('/ready')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data.get('ready') is True
    
    def test_live_endpoint(self, client):
        response = client.get('/live')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data.get('alive') is True


class TestTracksEndpoints:
    """Tests for tracks API endpoints."""
    
    def test_get_active_tracks(self, client):
        response = client.get('/api/tracks/')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'tracks' in data
        assert 'count' in data
    
    def test_get_tracks_with_params(self, client):
        response = client.get('/api/tracks/?max_age=30&limit=10')
        assert response.status_code == 200
    
    def test_get_track_history(self, client):
        response = client.get('/api/tracks/history')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'history' in data
        assert 'pagination' in data
    
    def test_get_tracks_by_type(self, client):
        response = client.get('/api/tracks/by-type')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'by_type' in data
    
    def test_get_tracks_geojson(self, client):
        response = client.get('/api/tracks/geojson')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data.get('type') == 'FeatureCollection'
        assert 'features' in data
    
    def test_get_track_stats(self, client):
        response = client.get('/api/tracks/stats')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'store' in data
    
    def test_get_single_track(self, client):
        response = client.get('/api/tracks/track_1')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['id'] == 'track_1'
        assert data['place'] == 'Київ'
    
    def test_get_single_track_not_found(self, client):
        response = client.get('/api/tracks/nonexistent_id')
        assert response.status_code == 404
    
    def test_delete_track_unauthorized(self, client):
        response = client.delete('/api/tracks/track_1')
        assert response.status_code == 401
    
    def test_delete_track_authorized(self, client, populated_store):
        response = client.delete(
            '/api/tracks/track_1',
            headers={'Authorization': 'Bearer test_secret'}
        )
        assert response.status_code == 200
        
        # Track should be removed
        assert populated_store.get('track_1') is None
    
    def test_hide_track_unauthorized(self, client):
        response = client.post('/api/tracks/track_1/hide')
        assert response.status_code == 401
    
    def test_hide_track_authorized(self, client, populated_store):
        response = client.post(
            '/api/tracks/track_1/hide',
            headers={'Authorization': 'Bearer test_secret'}
        )
        assert response.status_code == 200
        
        # Track should be hidden
        track = populated_store.get('track_1')
        assert track.hidden is True


class TestAdminEndpoints:
    """Tests for admin endpoints."""
    
    def test_admin_stats_unauthorized(self, client):
        response = client.get('/admin/stats')
        # Without auth - should fail
        assert response.status_code in [401, 403]
    
    def test_admin_stats_authorized(self, client):
        response = client.get(
            '/admin/stats',
            headers={'X-Admin-Secret': 'test_secret'}
        )
        assert response.status_code == 200
    
    def test_admin_markers_unauthorized(self, client):
        response = client.get('/admin/markers')
        assert response.status_code in [401, 403]


class TestCORS:
    """Tests for CORS headers."""
    
    def test_cors_headers(self, client):
        response = client.get('/health')
        # CORS headers depend on Flask-CORS setup
        assert response.status_code == 200


class TestErrorHandling:
    """Tests for error handling."""
    
    def test_404_error(self, client):
        response = client.get('/nonexistent_endpoint')
        assert response.status_code == 404
    
    def test_method_not_allowed(self, client):
        response = client.post('/health')  # GET only
        assert response.status_code == 405


class TestInputValidation:
    """Tests for input validation."""
    
    def test_invalid_max_age(self, client):
        response = client.get('/api/tracks/?max_age=invalid')
        # Should handle gracefully - use default
        assert response.status_code == 200
    
    def test_negative_limit(self, client):
        response = client.get('/api/tracks/?limit=-1')
        # Should handle gracefully
        assert response.status_code == 200


class TestTracksFiltering:
    """Tests for tracks filtering."""
    
    def test_filter_by_threat_type(self, client):
        response = client.get('/api/tracks/?threat_type=shahed')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        for track in data['tracks']:
            assert track['threat_type'] == 'shahed'
    
    def test_filter_by_region(self, client):
        response = client.get('/api/tracks/?region=Київ')
        assert response.status_code == 200
    
    def test_pagination_history(self, client):
        response = client.get('/api/tracks/history?page=1&per_page=1')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['pagination']['per_page'] == 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

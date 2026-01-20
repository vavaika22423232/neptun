"""
Tests for geocoding services.
"""
import pytest
from unittest.mock import Mock, patch
import time

from services.geocoding.base import GeocoderInterface, GeocodingResult
from services.geocoding.local import LocalGeocoder
from services.geocoding.chain import GeocoderChain
from services.geocoding.cache import GeocodeCache, CacheEntry
from services.geocoding.photon import PhotonGeocoder


class TestGeocodingResult:
    """Tests for GeocodingResult dataclass."""
    
    def test_create_result(self):
        result = GeocodingResult(
            coordinates=(50.45, 30.52),
            place_name="Київ",
            source="test",
            confidence=0.95,
        )
        assert result.coordinates == (50.45, 30.52)
        assert result.place_name == "Київ"
        assert result.source == "test"
        assert result.confidence == 0.95
    
    def test_result_is_frozen(self):
        result = GeocodingResult(
            coordinates=(50.45, 30.52),
            place_name="Київ",
            source="test",
        )
        with pytest.raises(Exception):  # FrozenInstanceError
            result.coordinates = (0, 0)


class TestLocalGeocoder:
    """Tests for LocalGeocoder."""
    
    @pytest.fixture
    def geocoder(self):
        return LocalGeocoder(
            city_coords={
                'київ': (50.4501, 30.5234),
                'харків': (49.9935, 36.2304),
                'одеса': (46.4825, 30.7233),
                'львів': (49.8397, 24.0297),
            },
            settlements={
                'бровари': (50.5114, 30.7908),
                'ірпінь': (50.5216, 30.2525),
            },
            settlements_by_oblast={
                'київ': {
                    'бориспіль': (50.3522, 30.9548),
                },
                'харків': {
                    'чугуїв': (49.8367, 36.6897),
                },
            },
        )
    
    def test_name(self, geocoder):
        assert geocoder.name == "local"
    
    def test_priority(self, geocoder):
        assert geocoder.priority == 10
    
    def test_geocode_exact_match(self, geocoder):
        result = geocoder.geocode("Київ")
        assert result is not None
        assert result.coordinates == (50.4501, 30.5234)
        assert result.source == "local"
    
    def test_geocode_case_insensitive(self, geocoder):
        result = geocoder.geocode("КИЇВ")
        assert result is not None
        assert result.coordinates == (50.4501, 30.5234)
    
    def test_geocode_with_prefix(self, geocoder):
        result = geocoder.geocode("м. Харків")
        assert result is not None
        assert result.coordinates[0] == pytest.approx(49.9935, 0.01)
    
    def test_geocode_settlement(self, geocoder):
        result = geocoder.geocode("Бровари")
        assert result is not None
        assert result.coordinates == (50.5114, 30.7908)
    
    def test_geocode_with_region(self, geocoder):
        result = geocoder.geocode("Бориспіль", region="Київська область")
        assert result is not None
        assert result.coordinates == (50.3522, 30.9548)
    
    def test_geocode_not_found(self, geocoder):
        result = geocoder.geocode("Невідоме місто")
        assert result is None
    
    def test_geocode_empty_query(self, geocoder):
        result = geocoder.geocode("")
        assert result is None
        result = geocoder.geocode(None)
        assert result is None
    
    def test_stats(self, geocoder):
        stats = geocoder.stats()
        assert stats['city_coords'] == 4
        assert stats['settlements'] == 2
        assert stats['oblasts_with_settlements'] == 2


class TestGeocodeCache:
    """Tests for GeocodeCache."""
    
    @pytest.fixture
    def cache(self, tmp_path):
        return GeocodeCache(
            cache_file=str(tmp_path / "cache.json"),
            negative_cache_file=str(tmp_path / "negative.json"),
            positive_ttl=3600,
            negative_ttl=1800,
        )
    
    def test_put_and_get(self, cache):
        result = GeocodingResult(
            coordinates=(50.45, 30.52),
            place_name="Київ",
            source="test",
        )
        cache.put("київ", result)
        
        cached = cache.get("київ")
        assert cached is not None
        assert cached.coordinates == (50.45, 30.52)
    
    def test_get_nonexistent(self, cache):
        result = cache.get("nonexistent")
        assert result is None
    
    def test_negative_cache(self, cache):
        cache.add_negative("unknown_place")
        assert cache.is_negative_cached("unknown_place") is True
        assert cache.is_negative_cached("other_place") is False
    
    def test_cache_with_region(self, cache):
        result = GeocodingResult(
            coordinates=(50.35, 30.95),
            place_name="Бориспіль",
            source="test",
        )
        cache.put("бориспіль", result, region="київська")
        
        # Should find with region
        cached = cache.get("бориспіль", region="київська")
        assert cached is not None
        
        # Should not find without region
        cached_no_region = cache.get("бориспіль")
        assert cached_no_region is None
    
    def test_stats(self, cache):
        result = GeocodingResult(
            coordinates=(50.45, 30.52),
            place_name="Test",
            source="test",
        )
        cache.put("test1", result)
        cache.add_negative("test2")
        
        stats = cache.stats()
        assert stats['total'] == 2
        assert stats['positive'] == 1
        assert stats['negative'] == 1


class TestGeocoderChain:
    """Tests for GeocoderChain."""
    
    @pytest.fixture
    def mock_geocoder_success(self):
        geocoder = Mock(spec=GeocoderInterface)
        geocoder.name = "mock_success"
        geocoder.priority = 20
        geocoder.is_available = True
        geocoder.geocode.return_value = GeocodingResult(
            coordinates=(50.45, 30.52),
            place_name="Mock City",
            source="mock",
        )
        return geocoder
    
    @pytest.fixture
    def mock_geocoder_fail(self):
        geocoder = Mock(spec=GeocoderInterface)
        geocoder.name = "mock_fail"
        geocoder.priority = 10
        geocoder.is_available = True
        geocoder.geocode.return_value = None
        return geocoder
    
    def test_chain_finds_result(self, mock_geocoder_success):
        chain = GeocoderChain(geocoders=[mock_geocoder_success])
        result = chain.geocode("Test")
        
        assert result is not None
        assert result.coordinates == (50.45, 30.52)
    
    def test_chain_fallback(self, mock_geocoder_fail, mock_geocoder_success):
        chain = GeocoderChain(geocoders=[mock_geocoder_fail, mock_geocoder_success])
        result = chain.geocode("Test")
        
        # Should fallback to success geocoder
        assert result is not None
        assert mock_geocoder_fail.geocode.called
        assert mock_geocoder_success.geocode.called
    
    def test_chain_priority_order(self, mock_geocoder_fail, mock_geocoder_success):
        # Fail has priority 10, success has 20
        # Should try fail first (lower priority = first)
        chain = GeocoderChain(geocoders=[mock_geocoder_success, mock_geocoder_fail])
        chain.geocode("Test")
        
        # Check call order - fail should be called first
        assert mock_geocoder_fail.geocode.call_count == 1
    
    def test_chain_caching(self, mock_geocoder_success, tmp_path):
        cache = GeocodeCache(
            cache_file=str(tmp_path / "cache.json"),
            negative_cache_file=str(tmp_path / "negative.json"),
        )
        chain = GeocoderChain(geocoders=[mock_geocoder_success], cache=cache)
        
        # First call
        result1 = chain.geocode("Test")
        assert result1 is not None
        assert mock_geocoder_success.geocode.call_count == 1
        
        # Second call - should hit cache
        result2 = chain.geocode("Test")
        assert result2 is not None
        assert mock_geocoder_success.geocode.call_count == 1  # Still 1
    
    def test_chain_empty_query(self, mock_geocoder_success):
        chain = GeocoderChain(geocoders=[mock_geocoder_success])
        
        assert chain.geocode("") is None
        assert chain.geocode("   ") is None
        assert mock_geocoder_success.geocode.call_count == 0
    
    def test_geocode_simple(self, mock_geocoder_success):
        chain = GeocoderChain(geocoders=[mock_geocoder_success])
        coords = chain.geocode_simple("Test")
        
        assert coords == (50.45, 30.52)
    
    def test_stats(self, mock_geocoder_success, tmp_path):
        cache = GeocodeCache(
            cache_file=str(tmp_path / "cache.json"),
            negative_cache_file=str(tmp_path / "negative.json"),
        )
        chain = GeocoderChain(geocoders=[mock_geocoder_success], cache=cache)
        chain.geocode("Test1")
        chain.geocode("Test1")  # Cache hit
        
        stats = chain.stats()
        assert stats['total_requests'] == 2
        assert stats['cache_hits'] == 1


class TestPhotonGeocoder:
    """Tests for PhotonGeocoder."""
    
    @pytest.fixture
    def geocoder(self):
        return PhotonGeocoder(timeout=5.0)
    
    def test_name(self, geocoder):
        assert geocoder.name == "photon"
    
    def test_priority(self, geocoder):
        assert geocoder.priority == 50  # Medium priority
    
    def test_is_available(self, geocoder):
        assert geocoder.is_available() is True
    
    @patch('services.geocoding.photon.requests.get')
    def test_geocode_success(self, mock_get, geocoder):
        mock_get.return_value.ok = True
        mock_get.return_value.json.return_value = {
            'features': [{
                'geometry': {
                    'coordinates': [30.52, 50.45]  # [lng, lat]
                },
                'properties': {
                    'name': 'Київ',
                    'country': 'Ukraine',
                }
            }]
        }
        
        result = geocoder.geocode("Київ")
        
        assert result is not None
        assert result.coordinates[0] == pytest.approx(50.45, 0.01)
        assert result.coordinates[1] == pytest.approx(30.52, 0.01)
        assert result.source == "photon"
    
    @patch('services.geocoding.photon.requests.get')
    def test_geocode_no_results(self, mock_get, geocoder):
        mock_get.return_value.ok = True
        mock_get.return_value.json.return_value = {'features': []}
        
        result = geocoder.geocode("Unknown Place")
        assert result is None
    
    @patch('services.geocoding.photon.requests.get')
    def test_geocode_outside_ukraine(self, mock_get, geocoder):
        mock_get.return_value.ok = True
        mock_get.return_value.json.return_value = {
            'features': [{
                'geometry': {
                    'coordinates': [37.62, 55.75]  # Moscow coordinates
                },
                'properties': {
                    'name': 'Moscow',
                    'country': 'Russia',
                }
            }]
        }
        
        result = geocoder.geocode("Moscow")
        # Should filter out - outside Ukraine bbox
        assert result is None
    
    @patch('services.geocoding.photon.requests.get')
    def test_geocode_api_error(self, mock_get, geocoder):
        mock_get.return_value.ok = False
        
        result = geocoder.geocode("Test")
        assert result is None
    
    def test_stats(self, geocoder):
        stats = geocoder.stats()
        assert 'requests' in stats
        assert 'hits' in stats
        assert 'errors' in stats


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

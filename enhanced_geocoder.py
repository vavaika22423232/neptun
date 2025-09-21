#!/usr/bin/env python3
"""
Enhanced geocoding using OpenStreetMap Nominatim API
Provides comprehensive coordinates for Ukrainian cities and settlements
"""

import requests
import time
import json
import os
from typing import Optional, Tuple

class UkrainianGeocoder:
    """Enhanced geocoder for Ukrainian settlements using OSM Nominatim"""
    
    def __init__(self, cache_file="ukraine_geocache.json"):
        self.base_url = "https://nominatim.openstreetmap.org/search"
        self.cache_file = cache_file
        self.cache = self.load_cache()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Ukrainian-Military-Alerts/1.0 (your-email@example.com)'
        })
    
    def load_cache(self) -> dict:
        """Load geocoding cache from file"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save_cache(self):
        """Save geocoding cache to file"""
        with open(self.cache_file, 'w', encoding='utf-8') as f:
            json.dump(self.cache, f, ensure_ascii=False, indent=2)
    
    def geocode_settlement(self, city_name: str, region: str = None) -> Optional[Tuple[float, float]]:
        """
        Geocode Ukrainian settlement with optional region context
        
        Args:
            city_name: Name of the city/settlement
            region: Optional region name for disambiguation
            
        Returns:
            Tuple of (latitude, longitude) or None if not found
        """
        # Create cache key
        cache_key = f"{city_name.lower()}_{region.lower() if region else 'ukraine'}"
        
        # Check cache first
        if cache_key in self.cache:
            return tuple(self.cache[cache_key])
        
        # Prepare search query
        query_parts = [city_name]
        if region:
            query_parts.append(region)
        query_parts.append("Ukraine")
        
        query = ", ".join(query_parts)
        
        params = {
            'q': query,
            'format': 'json',
            'countrycodes': 'ua',  # Restrict to Ukraine
            'limit': 5,
            'addressdetails': 1
        }
        
        try:
            # Rate limiting - OSM Nominatim requires max 1 request per second
            time.sleep(1.1)
            
            response = self.session.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            
            results = response.json()
            
            if results:
                # Find best match
                best_result = self.find_best_match(results, city_name, region)
                if best_result:
                    lat = float(best_result['lat'])
                    lon = float(best_result['lon'])
                    
                    # Cache the result
                    self.cache[cache_key] = [lat, lon]
                    self.save_cache()
                    
                    print(f"✅ Geocoded {city_name} -> ({lat}, {lon})")
                    return (lat, lon)
            
            print(f"❌ No results for {city_name}")
            return None
            
        except Exception as e:
            print(f"🚨 Geocoding error for {city_name}: {e}")
            return None
    
    def find_best_match(self, results, city_name, region):
        """Find the best matching result from OSM response"""
        city_lower = city_name.lower()
        
        for result in results:
            display_name = result.get('display_name', '').lower()
            osm_type = result.get('type', '')
            
            # Prefer cities, towns, villages over other types
            if osm_type in ['city', 'town', 'village', 'hamlet']:
                # Check if city name appears in display name
                if city_lower in display_name:
                    # If region specified, prefer results containing region
                    if region and region.lower() in display_name:
                        return result
                    elif not region:
                        return result
        
        # Fallback to first result if no perfect match
        return results[0] if results else None

# Test the geocoder
if __name__ == "__main__":
    geocoder = UkrainianGeocoder()
    
    # Test problematic cities
    test_cities = [
        ("Зарічне", "Дніпропетровська область"),
        ("Зарічне", "Рівненська область"),
        ("Гребінка", "Полтавська область"),
        ("Олександрія", "Кіровоградська область"),
        ("Куп'янськ", "Харківська область"),
    ]
    
    print("🧪 Testing Enhanced Ukrainian Geocoder")
    print("="*50)
    
    for city, region in test_cities:
        coords = geocoder.geocode_settlement(city, region)
        if coords:
            print(f"📍 {city} ({region}): {coords}")
        else:
            print(f"❌ {city} ({region}): Not found")
        print()

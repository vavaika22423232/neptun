#!/usr/bin/env python3
"""
OpenStreetMap Nominatim API integration for Ukrainian geocoding
Provides accurate coordinates for all Ukrainian settlements
"""

import requests
import json
import time
from typing import Dict, List, Tuple, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NominatimGeocoder:
    """
    OpenStreetMap Nominatim API geocoder for Ukrainian settlements
    """
    
    def __init__(self):
        self.base_url = "https://nominatim.openstreetmap.org/search"
        self.headers = {
            'User-Agent': 'Ukrainian-Threat-Monitor/1.0 (https://github.com/vavaika22423232/neptun)'
        }
        self.cache = {}  # In-memory cache for repeated queries
        self.last_request_time = 0
        self.min_request_interval = 1.0  # Respect rate limiting (1 request per second)
    
    def _rate_limit(self):
        """Ensure we don't exceed rate limits"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            time.sleep(sleep_time)
        self.last_request_time = time.time()
    
    def geocode_settlement(self, city_name: str, region: str = None) -> Optional[Tuple[float, float]]:
        """
        Geocode a Ukrainian settlement using Nominatim API
        
        Args:
            city_name: Name of the settlement (e.g., "Зарічне", "Гребінка")
            region: Optional region specification (e.g., "Полтавська область")
            
        Returns:
            Tuple of (latitude, longitude) or None if not found
        """
        # Check cache first
        cache_key = f"{city_name}_{region or 'ukraine'}"
        if cache_key in self.cache:
            logger.debug(f"Cache hit for {cache_key}: {self.cache[cache_key]}")
            return self.cache[cache_key]
        
        # Prepare query
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
            'addressdetails': 1,
            'extratags': 1
        }
        
        try:
            # Rate limiting
            self._rate_limit()
            
            logger.info(f"Nominatim query: {query}")
            response = requests.get(self.base_url, params=params, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            results = response.json()
            
            if not results:
                logger.warning(f"No results found for: {query}")
                self.cache[cache_key] = None
                return None
            
            # Find the best match
            best_result = self._find_best_match(results, city_name, region)
            
            if best_result:
                lat = float(best_result['lat'])
                lng = float(best_result['lon'])
                coords = (lat, lng)
                
                logger.info(f"Found coordinates for {city_name}: {coords}")
                logger.debug(f"Address: {best_result.get('display_name', 'N/A')}")
                
                # Cache the result
                self.cache[cache_key] = coords
                return coords
            else:
                logger.warning(f"No suitable match found for: {query}")
                self.cache[cache_key] = None
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error for {query}: {e}")
            return None
        except (ValueError, KeyError) as e:
            logger.error(f"Parsing error for {query}: {e}")
            return None
    
    def _find_best_match(self, results: List[Dict], city_name: str, region: str = None) -> Optional[Dict]:
        """
        Find the best matching result from Nominatim response
        """
        if not results:
            return None
        
        # Scoring criteria
        scored_results = []
        
        for result in results:
            score = 0
            display_name = result.get('display_name', '').lower()
            address = result.get('address', {})
            
            # Exact city name match gets high score
            if city_name.lower() in display_name:
                score += 10
            
            # Region match
            if region:
                region_lower = region.lower()
                if any(region_lower in field.lower() for field in [
                    address.get('state', ''),
                    address.get('county', ''),
                    display_name
                ]):
                    score += 5
            
            # Prefer settlements over larger administrative areas
            place_type = result.get('type', '')
            if place_type in ['city', 'town', 'village', 'hamlet']:
                score += 3
            elif place_type in ['administrative']:
                score -= 2
            
            # Prefer higher importance scores from OSM
            importance = float(result.get('importance', 0))
            score += importance * 2
            
            scored_results.append((score, result))
        
        # Return the highest scoring result
        scored_results.sort(key=lambda x: x[0], reverse=True)
        best_score, best_result = scored_results[0]
        
        logger.debug(f"Best match score: {best_score} for {best_result.get('display_name', 'N/A')}")
        
        return best_result if best_score > 0 else None
    
    def batch_geocode(self, settlements: List[Tuple[str, str]]) -> Dict[str, Tuple[float, float]]:
        """
        Batch geocode multiple settlements
        
        Args:
            settlements: List of (city_name, region) tuples
            
        Returns:
            Dictionary mapping city names to coordinates
        """
        results = {}
        
        for i, (city_name, region) in enumerate(settlements):
            logger.info(f"Geocoding {i+1}/{len(settlements)}: {city_name}")
            coords = self.geocode_settlement(city_name, region)
            if coords:
                results[city_name] = coords
            
            # Progress update every 10 items
            if (i + 1) % 10 == 0:
                logger.info(f"Progress: {i+1}/{len(settlements)} completed")
        
        return results

# Global geocoder instance
nominatim_geocoder = NominatimGeocoder()

def get_coordinates_nominatim(city_name: str, region: str = None) -> Optional[Tuple[float, float]]:
    """
    Public function to get coordinates using Nominatim
    
    Args:
        city_name: Name of the settlement
        region: Optional region specification
        
    Returns:
        Tuple of (latitude, longitude) or None if not found
    """
    return nominatim_geocoder.geocode_settlement(city_name, region)

if __name__ == "__main__":
    # Test the geocoder
    test_cities = [
        ("Зарічне", "Дніпропетровська область"),
        ("Зарічне", "Рівненська область"), 
        ("Гребінка", "Полтавська область"),
        ("Київ", None),
        ("Харків", None)
    ]
    
    for city, region in test_cities:
        print(f"\nTesting: {city}" + (f" ({region})" if region else ""))
        coords = get_coordinates_nominatim(city, region)
        if coords:
            print(f"  ✅ Found: {coords}")
        else:
            print(f"  ❌ Not found")

"""
Integration with Ukrainian energy providers APIs for blackout schedules
Supports: DTEK, Ukrenergo, YASNO, and regional providers
"""

import requests
import json
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BlackoutAPIClient:
    """Client for fetching blackout schedules from various Ukrainian energy providers"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # Initialize geocoder for address lookup
        self.geocoder = Nominatim(user_agent="neptun_blackout_app")
        
        # API endpoints for different providers
        self.providers = {
            'dtek_kyiv': {
                'name': 'ДТЕК Київські електромережі',
                'api': 'https://www.dtek-krem.com.ua/ua/shutdowns',
                'regions': ['київ', 'київська']
            },
            'dtek_dnipro': {
                'name': 'ДТЕК Дніпровські електромережі',
                'api': 'https://www.dtek-dnem.com.ua/ua/shutdowns',
                'regions': ['дніпро', 'дніпропетровська']
            },
            'dtek_odesa': {
                'name': 'ДТЕК Одеські електромережі',
                'api': 'https://www.dtek-oem.com.ua/ua/shutdowns',
                'regions': ['одеса', 'одеська']
            },
            'dtek_donetsk': {
                'name': 'ДТЕК Донецькі електромережі',
                'api': 'https://www.dtek-donec.com.ua/ua/shutdowns',
                'regions': ['донецька', 'маріуполь']
            },
            'yasno': {
                'name': 'YASNO',
                'api': 'https://api.yasno.com.ua/api/v1/pages/home/schedule-turn-off-electricity',
                'regions': ['київ', 'київська']
            },
            'ukrenergo': {
                'name': 'Укренерго',
                'api': 'https://www.oe.if.ua/',
                'regions': ['all']
            }
        }
    
    def geocode_address(self, city: str, street: str = None) -> Optional[Dict]:
        """
        Geocode address to get coordinates and full location info
        """
        try:
            # Build query
            query_parts = [city, 'Ukraine']
            if street:
                query_parts.insert(1, street)
            query = ', '.join(query_parts)
            
            logger.info(f"Geocoding: {query}")
            location = self.geocoder.geocode(query, exactly_one=True, timeout=10)
            
            if location:
                return {
                    'address': location.address,
                    'latitude': location.latitude,
                    'longitude': location.longitude,
                    'raw': location.raw
                }
            return None
            
        except (GeocoderTimedOut, GeocoderServiceError) as e:
            logger.error(f"Geocoding error: {e}")
            return None
    
    def detect_provider(self, city: str, oblast: str = None) -> str:
        """
        Detect energy provider based on city/oblast
        """
        city_lower = city.lower()
        oblast_lower = oblast.lower() if oblast else ''
        
        # Check each provider
        for provider_id, provider_info in self.providers.items():
            for region in provider_info['regions']:
                if region == 'all':
                    continue
                if region in city_lower or region in oblast_lower:
                    return provider_id
        
        return 'ukrenergo'  # Default fallback
    
    def fetch_dtek_schedule(self, provider_id: str, address: str) -> Optional[Dict]:
        """
        Fetch schedule from DTEK API
        DTEK provides schedules by queue groups
        """
        try:
            provider = self.providers.get(provider_id)
            if not provider or 'dtek' not in provider_id:
                return None
            
            # DTEK APIs typically require address search first
            # This is a simplified version - real implementation needs proper API calls
            
            # For now, return structure based on their typical response
            # TODO: Implement actual DTEK API integration when endpoints are documented
            
            logger.info(f"Fetching from {provider['name']}")
            
            # Simulated DTEK response structure
            return {
                'provider': provider['name'],
                'group': None,  # Will be determined by address
                'schedule': [],
                'source': 'dtek'
            }
            
        except Exception as e:
            logger.error(f"Error fetching DTEK schedule: {e}")
            return None
    
    def fetch_yasno_schedule(self, address: str) -> Optional[Dict]:
        """
        Fetch schedule from YASNO API
        YASNO uses group-based system (1-6)
        """
        try:
            url = self.providers['yasno']['api']
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # YASNO returns schedule for all groups
                # Need to determine which group the address belongs to
                
                return {
                    'provider': 'YASNO',
                    'data': data,
                    'source': 'yasno'
                }
            
        except Exception as e:
            logger.error(f"Error fetching YASNO schedule: {e}")
            return None
    
    def determine_blackout_group(self, city: str, street: str, building: str = None) -> str:
        """
        Determine blackout group (queue) for specific address
        Returns subgroup like "1.1", "1.2", "2.1", "2.2", "3.1", "3.2"
        
        Uses the UKRAINE_ADDRESSES_DB database for accurate queue assignment
        """
        from ukraine_addresses_db import UKRAINE_ADDRESSES_DB
        
        # Normalize inputs
        city_key = city.strip().lower()
        street_key = street.strip().lower() if street else ''
        
        # Build search key: "city street"
        search_key = f"{city_key} {street_key}".strip()
        
        # Direct match in database
        if search_key in UKRAINE_ADDRESSES_DB:
            return UKRAINE_ADDRESSES_DB[search_key]['group']
        
        # Try matching without building number (DTEK assigns queues by street, not building)
        # Try partial matches - search for any entry that starts with our city+street
        for db_key, db_data in UKRAINE_ADDRESSES_DB.items():
            if db_key.startswith(search_key):
                return db_data['group']
        
        # Try matching just city and part of street name
        if street_key:
            street_words = street_key.split()
            for street_word in street_words:
                if len(street_word) > 3:  # Skip short words like "вул"
                    partial_key = f"{city_key} {street_word}"
                    for db_key, db_data in UKRAINE_ADDRESSES_DB.items():
                        if partial_key in db_key:
                            return db_data['group']
        
        # Fallback: assign based on first letter of street for consistency
        # This ensures same address always gets same queue
        if street_key:
            first_letter_code = ord(street_key[0].lower()) % 6
        else:
            first_letter_code = ord(city_key[0].lower()) % 6
        
        main_group = (first_letter_code // 2) + 1  # 1, 2, or 3
        subgroup = (first_letter_code % 2) + 1     # 1 or 2
        
        return f"{main_group}.{subgroup}"
    
    def get_schedule_for_address(self, city: str, street: str, building: str = None) -> Dict:
        """
        Main method to get blackout schedule for any address in Ukraine
        
        Returns:
        - provider: Energy provider name
        - group: Blackout group/queue number
        - schedule: List of time slots with status
        - address: Formatted address
        - coordinates: Lat/lon if available
        """
        
        # Step 1: Geocode address to verify it exists
        geo_result = self.geocode_address(city, street)
        
        if not geo_result:
            # Try just city if street search failed
            geo_result = self.geocode_address(city)
        
        # Step 2: Detect provider
        provider_id = self.detect_provider(city)
        provider = self.providers[provider_id]
        
        # Step 3: Determine blackout group
        group = self.determine_blackout_group(city, street, building)
        
        # Step 4: Get schedule from provider
        # TODO: Replace with real API calls
        schedule_data = self._get_sample_schedule(group)
        
        # Build full address
        full_address = f"{city}"
        if street:
            full_address += f", {street}"
        if building:
            full_address += f", {building}"
        
        result = {
            'address': full_address,
            'city': city,
            'provider': provider['name'],
            'group': group,
            'schedule': schedule_data,
            'coordinates': {
                'lat': geo_result['latitude'] if geo_result else None,
                'lon': geo_result['longitude'] if geo_result else None
            } if geo_result else None,
            'found': geo_result is not None
        }
        
        return result
    
    def _get_sample_schedule(self, group: str) -> List[Dict]:
        """
        Returns sample schedule structure for subgroups
        TODO: Replace with real API data
        """
        schedules = {
            '1.1': [
                {'time': '00:00 - 04:00', 'label': 'Електропостачання', 'status': 'normal'},
                {'time': '04:00 - 08:00', 'label': 'Можливе відключення', 'status': 'normal'},
                {'time': '08:00 - 12:00', 'label': 'Електропостачання', 'status': 'normal'},
                {'time': '12:00 - 16:00', 'label': 'Активне відключення', 'status': 'active'},
                {'time': '16:00 - 20:00', 'label': 'Електропостачання', 'status': 'normal'},
                {'time': '20:00 - 24:00', 'label': 'Можливе відключення', 'status': 'upcoming'},
            ],
            '1.2': [
                {'time': '00:00 - 04:00', 'label': 'Можливе відключення', 'status': 'upcoming'},
                {'time': '04:00 - 08:00', 'label': 'Електропостачання', 'status': 'normal'},
                {'time': '08:00 - 12:00', 'label': 'Можливе відключення', 'status': 'normal'},
                {'time': '12:00 - 16:00', 'label': 'Електропостачання', 'status': 'normal'},
                {'time': '16:00 - 20:00', 'label': 'Активне відключення', 'status': 'active'},
                {'time': '20:00 - 24:00', 'label': 'Електропостачання', 'status': 'normal'},
            ],
            '2.1': [
                {'time': '00:00 - 04:00', 'label': 'Електропостачання', 'status': 'normal'},
                {'time': '04:00 - 08:00', 'label': 'Активне відключення', 'status': 'active'},
                {'time': '08:00 - 12:00', 'label': 'Електропостачання', 'status': 'normal'},
                {'time': '12:00 - 16:00', 'label': 'Можливе відключення', 'status': 'normal'},
                {'time': '16:00 - 20:00', 'label': 'Електропостачання', 'status': 'normal'},
                {'time': '20:00 - 24:00', 'label': 'Можливе відключення', 'status': 'upcoming'},
            ],
            '2.2': [
                {'time': '00:00 - 04:00', 'label': 'Можливе відключення', 'status': 'normal'},
                {'time': '04:00 - 08:00', 'label': 'Електропостачання', 'status': 'normal'},
                {'time': '08:00 - 12:00', 'label': 'Активне відключення', 'status': 'active'},
                {'time': '12:00 - 16:00', 'label': 'Електропостачання', 'status': 'normal'},
                {'time': '16:00 - 20:00', 'label': 'Можливе відключення', 'status': 'upcoming'},
                {'time': '20:00 - 24:00', 'label': 'Електропостачання', 'status': 'normal'},
            ],
            '3.1': [
                {'time': '00:00 - 04:00', 'label': 'Можливе відключення', 'status': 'upcoming'},
                {'time': '04:00 - 08:00', 'label': 'Електропостачання', 'status': 'normal'},
                {'time': '08:00 - 12:00', 'label': 'Можливе відключення', 'status': 'normal'},
                {'time': '12:00 - 16:00', 'label': 'Електропостачання', 'status': 'normal'},
                {'time': '16:00 - 20:00', 'label': 'Активне відключення', 'status': 'active'},
                {'time': '20:00 - 24:00', 'label': 'Електропостачання', 'status': 'normal'},
            ],
            '3.2': [
                {'time': '00:00 - 04:00', 'label': 'Електропостачання', 'status': 'normal'},
                {'time': '04:00 - 08:00', 'label': 'Можливе відключення', 'status': 'normal'},
                {'time': '08:00 - 12:00', 'label': 'Електропостачання', 'status': 'normal'},
                {'time': '12:00 - 16:00', 'label': 'Можливе відключення', 'status': 'upcoming'},
                {'time': '16:00 - 20:00', 'label': 'Електропостачання', 'status': 'normal'},
                {'time': '20:00 - 24:00', 'label': 'Активне відключення', 'status': 'active'},
            ],
        }
        
        return schedules.get(group, schedules['1.1'])
    
    def search_addresses(self, query: str) -> List[Dict]:
        """
        Search for addresses matching query
        Uses geocoding service to find real addresses
        """
        results = []
        
        try:
            # Search in Ukraine
            locations = self.geocoder.geocode(
                f"{query}, Ukraine",
                exactly_one=False,
                limit=5,
                timeout=10
            )
            
            if locations:
                for loc in locations:
                    # Parse address components
                    address_parts = loc.address.split(',')
                    
                    results.append({
                        'address': loc.address,
                        'display_name': address_parts[0] if address_parts else loc.address,
                        'latitude': loc.latitude,
                        'longitude': loc.longitude
                    })
        
        except Exception as e:
            logger.error(f"Address search error: {e}")
        
        return results


# Global instance
blackout_client = BlackoutAPIClient()

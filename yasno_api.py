"""
YASNO (DTEK) API Client for real-time blackout schedules
Отримує актуальні графіки відключень з офіційного API YASNO
"""

import requests
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging

log = logging.getLogger(__name__)

class YasnoAPI:
    """Client for YASNO (DTEK) blackout schedule API"""
    
    BASE_URL = "https://api.yasno.com.ua/api/v1/pages/home/schedule-turn-off-electricity"
    
    # Mapping cities to YASNO regions
    CITY_TO_REGION = {
        'київ': 'kiev',
        'киев': 'kiev',
        'kyiv': 'kiev',
        'kiev': 'kiev',
        'дніпро': 'dnipro',
        'днепр': 'dnipro',
        'dnipro': 'dnipro',
        'дніпропетровськ': 'dnipro',
    }
    
    # Available groups per region
    AVAILABLE_GROUPS = ['1.1', '1.2', '2.1', '2.2', '3.1', '3.2', '4.1', '4.2', '5.1', '5.2', '6.1', '6.2']
    
    def __init__(self):
        self._cache = None
        self._cache_time = None
        self._cache_duration = timedelta(minutes=15)
    
    def _get_data(self, force_refresh: bool = False) -> Optional[Dict]:
        """Fetch data from YASNO API with caching"""
        now = datetime.now()
        
        # Return cached data if valid
        if not force_refresh and self._cache and self._cache_time:
            if now - self._cache_time < self._cache_duration:
                return self._cache
        
        try:
            response = requests.get(
                self.BASE_URL,
                headers={
                    'Accept': 'application/json',
                    'User-Agent': 'Mozilla/5.0 (compatible; NeptunApp/1.0)'
                },
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            self._cache = data
            self._cache_time = now
            log.info("YASNO API data fetched successfully")
            return data
            
        except Exception as e:
            log.error(f"Error fetching YASNO API: {e}")
            # Return cached data even if expired
            if self._cache:
                return self._cache
            return None
    
    def get_schedule_component(self, data: Dict) -> Optional[Dict]:
        """Extract schedule component from API response"""
        if not data or 'components' not in data:
            return None
        
        for component in data.get('components', []):
            if component.get('template_name') == 'electricity-outages-daily-schedule':
                return component
        return None
    
    def get_regions(self) -> List[str]:
        """Get available regions"""
        data = self._get_data()
        schedule = self.get_schedule_component(data)
        if schedule and 'schedule' in schedule:
            return list(schedule['schedule'].keys())
        return ['kiev', 'dnipro']
    
    def get_groups_for_region(self, region: str) -> List[str]:
        """Get available groups for a region"""
        data = self._get_data()
        schedule = self.get_schedule_component(data)
        if schedule and 'schedule' in schedule:
            region_data = schedule['schedule'].get(region, {})
            return list(region_data.keys())
        return self.AVAILABLE_GROUPS
    
    def city_to_region(self, city: str) -> Optional[str]:
        """Convert city name to YASNO region"""
        city_lower = city.lower().strip()
        return self.CITY_TO_REGION.get(city_lower)
    
    def get_schedule_for_group(self, region: str, group: str, day_index: int = 0) -> List[Dict]:
        """
        Get schedule for specific region and group
        
        Args:
            region: 'kiev' or 'dnipro'
            group: e.g. '1.1', '2.2', etc.
            day_index: 0 = today, 1 = tomorrow, etc. (up to 6)
        
        Returns:
            List of time slots with outage info
        """
        data = self._get_data()
        schedule_component = self.get_schedule_component(data)
        
        if not schedule_component:
            log.warning("No schedule component found in YASNO data")
            return []
        
        schedule_data = schedule_component.get('schedule', {})
        region_data = schedule_data.get(region, {})
        
        group_key = f"group_{group}"
        group_schedule = region_data.get(group_key, [])
        
        if not group_schedule:
            log.warning(f"No schedule found for {region}/{group_key}")
            return []
        
        # Get schedule for specific day
        if day_index < len(group_schedule):
            day_schedule = group_schedule[day_index]
        else:
            day_schedule = group_schedule[0] if group_schedule else []
        
        return day_schedule
    
    def get_hourly_schedule(self, region: str, group: str, day_index: int = 0) -> List[Dict]:
        """
        Convert YASNO time ranges to hourly schedule
        
        Returns:
            List of dicts with hour and blackout status
        """
        raw_schedule = self.get_schedule_for_group(region, group, day_index)
        
        # Initialize all hours as having electricity
        hourly = [{'hour': h, 'blackout': False, 'type': 'ELECTRICITY'} for h in range(24)]
        
        for slot in raw_schedule:
            start = slot.get('start', 0)
            end = slot.get('end', 0)
            outage_type = slot.get('type', 'POSSIBLE_OUTAGE')
            
            # Mark hours within range as potential blackout
            start_hour = int(start)
            end_hour = int(end) if end <= 24 else 24
            
            for h in range(start_hour, end_hour):
                if h < 24:
                    hourly[h]['blackout'] = True
                    hourly[h]['type'] = outage_type
        
        return hourly
    
    def get_current_status(self, region: str, group: str) -> Dict:
        """
        Get current electricity status for region/group
        
        Returns:
            Dict with current status info
        """
        now = datetime.now()
        current_hour = now.hour + now.minute / 60  # Include fractional hour
        
        # Get today's schedule
        hourly = self.get_hourly_schedule(region, group, day_index=0)
        raw_schedule = self.get_schedule_for_group(region, group, day_index=0)
        
        # Check if currently in blackout window
        is_blackout = False
        current_slot_type = 'ELECTRICITY'
        
        for slot in raw_schedule:
            start = slot.get('start', 0)
            end = slot.get('end', 0)
            if start <= current_hour < end:
                is_blackout = True
                current_slot_type = slot.get('type', 'POSSIBLE_OUTAGE')
                break
        
        # Find next blackout
        next_blackout = None
        for slot in raw_schedule:
            start = slot.get('start', 0)
            if start > current_hour:
                next_blackout = start
                break
        
        # Find when power returns (if currently in blackout)
        next_power_on = None
        if is_blackout:
            for slot in raw_schedule:
                end = slot.get('end', 0)
                if end > current_hour:
                    next_power_on = end
                    break
        
        return {
            'region': region,
            'group': group,
            'current_hour': int(current_hour),
            'is_blackout': is_blackout,
            'status_type': current_slot_type,
            'status': 'no_electricity' if is_blackout else 'has_electricity',
            'next_blackout_hour': next_blackout,
            'next_power_on_hour': next_power_on,
            'schedule': hourly,
            'raw_schedule': raw_schedule,
            'last_update': now.isoformat(),
        }
    
    def get_schedule_for_address(self, city: str, group: Optional[str] = None) -> Dict:
        """
        Get schedule for city and optional group
        
        Args:
            city: City name (Київ, Дніпро, etc.)
            group: Optional group like '1.1', '2.2'. If not provided, returns all groups.
        
        Returns:
            Schedule data dict
        """
        region = self.city_to_region(city)
        
        if not region:
            return {
                'found': False,
                'error': f'Місто "{city}" не підтримується. Доступні: Київ, Дніпро',
                'available_cities': ['Київ', 'Дніпро']
            }
        
        data = self._get_data()
        if not data:
            return {
                'found': False,
                'error': 'Не вдалося отримати дані з YASNO API'
            }
        
        schedule_component = self.get_schedule_component(data)
        last_update = schedule_component.get('lastRegistryUpdateTime', 0) if schedule_component else 0
        last_update_dt = datetime.fromtimestamp(last_update) if last_update else datetime.now()
        
        if group:
            # Return specific group
            status = self.get_current_status(region, group)
            return {
                'found': True,
                'city': city,
                'region': region,
                'group': group,
                'provider': 'YASNO (DTEK)',
                'source': 'yasno_api',
                'last_update': last_update_dt.isoformat(),
                **status
            }
        else:
            # Return all groups for region
            available_groups = self.get_groups_for_region(region)
            return {
                'found': True,
                'city': city,
                'region': region,
                'provider': 'YASNO (DTEK)',
                'source': 'yasno_api',
                'available_groups': available_groups,
                'last_update': last_update_dt.isoformat(),
            }


# Singleton instance
yasno_api = YasnoAPI()


def get_yasno_schedule(city: str, group: Optional[str] = None) -> Dict:
    """Convenience function to get YASNO schedule"""
    return yasno_api.get_schedule_for_address(city, group)


def get_yasno_current_status(city: str, group: str) -> Dict:
    """Get current status for city and group"""
    region = yasno_api.city_to_region(city)
    if not region:
        return {'error': f'Місто {city} не підтримується'}
    return yasno_api.get_current_status(region, group)


# Test
if __name__ == '__main__':
    # Test API
    print("Testing YASNO API...")
    
    # Get schedule for Kyiv, group 1.1
    result = get_yasno_schedule('Київ', '1.1')
    print(f"\nKyiv 1.1 status: {result.get('status')}")
    print(f"Is blackout: {result.get('is_blackout')}")
    print(f"Next blackout: {result.get('next_blackout_hour')}")
    
    # Get all groups for Kyiv
    result = get_yasno_schedule('Київ')
    print(f"\nAvailable groups for Kyiv: {result.get('available_groups')}")
    
    # Test Dnipro
    result = get_yasno_schedule('Дніпро', '2.1')
    print(f"\nDnipro 2.1 status: {result.get('status')}")

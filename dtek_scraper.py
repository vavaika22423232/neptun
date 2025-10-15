"""
DTEK Web Scraper - extracts blackout schedules from DTEK websites
Since DTEK doesn't provide public API, we use web scraping
"""

import requests
from bs4 import BeautifulSoup
import json
import logging
from typing import Dict, List, Optional
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DTEKScraper:
    """Scraper for DTEK power company websites"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'uk-UA,uk;q=0.9,en;q=0.8',
        })
        
        # DTEK regional websites
        self.dtek_sites = {
            'kyiv': {
                'url': 'https://www.dtek-krem.com.ua/ua/shutdowns',
                'name': 'ДТЕК Київські електромережі',
                'regions': ['Київ', 'Київська']
            },
            'odesa': {
                'url': 'https://www.dtek-oem.com.ua/ua/shutdowns',
                'name': 'ДТЕК Одеські електромережі',
                'regions': ['Одеса', 'Одеська']
            },
            'dnipro': {
                'url': 'https://www.dtek-dnem.com.ua/ua/shutdowns',
                'name': 'ДТЕК Дніпровські електромережі',
                'regions': ['Дніпро', 'Дніпропетровська']
            },
            'donetsk': {
                'url': 'https://www.dtek-donec.com.ua/ua/shutdowns',
                'name': 'ДТЕК Донецькі електромережі',
                'regions': ['Донецька', 'Маріуполь']
            }
        }
    
    def search_address_dtek(self, city: str, street: str = None, building: str = None, region='kyiv') -> Optional[Dict]:
        """
        Search for address in DTEK database
        This would normally make a POST request to their search API
        
        Example from DTEK site:
        POST https://www.dtek-krem.com.ua/ua/ajax/shutdowns/search
        Data: {city: "Київ", street: "Хрещатик", building: "1"}
        """
        
        site_info = self.dtek_sites.get(region)
        if not site_info:
            logger.error(f"Unknown DTEK region: {region}")
            return None
        
        try:
            # Try to find the AJAX endpoint for address search
            # DTEK usually uses endpoints like /ajax/shutdowns/search
            base_url = site_info['url'].rsplit('/', 1)[0]
            search_url = f"{base_url}/ajax/shutdowns/search"
            
            payload = {
                'city': city,
                'street': street or '',
                'building': building or ''
            }
            
            logger.info(f"Searching DTEK {region}: {payload}")
            
            response = self.session.post(
                search_url,
                data=payload,
                timeout=10,
                allow_redirects=True
            )
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    return data
                except json.JSONDecodeError:
                    # Try to parse HTML if not JSON
                    return self._parse_html_response(response.text)
            else:
                logger.warning(f"DTEK search returned {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error searching DTEK: {e}")
            return None
    
    def _parse_html_response(self, html: str) -> Optional[Dict]:
        """Parse HTML response from DTEK"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Look for queue/group information
            queue_element = soup.find(text=re.compile(r'Черга|Група', re.IGNORECASE))
            if queue_element:
                # Extract queue number (e.g., "Черга 2.1")
                queue_match = re.search(r'(\d+\.\d+|\d+)', queue_element)
                if queue_match:
                    return {'queue': queue_match.group(1)}
            
            return None
        except Exception as e:
            logger.error(f"Error parsing HTML: {e}")
            return None
    
    def get_schedule_for_queue(self, queue: str, region='kyiv') -> List[Dict]:
        """
        Get blackout schedule for specific queue from DTEK
        
        Queue format: "1.1", "2.1", "3.2" etc.
        """
        site_info = self.dtek_sites.get(region)
        if not site_info:
            return []
        
        try:
            # DTEK usually publishes schedules as tables or graphics
            # We need to scrape the schedule page
            response = self.session.get(site_info['url'], timeout=10)
            
            if response.status_code == 200:
                return self._parse_schedule_from_html(response.text, queue)
            
        except Exception as e:
            logger.error(f"Error getting schedule: {e}")
        
        return []
    
    def _parse_schedule_from_html(self, html: str, queue: str) -> List[Dict]:
        """Parse schedule table from DTEK HTML"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # DTEK typically shows schedules in tables
            # Look for the queue-specific schedule
            schedule = []
            
            # This is a placeholder - actual implementation would depend on DTEK's HTML structure
            # You would need to inspect their page and extract the specific schedule format
            
            logger.info(f"Parsing schedule for queue {queue}")
            
            # Return empty for now - need to implement based on actual DTEK HTML structure
            return schedule
            
        except Exception as e:
            logger.error(f"Error parsing schedule HTML: {e}")
            return []
    
    def get_all_addresses_for_city(self, city: str, region='kyiv') -> List[Dict]:
        """
        Get list of all addresses/streets available in DTEK database for a city
        This would be used for autocomplete
        """
        # This would require accessing DTEK's address database
        # Possibly through their autocomplete API endpoint
        
        site_info = self.dtek_sites.get(region)
        if not site_info:
            return []
        
        try:
            # DTEK might have an autocomplete endpoint like:
            # GET /ajax/shutdowns/autocomplete?term=Київ
            base_url = site_info['url'].rsplit('/', 1)[0]
            autocomplete_url = f"{base_url}/ajax/shutdowns/autocomplete"
            
            response = self.session.get(
                autocomplete_url,
                params={'term': city},
                timeout=10
            )
            
            if response.status_code == 200:
                try:
                    return response.json()
                except:
                    return []
            
        except Exception as e:
            logger.error(f"Error getting addresses: {e}")
        
        return []


# Global instance
dtek_scraper = DTEKScraper()


# Test function
if __name__ == "__main__":
    # Test searching an address
    result = dtek_scraper.search_address_dtek(
        city="Київ",
        street="Хрещатик",
        building="1",
        region='kyiv'
    )
    print(f"Search result: {result}")

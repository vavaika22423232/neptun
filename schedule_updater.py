"""
Автоматичне оновлення графіків відключень з ДТЕК та Укренерго.
Запускається кожну годину у фоновому режимі.
"""

import logging
import requests
from datetime import datetime
from typing import Dict, List, Any
from dtek_scraper import DTEKScraper

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ScheduleUpdater:
    """Клас для автоматичного оновлення графіків відключень"""
    
    def __init__(self):
        self.dtek_scraper = DTEKScraper()
        self.schedules_cache = {}
        self.last_update = None
        
        # ДТЕК регіони
        self.dtek_regions = {
            'kyiv': 'https://www.dtek-krem.com.ua',
            'odesa': 'https://www.dtek-oem.com.ua', 
            'dnipro': 'https://www.dtek-dnem.com.ua',
            'donetsk': 'https://www.dtek-donec.com.ua'
        }
        
        # Укренерго API
        self.ukrenergo_api = 'https://www.ukrenergo.energy/api'
    
    def update_all_schedules(self):
        """Оновлення всіх графіків з усіх джерел"""
        logger.info(f"🔄 Starting schedule update at {datetime.now()}")
        
        try:
            # Оновлення графіків ДТЕК
            dtek_schedules = self._update_dtek_schedules()
            
            # Оновлення графіків Укренерго
            ukrenergo_schedules = self._update_ukrenergo_schedules()
            
            # Об'єднання даних
            self.schedules_cache = {
                'dtek': dtek_schedules,
                'ukrenergo': ukrenergo_schedules,
                'last_update': datetime.now().isoformat()
            }
            
            self.last_update = datetime.now()
            logger.info(f"✅ Schedule update completed successfully")
            logger.info(f"   DTEK regions: {len(dtek_schedules)}")
            logger.info(f"   Ukrenergo data: {'available' if ukrenergo_schedules else 'not available'}")
            
            return self.schedules_cache
            
        except Exception as e:
            logger.error(f"❌ Error updating schedules: {e}")
            return None
    
    def _update_dtek_schedules(self) -> Dict[str, Any]:
        """Оновлення графіків з ДТЕК сайтів"""
        dtek_data = {}
        
        for region, base_url in self.dtek_regions.items():
            try:
                logger.info(f"  Fetching DTEK {region}...")
                
                # Отримання графіків для всіх черг
                region_schedules = {}
                for subgroup in ['1.1', '1.2', '2.1', '2.2', '3.1', '3.2']:
                    schedule = self.dtek_scraper.get_schedule_for_queue(subgroup, region)
                    if schedule:
                        region_schedules[subgroup] = schedule
                
                if region_schedules:
                    dtek_data[region] = region_schedules
                    logger.info(f"    ✓ {region}: {len(region_schedules)} subgroups")
                else:
                    logger.warning(f"    ⚠ {region}: No schedules found")
                    
            except Exception as e:
                logger.error(f"    ✗ {region}: {e}")
                continue
        
        return dtek_data
    
    def _update_ukrenergo_schedules(self) -> Dict[str, Any]:
        """Оновлення даних з Укренерго API"""
        try:
            logger.info("  Fetching Ukrenergo data...")
            
            # Спроба отримати дані з різних endpoints Укренерго
            endpoints = [
                '/outages',
                '/schedule',
                '/power-system-status'
            ]
            
            for endpoint in endpoints:
                try:
                    url = f"{self.ukrenergo_api}{endpoint}"
                    response = requests.get(url, timeout=10)
                    
                    if response.status_code == 200:
                        data = response.json()
                        logger.info(f"    ✓ Ukrenergo {endpoint}: success")
                        return data
                        
                except Exception as e:
                    logger.debug(f"    - Ukrenergo {endpoint}: {e}")
                    continue
            
            logger.warning("    ⚠ Ukrenergo: No data available from any endpoint")
            return {}
            
        except Exception as e:
            logger.error(f"    ✗ Ukrenergo error: {e}")
            return {}
    
    def get_schedule_for_address(self, city: str, street: str, building: str, region: str = None) -> Dict[str, Any]:
        """
        Отримання актуального графіка для конкретної адреси
        
        Args:
            city: Місто/село
            street: Вулиця
            building: Будинок
            region: Регіон (kyiv, odesa, dnipro, donetsk)
        
        Returns:
            Графік відключень для адреси
        """
        try:
            # Якщо регіон не вказано, спробуємо визначити по місту
            if not region:
                region = self._detect_region(city)
            
            # Пошук адреси в ДТЕК
            result = self.dtek_scraper.search_address_dtek(city, street, building, region)
            
            if result and 'queue' in result:
                queue = result['queue']
                
                # Отримання актуального графіка з кешу
                if region in self.schedules_cache.get('dtek', {}):
                    if queue in self.schedules_cache['dtek'][region]:
                        schedule = self.schedules_cache['dtek'][region][queue]
                        return {
                            'queue': queue,
                            'schedule': schedule,
                            'region': region,
                            'provider': result.get('provider', 'ДТЕК'),
                            'last_update': self.last_update.isoformat() if self.last_update else None
                        }
            
            # Якщо не знайдено в кеші, отримуємо напряму
            schedule = self.dtek_scraper.get_schedule_for_queue(result.get('queue', '1.1'), region)
            
            return {
                'queue': result.get('queue', 'unknown'),
                'schedule': schedule,
                'region': region,
                'provider': result.get('provider', 'unknown'),
                'last_update': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting schedule for address: {e}")
            return {}
    
    def _detect_region(self, city: str) -> str:
        """Визначення регіону по назві міста"""
        city_lower = city.lower()
        
        # Київ та область
        if any(name in city_lower for name in ['київ', 'kyiv', 'буча', 'ірпінь', 'бориспіль', 'бровари']):
            return 'kyiv'
        
        # Одеса та область
        if any(name in city_lower for name in ['одес', 'odesa', 'чорноморськ', 'южне', 'лиманка']):
            return 'odesa'
        
        # Дніпро та область
        if any(name in city_lower for name in ['дніпро', 'dnipro', 'кривий ріг', 'нікополь', 'кам\'янське']):
            return 'dnipro'
        
        # Донецька область
        if any(name in city_lower for name in ['маріуполь', 'краматорськ', 'слов\'янськ', 'покровськ']):
            return 'donetsk'
        
        # За замовчуванням Київ
        return 'kyiv'
    
    def get_cached_schedules(self) -> Dict[str, Any]:
        """Отримання кешованих графіків"""
        return self.schedules_cache
    
    def is_cache_valid(self, max_age_hours: int = 1) -> bool:
        """Перевірка чи актуальний кеш"""
        if not self.last_update:
            return False
        
        age = (datetime.now() - self.last_update).total_seconds() / 3600
        return age < max_age_hours


# Глобальний екземпляр
schedule_updater = ScheduleUpdater()


def start_schedule_updates():
    """Запуск першого оновлення"""
    logger.info("🚀 Starting initial schedule update...")
    schedule_updater.update_all_schedules()

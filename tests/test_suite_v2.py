import unittest
from unittest.mock import MagicMock, patch
import sys
import os
import json
import asyncio

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.parser_v2 import parse_message
from api import app

class TestParserAdvanced(unittest.TestCase):
    """
    Test the Deterministic Parsing Pipeline (core/parser_v2.py)
    """
    def test_basic_classification(self):
        inputs = [
            ("‼️ Ракета", "missile"),
            ("🛵 Шахед", "uav"),
            ("✈️ Активність авіації", "kab"),
            ("Вибух у місті", "explosion")
        ]
        for text, expected in inputs:
            e = parse_message(text)
            self.assertEqual(e.type, expected, f"Failed on '{text}'")

    def test_oblast_authority_extraction(self):
        inputs = [
            ("Шахед на Чернігівську обл", "Чернігівська область"),
            ("(Київська область) Ракетна небезпека", "Київська область"),
            ("Загроза на Сумщині", "Сумська область"),
            ("Дніпропетровщина - увага", "Дніпропетровська область")
        ]
        for text, expected in inputs:
            e = parse_message(text)
            self.assertEqual(e.region, expected, f"Region extraction failed on '{text}'")

    def test_location_resolution_strict(self):
        # 1. Frontline City with Explicit Region
        e = parse_message("КАБ на Покровськ (Донецька обл)")
        self.assertEqual(e.location, "Покровськ")
        self.assertEqual(e.region, "Донецька область")
        
        # 2. Region Center via Fallback (if no city found matching text EXACTLY)
        # "Чернігівську обл" -> matches "Чернігів" city inside? 
        # Yes, "Чернігів" is in "Чернігівську" if we aren't careful with boundaries
        # But we added \b boundaries. "Чернігів" is typically NOT in "Чернігівську" (suffix mismatch)
        # So it might fall back to region center, which IS "Чернігів".
        e = parse_message("Шахед на Чернігівську обл")
        self.assertEqual(e.location, "Чернігів") 

        # 3. Global Unique City (No Region)
        e = parse_message("Ракета на Київ")
        self.assertEqual(e.location, "Київ")

    def test_noise_filtering(self):
        # "Kurs" and "Pivnich" should be ignored, not detected as locations
        text = "БПЛА курс Північ"
        e = parse_message(text)
        # Should NOT map "Pivnich" to a city (unless it exists in our DB, which it shouldn't for now)
        self.assertNotEqual(e.location, "Північ")
        
    def test_transliteration_or_typos(self):
        # Our DB only has correct Ukrainian names.
        # "Kyyiv" or "Kyiv" in latin might fail if not prepared.
        # Current v2 only handles Cyrillic.
        pass

class TestAPIRoutes(unittest.TestCase):
    """
    Test the Flask API Endpoints (api.py)
    """
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
        
    @patch('api.db')
    def test_health_check(self, mock_db):
        mock_db.is_connected.return_value = True
        response = self.app.get('/health')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['redis'], 'connected')

    @patch('api.db')
    def test_get_alerts_filtering(self, mock_db):
        # Mock Redis return
        mock_threats = [
            {'id': '1', 'region': 'Kyivska', 'type': 'uav'},
            {'id': '2', 'region': 'Odeska', 'type': 'missile'}
        ]
        
        # Setup side_effect to simulate filtering logic roughly or just return all
        # In api.py, filtering happens inside get_active_threats
        mock_db.get_active_threats.return_value = [mock_threats[0]] # Simulate filter result
        
        response = self.app.get('/api/alerts?region=Kyivska')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data['alerts']), 1)
        self.assertEqual(data['alerts'][0]['region'], 'Kyivska')
        
    @patch('api.db')
    def test_map_endpoint(self, mock_db):
        mock_db.get_active_threats.return_value = []
        response = self.app.get('/api/map')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('meta', data)
        self.assertEqual(data['meta']['source'], 'neptun_v2')

if __name__ == '__main__':
    unittest.main()

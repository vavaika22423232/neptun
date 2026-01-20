"""
Pytest configuration and fixtures.
"""
import os
import sys

import pytest

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(scope="session")
def sample_city_coords():
    """Sample city coordinates for testing."""
    return {
        'київ': (50.4501, 30.5234),
        'харків': (49.9935, 36.2304),
        'одеса': (46.4825, 30.7233),
        'дніпро': (48.4647, 35.0462),
        'львів': (49.8397, 24.0297),
        'запоріжжя': (47.8388, 35.1396),
        'миколаїв': (46.9750, 31.9946),
        'херсон': (46.6354, 32.6169),
        'полтава': (49.5883, 34.5514),
        'чернігів': (51.4982, 31.2893),
    }


@pytest.fixture(scope="session")
def sample_regions():
    """Sample Ukrainian regions."""
    return [
        "Київська область",
        "Харківська область",
        "Одеська область",
        "Дніпропетровська область",
        "Львівська область",
        "Запорізька область",
        "Миколаївська область",
        "Херсонська область",
        "Полтавська область",
        "Чернігівська область",
    ]


@pytest.fixture
def sample_telegram_messages():
    """Sample Telegram messages for testing."""
    return [
        {
            'text': "⚠️ Шахеди над Черкаською областю, курс на Київ!",
            'expected_threat': 'shahed',
            'expected_region': 'Черкаська',
        },
        {
            'text': "🚀 Пуск крилатих ракет з акваторії Чорного моря",
            'expected_threat': 'cruise_missile',
            'expected_region': None,
        },
        {
            'text': "Балістична загроза! Харківська область!",
            'expected_threat': 'ballistic',
            'expected_region': 'Харківська',
        },
        {
            'text': "Група БПЛА (5 од.) напрямок Полтава",
            'expected_threat': 'shahed',
            'expected_count': 5,
        },
        {
            'text': "Кінжал! Час підльоту 2 хвилини!",
            'expected_threat': 'kinzhal',
            'expected_region': None,
        },
    ]


@pytest.fixture
def mock_alarm_response():
    """Mock response from ukrainealarm.com API."""
    return {
        "states": [
            {
                "id": 31,
                "name": "Київська область",
                "type": "state",
                "activeAlerts": [
                    {"type": "AIR", "regionType": "State"}
                ]
            },
            {
                "id": 14,
                "name": "Харківська область",
                "type": "state",
                "activeAlerts": []
            },
        ]
    }


@pytest.fixture
def clean_environment(monkeypatch):
    """Clean environment for testing."""
    # Remove sensitive env vars during tests
    monkeypatch.delenv("TELEGRAM_API_ID", raising=False)
    monkeypatch.delenv("TELEGRAM_API_HASH", raising=False)
    monkeypatch.delenv("ALARM_API_KEY", raising=False)
    monkeypatch.delenv("ADMIN_SECRET", raising=False)


# Markers for test categories
def pytest_configure(config):
    config.addinivalue_line("markers", "slow: marks tests as slow")
    config.addinivalue_line("markers", "integration: marks integration tests")
    config.addinivalue_line("markers", "api: marks API tests")

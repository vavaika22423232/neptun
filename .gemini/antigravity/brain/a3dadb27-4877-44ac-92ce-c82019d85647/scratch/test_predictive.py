import sys
import os
import asyncio
import logging

# Add worker to path
sys.path.append(os.path.join(os.getcwd(), 'nextjs-app', 'worker'))

os.environ['TG_API_ID'] = '123'
os.environ['TG_API_HASH'] = 'abc'
os.environ['DOMAIN_LLM_BACKEND'] = 'none'

from geo.resolver import resolve
from core.parser_v2 import ParsedEntities

# Mock logging
logging.basicConfig(level=logging.INFO)

async def test_predictive_resolution():
    print("--- Testing Target-Only Resolution ---")
    # Message: "Шахеди в напрямку Києва"
    # Entities from parser (simulated)
    entities = {
        'event_type': 'uav',
        'place_name': None,
        'target_city': 'Київ',
        'direction': 'на Київ'
    }
    
    res = resolve(entities)
    print(f"Resolved: {res.place_name} ({res.lat}, {res.lng})")
    print(f"Is Predictive: {res.is_predictive}")
    print(f"Status: {res.status}")

    # Now simulate worker logic
    # In worker.py, if res.is_predictive is True, coords are cleared and offset logic runs.
    
    # Simulate bearing extraction
    bearing = 135.0 # SE (heading to Kyiv from SE)
    
    from worker import _project_point
    if res.is_predictive:
        reverse_bearing = (bearing + 180) % 360
        new_lat, new_lng = _project_point(res.lat, res.lng, reverse_bearing, 12.0)
        print(f"Shifted Coords: {new_lat}, {new_lng} (Offset from {res.place_name})")

if __name__ == "__main__":
    asyncio.run(test_predictive_resolution())

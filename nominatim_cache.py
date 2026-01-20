"""
Persistent cache for Nominatim geocoding results
Автоматично зберігає знайдені координати міст
"""

import json
import os
from typing import Optional

CACHE_FILE = 'nominatim_cache.json'

def load_cache() -> dict:
    """Load cache from file"""
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Failed to load cache: {e}")
    return {}

def save_cache(cache: dict):
    """Save cache to file"""
    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Warning: Failed to save cache: {e}")

def get_from_cache(city: str, region: Optional[str] = None) -> Optional[tuple[float, float]]:
    """Get coordinates from cache"""
    cache = load_cache()
    key = f"{city}_{region or ''}"
    if key in cache:
        coords = cache[key]
        if coords:
            return tuple(coords)
    return None

def add_to_cache(city: str, coords: tuple[float, float], region: Optional[str] = None):
    """Add coordinates to cache"""
    cache = load_cache()
    key = f"{city}_{region or ''}"
    cache[key] = list(coords)
    save_cache(cache)
    print(f"✓ Cached: {city} -> {coords}")

def export_to_python_dict():
    """Export cache as Python dictionary for adding to CITY_COORDS"""
    cache = load_cache()
    if not cache:
        print("Cache is empty")
        return

    print("\n# === Auto-discovered cities from Nominatim API ===")
    for key, coords in sorted(cache.items()):
        city = key.split('_')[0]
        if coords:
            print(f"    '{city}': ({coords[0]}, {coords[1]}),")
    print("# === End of auto-discovered cities ===\n")

if __name__ == '__main__':
    print("Nominatim Cache Manager")
    print("=" * 50)
    cache = load_cache()
    print(f"Cache contains {len(cache)} entries")

    if cache:
        print("\nRecent entries:")
        for key, coords in list(cache.items())[-10:]:
            city = key.split('_')[0]
            print(f"  {city}: {coords}")

        print("\nTo export as Python dict, run:")
        print("  python3 -c 'from nominatim_cache import export_to_python_dict; export_to_python_dict()'")

import sys
sys.path.insert(0, '/Users/vladimirmalik/Desktop/render2')

# Import from app.py
from app import CITY_COORDS

def norm_city_token(tok: str) -> str:
    t = tok.lower().strip(" .,''ʼ`-:")
    t = t.replace("'", "'")
    if t.endswith('ку'): t = t[:-2] + 'ка'
    elif t.endswith('ву'): t = t[:-2] + 'ва'
    elif t.endswith('ову'): t = t[:-3] + 'ова'
    elif t.endswith('ого'): t = t[:-3] + 'ий'
    elif t.endswith('ю'): t = t[:-1] + 'я'
    elif t.endswith('у'): t = t[:-1] + 'а'
    if t.startswith('нову '):
        t = 'нова ' + t[5:]
    t = t.replace('водолагу','водолога')
    return t

cities_to_test = [
    'новий буг',
    'мошни',
    'корсунь-шевченківського',
    'гельмязів',
    'радушне'
]

print("Testing city coordinates lookup:")
print("=" * 60)

for city in cities_to_test:
    # Normalize
    normalized = norm_city_token(city)
    
    # Look up coordinates
    coords = CITY_COORDS.get(normalized)
    
    status = "✓ FOUND" if coords else "✗ NOT FOUND"
    coords_str = f"({coords[0]:.4f}, {coords[1]:.4f})" if coords else "N/A"
    
    print(f"{status}: '{city}' -> '{normalized}' -> {coords_str}")

print("=" * 60)

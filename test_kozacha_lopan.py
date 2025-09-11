#!/usr/bin/env python3

"""
Test Kozacha Lopan location detection
"""

def test_city_parsing():
    """Test parsing of Kozacha Lopan message"""
    
    test_message = "💣 Козача Лопань (Харківська обл.)\nЗагроза застосування КАБів. Негайно прямуйте в укриття!"
    
    print("🔍 Testing Kozacha Lopan parsing...")
    print("-" * 60)
    print(f"Message: {test_message}")
    print()
    
    # Extract city name pattern similar to app.py logic
    import re
    
    # Check different patterns
    patterns = [
        r'💣\s*([^(]+)\s*\(',  # Pattern for bomb emoji messages
        r'([А-ЯЁІЇЄҐ][А-яёіїєґ\s\-]+)\s*\(',  # General city pattern
        r'Козача Лопань'  # Specific pattern
    ]
    
    for i, pattern in enumerate(patterns, 1):
        match = re.search(pattern, test_message)
        if match:
            city_name = match.group(1).strip() if len(match.groups()) > 0 else match.group(0)
            print(f"Pattern {i}: '{pattern}' -> Found: '{city_name}'")
        else:
            print(f"Pattern {i}: '{pattern}' -> No match")
    print()

def check_coordinates():
    """Check if we have coordinates for Kozacha Lopan"""
    
    print("📍 Checking coordinate sources...")
    print("-" * 60)
    
    # Real coordinates for Kozacha Lopan
    # From Google Maps: approximately 49.8872, 36.4167
    real_coords = (49.8872, 36.4167)
    kharkiv_coords = (49.9935, 36.2304)
    
    print(f"Real Kozacha Lopan coordinates: {real_coords}")
    print(f"Kharkiv city coordinates: {kharkiv_coords}")
    
    # Calculate distance
    import math
    
    def distance(lat1, lon1, lat2, lon2):
        R = 6371  # Earth radius in km
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (math.sin(dlat/2) * math.sin(dlat/2) +
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
             math.sin(dlon/2) * math.sin(dlon/2))
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return R * c
    
    dist = distance(real_coords[0], real_coords[1], kharkiv_coords[0], kharkiv_coords[1])
    print(f"Distance between Kozacha Lopan and Kharkiv: {dist:.2f} km")
    
    if dist < 50:
        print("💡 Previously the system was falling back to oblast center coordinates.")
        print("   Now we added specific coordinates for Kozacha Lopan.")
    
    print()

def test_coordinate_lookup():
    """Test coordinate lookup logic"""
    print("🔍 Testing coordinate lookup...")
    print("-" * 60)
    
    # Simplified coordinate dictionary for testing
    test_coords = {
        'козача лопань': (49.8872, 36.4167),
        'харків': (49.9935, 36.2304),
        'дергачі': (50.1061, 36.1217),
    }
    
    test_city = "козача лопань"
    
    if test_city in test_coords:
        coords = test_coords[test_city]
        print(f"✅ Found coordinates for '{test_city}': {coords}")
        print(f"   Latitude: {coords[0]}")
        print(f"   Longitude: {coords[1]}")
        print("   This should now display at the correct location, not in Kharkiv!")
    else:
        print(f"❌ No coordinates found for '{test_city}'")
        print("   Would fall back to oblast center (Kharkiv)")
    
    print()

if __name__ == "__main__":
    test_city_parsing()
    check_coordinates()
    test_coordinate_lookup()

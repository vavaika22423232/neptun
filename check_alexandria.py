#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(__file__))

from app import CITY_COORDS

def check_alexandria_entries():
    """Check all Alexandria entries in CITY_COORDS"""
    
    print("=== Alexandria entries in CITY_COORDS ===")
    
    # Look for all variants of Alexandria
    alexandria_variants = []
    for city_name, coords in CITY_COORDS.items():
        if 'олександр' in city_name.lower():
            alexandria_variants.append((city_name, coords))
    
    print(f"Found {len(alexandria_variants)} Alexandria variants:")
    for name, coords in alexandria_variants:
        print(f"  '{name}': {coords}")
    
    print()
    
    # Check if Lutsk coordinates match any Alexandria
    lutsk_coords = (50.7472, 25.3254)
    print(f"Луцьк coordinates: {lutsk_coords}")
    
    for name, coords in alexandria_variants:
        if coords == lutsk_coords:
            print(f"⚠️  CONFLICT: '{name}' has same coordinates as Луцьк!")
        elif abs(coords[0] - lutsk_coords[0]) < 0.1 and abs(coords[1] - lutsk_coords[1]) < 0.1:
            print(f"⚠️  CLOSE: '{name}' is very close to Луцьк coordinates")
    
    print()
    
    # Expected Alexandria coordinates (Kirovohrad oblast)
    # Alexandria in Kirovohrad should be around (48.8, 33.1)
    print("Expected Alexandria (Kirovohrad) coordinates should be around (48.8, 33.1)")
    
    for name, coords in alexandria_variants:
        if abs(coords[0] - 48.8) < 1.0 and abs(coords[1] - 33.1) < 1.0:
            print(f"✅ CORRECT: '{name}' seems to be Alexandria in Kirovohrad oblast: {coords}")

if __name__ == "__main__":
    check_alexandria_entries()

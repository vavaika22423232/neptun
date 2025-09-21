#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Check what Zarichne entries we have in the database
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import CITY_COORDS

def check_zarichne_entries():
    """Check all Zarichne entries in database."""
    print("🔍 CHECKING ZARICHNE ENTRIES IN DATABASE")
    print("=" * 50)
    
    # Look for all entries containing "зарічне"
    zarichne_entries = []
    for key, coords in CITY_COORDS.items():
        if 'зарічне' in key.lower():
            zarichne_entries.append((key, coords))
    
    print(f"Found {len(zarichne_entries)} entries for 'зарічне':")
    for i, (key, coords) in enumerate(zarichne_entries, 1):
        lat, lng = coords
        print(f"  {i}. '{key}' -> ({lat}, {lng})")
        
        # Try to determine region based on coordinates
        if 48.0 <= lat <= 49.5 and 33.0 <= lng <= 36.0:
            region = "🏭 Днепропетровская область"
        elif 50.5 <= lat <= 51.5 and 25.0 <= lng <= 27.0:
            region = "🌾 Ровенская область"
        elif 50.0 <= lat <= 52.0 and 22.0 <= lng <= 26.0:
            region = "🏔️ Волынская область"
        else:
            region = "❓ Неопределенная область"
        
        print(f"       Примерная область: {region}")
    
    # Also check with different spellings
    print(f"\n🔍 Checking alternative spellings:")
    alternatives = ['заричне', 'зарiчне', 'заричне днепропетровская', 'зарічне днепропетровская', 'зарічне дніпропетровська']
    for alt in alternatives:
        if alt in CITY_COORDS:
            coords = CITY_COORDS[alt]
            print(f"  '{alt}' -> {coords}")

if __name__ == "__main__":
    check_zarichne_entries()

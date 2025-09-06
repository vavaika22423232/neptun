#!/usr/bin/env python3
import sys
sys.path.append('.')
import app

# Test simple district message (should hit early raion_oblast processing)
simple_district = '🛸 Конотопський район (Сумська обл.)\nКурс БПЛА. Прямуйте в укриття!'

print("=== SIMPLE DISTRICT TEST ===")
print(f"Message: {repr(simple_district)}")

result = app.process_message(simple_district, "test_simple", "2025-01-01 12:00:00", "test_channel")

if result and len(result) > 0:
    place = result[0].get('place', '')
    coords = (result[0].get('lat'), result[0].get('lng'))
    source_match = result[0].get('source_match', 'unknown')
    
    print(f"Place: {place}")
    print(f"Coordinates: {coords}")
    print(f"Source match: {source_match}")
    
    # Check if this hit raion_oblast_combo
    if source_match in ['raion_oblast_combo', 'raion_oblast_combo_early']:
        print("✅ SUCCESS: Hit early raion_oblast processing!")
    else:
        print("❌ FAILED: Did not hit early raion_oblast processing")
else:
    print("❌ FAILED: No result returned!")

print(f"\n=== RAION_FALLBACK CHECK ===")
if hasattr(app, 'RAION_FALLBACK'):
    konot_coords = app.RAION_FALLBACK.get('конотопський')
    print(f"'конотопський' in RAION_FALLBACK: {konot_coords}")
    
    sumy_coords = app.RAION_FALLBACK.get('сумський')  
    print(f"'сумський' in RAION_FALLBACK: {sumy_coords}")
else:
    print("RAION_FALLBACK not found")

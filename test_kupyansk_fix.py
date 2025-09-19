#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(__file__))

from app import process_message

def test_kupyansk_raion():
    """Test that Куп'янський район message creates marker in Kupiansk, not Kharkiv"""
    
    test_message = """🛸 Куп'янський район (Харківська обл.)
Загроза застосування БПЛА. Перейдіть в укриття!"""
    
    print("=== Testing Куп'янський район Message ===")
    print(f"Message: {test_message}")
    print()
    
    result = process_message(test_message, "test_kupyansk", "2025-09-16 20:39:39", "UkraineAlarmSignal")
    
    if result:
        print(f"Found {len(result)} markers:")
        for i, track in enumerate(result):
            print(f"{i+1}. {track['place']} at ({track['lat']:.4f}, {track['lng']:.4f}) - {track.get('source_match', 'unknown')}")
            print(f"   Text: {track['text'][:100]}...")
            print(f"   Threat type: {track['threat_type']}")
            print()
    else:
        print("No markers found")
    
    print("=== Expected Results ===")
    print("Should create marker in Куп'янськ area (49.7106, 37.6156), NOT in Харків (49.9935, 36.2304)")
    print()
    
    # Verify coordinates
    if result and len(result) > 0:
        track = result[0]
        kupiansk_lat, kupiansk_lng = 49.7106, 37.6156
        kharkiv_lat, kharkiv_lng = 49.9935, 36.2304
        
        # Check if closer to Kupiansk than to Kharkiv
        dist_to_kupiansk = ((track['lat'] - kupiansk_lat)**2 + (track['lng'] - kupiansk_lng)**2)**0.5
        dist_to_kharkiv = ((track['lat'] - kharkiv_lat)**2 + (track['lng'] - kharkiv_lng)**2)**0.5
        
        if dist_to_kupiansk < dist_to_kharkiv:
            print("✅ SUCCESS: Marker placed closer to Kupiansk than to Kharkiv")
        else:
            print("❌ FAILURE: Marker placed closer to Kharkiv than to Kupiansk")
        
        print(f"Distance to Kupiansk: {dist_to_kupiansk:.4f}")
        print(f"Distance to Kharkiv: {dist_to_kharkiv:.4f}")

if __name__ == "__main__":
    test_kupyansk_raion()

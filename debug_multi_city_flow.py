#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug script to trace the exact flow of multi-city message processing
"""

import sys
sys.path.append('/Users/vladimirmalik/Desktop/render2')

def debug_multi_city_flow():
    from app import process_message
    
    # Temporarily patch process_message to add debug prints
    import app
    
    # Store original function
    original_ensure_city_coords = app.ensure_city_coords
    original_ensure_city_coords_with_context = app.ensure_city_coords_with_message_context
    
    def debug_ensure_city_coords(name):
        print(f"🔍 ensure_city_coords called with: '{name}'")
        result = original_ensure_city_coords(name)
        print(f"   → returned: {result}")
        return result
    
    def debug_ensure_city_coords_with_context(name, message_text=""):
        print(f"🔍 ensure_city_coords_with_message_context called with: '{name}', message preview: '{message_text[:50]}...'")
        result = original_ensure_city_coords_with_context(name, message_text)
        print(f"   → returned: {result}")
        return result
    
    # Apply patches
    app.ensure_city_coords = debug_ensure_city_coords
    app.ensure_city_coords_with_message_context = debug_ensure_city_coords_with_context
    
    try:
        test_message = """🛸 Білозерка (Херсонська обл.)
Загроза застосування БПЛА. Перейдіть в укриття! | 🛸 Суми (Сумська обл.)
Загроза застосування БПЛА. Перейдіть в укриття!"""
        
        print("🔥 DEBUGGING MULTI-CITY MESSAGE PROCESSING")
        print("=" * 60)
        print(f"Message: {repr(test_message)}")
        print()
        
        results = process_message(test_message, "debug_multi", "2025-09-21 12:00:00", "test")
        
        print("\n📍 FINAL RESULTS:")
        if results:
            for i, marker in enumerate(results, 1):
                print(f"  {i}. {marker['place']} -> ({marker['lat']}, {marker['lng']}) [source: {marker.get('source_match', 'unknown')}]")
        else:
            print("  No markers created")
            
    finally:
        # Restore original functions
        app.ensure_city_coords = original_ensure_city_coords
        app.ensure_city_coords_with_message_context = original_ensure_city_coords_with_context

if __name__ == "__main__":
    debug_multi_city_flow()

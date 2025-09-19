#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(__file__))

from app import process_message, CITY_COORDS
import math

def test_bold_alexandria_message():
    """Test Alexandria message with bold formatting"""
    
    test_message = """**🛸 Олександрія (Кіровоградська обл.)** Загроза застосування БПЛА. Перейдіть в укриття! | БпЛА курсом на Олександрію"""
    
    print("=== Testing Bold Alexandria Message ===")
    print(f"Message: {test_message}")
    print()
    
    # Process the message
    result = process_message(test_message, 123, "test_channel", "test_channel")
    
    if result:
        print(f"Found {len(result)} markers:")
        for i, marker in enumerate(result):
            print(f"{i+1}. {marker['place']} at ({marker['lat']}, {marker['lng']}) - {marker['source_match']}")
            print(f"   Text: {marker['text'][:100]}...")
            print(f"   Threat type: {marker['threat_type']}")
            print()
        
        # Check coordinates
        print("=== Expected Results ===")
        print("Should create marker in Олександрія (Кіровоградська обл.), NOT in Луцьк")
        print()
        
        if 'олександрія' in CITY_COORDS:
            expected_coords = CITY_COORDS['олександрія']
            print(f"Expected Олександрія coordinates: {expected_coords}")
        
        if 'луцьк' in CITY_COORDS:
            lutsk_coords = CITY_COORDS['луцьк']
            print(f"Луцьк coordinates: {lutsk_coords}")
        
        # Calculate distances
        if result:
            marker = result[0]
            marker_lat, marker_lng = marker['lat'], marker['lng']
            
            if 'олександрія' in CITY_COORDS:
                alex_lat, alex_lng = CITY_COORDS['олександрія']
                alex_distance = math.sqrt((marker_lat - alex_lat)**2 + (marker_lng - alex_lng)**2)
                print(f"Distance to Олександрія: {alex_distance:.4f}")
            
            if 'луцьк' in CITY_COORDS:
                lutsk_lat, lutsk_lng = CITY_COORDS['луцьк']
                lutsk_distance = math.sqrt((marker_lat - lutsk_lat)**2 + (marker_lng - lutsk_lng)**2)
                print(f"Distance to Луцьк: {lutsk_distance:.4f}")
                
                if 'олександрія' in CITY_COORDS and alex_distance < lutsk_distance:
                    print("✅ SUCCESS: Marker placed closer to Alexandria than to Lutsk")
                else:
                    print("❌ FAILURE: Marker placed closer to Lutsk than to Alexandria")
    else:
        print("❌ No markers found!")

def test_formatting_processing():
    """Test how bold formatting affects processing"""
    
    test_message = """**🛸 Олександрія (Кіровоградська обл.)** Загроза застосування БПЛА. Перейдіть в укриття! | БпЛА курсом на Олександрію"""
    
    print("\n=== Testing Formatting Processing ===")
    print(f"Original: {test_message}")
    
    # Test how the system might process bold formatting
    processed = test_message.replace('**', '')
    print(f"Without bold: {processed}")
    
    # Test emoji structure detection
    import re
    
    # Look for emoji structure patterns
    emoji_pattern = r'🛸\s*([А-Яа-яЇїІіЄєҐґ\'\-\s]+?)\s*\(([^)]+)\)'
    match = re.search(emoji_pattern, test_message)
    
    if match:
        print(f"✅ Emoji structure matched: '{match.group(1)}' in '{match.group(2)}'")
        city_name = match.group(1).strip().lower()
        print(f"City name extracted: '{city_name}'")
    else:
        print("❌ Emoji structure pattern did not match")
    
    # Test course pattern
    course_pattern = r'курс(?:ом)?\s+на\s+([a-zа-яіїєґ\'ʼ\'`\-]{3,40})'
    course_match = re.search(course_pattern, test_message.lower())
    
    if course_match:
        print(f"✅ Course pattern matched: '{course_match.group(1)}'")
    else:
        print("❌ Course pattern did not match")

if __name__ == "__main__":
    test_bold_alexandria_message()
    test_formatting_processing()

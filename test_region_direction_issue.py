#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(__file__))

from app import process_message

def test_regional_direction_issue():
    """Test the specific issue where markers appear in region centers instead of target cities"""
    
    test_message = """🛵 Чернігівщина: група БпЛА ➡️ у напрямку Ніжина.
🛵 Полтавщина: БпЛА ➡️ через Диканьку. 
🛵 Харківщина: БпЛА ➡️ повз Слатине."""
    
    print("=== Testing Regional Direction Messages ===")
    print(f"Message: {test_message}")
    print()
    
    result = process_message(test_message, "test_123", "2025-09-16", "test_channel")
    
    if result:
        print(f"Found {len(result)} markers:")
        for i, track in enumerate(result):
            print(f"{i+1}. {track['place']} at ({track['lat']:.4f}, {track['lng']:.4f}) - {track.get('source_match', 'unknown')}")
            print(f"   Text: {track['text'][:100]}...")
            print()
    else:
        print("No markers found")
    
    print("=== Expected Results ===")
    print("1. Ніжин (not Чернігів)")
    print("2. Диканька (not Полтава)")  
    print("3. Слатине (not Харків)")
    print()
    
    # Test individual lines to see how they're processed
    print("=== Testing Individual Lines ===")
    test_lines = [
        "🛵 Чернігівщина: група БпЛА ➡️ у напрямку Ніжина.",
        "🛵 Полтавщина: БпЛА ➡️ через Диканьку.",
        "🛵 Харківщина: БпЛА ➡️ повз Слатине."
    ]
    
    for i, line in enumerate(test_lines):
        print(f"\nLine {i+1}: {line}")
        line_result = process_message(line, f"test_{i+1}", "2025-09-16", "test_channel")
        if line_result:
            for track in line_result:
                print(f"  → {track['place']} at ({track['lat']:.4f}, {track['lng']:.4f}) - {track.get('source_match', 'unknown')}")
        else:
            print("  → No markers")

if __name__ == "__main__":
    test_regional_direction_issue()

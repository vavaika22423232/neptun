#!/usr/bin/env python3
"""
Debug UAV parsing step by step
"""

import sys
import os
import re

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_uav_patterns():
    """Test individual UAV patterns"""
    
    test_message = """Чернігівщина:
3 БпЛА в районі Ніжина
1 БпЛА на Березну"""
    
    print("="*60)
    print("TESTING UAV PATTERNS")
    print("="*60)
    print(f"Message: {repr(test_message)}")
    print()
    
    lower = test_message.lower()
    print(f"Lower: {repr(lower)}")
    print()
    
    # Test basic conditions
    print("Basic checks:")
    print(f"  'бпла' in lower: {'бпла' in lower}")
    print(f"  'курс' in lower: {'курс' in lower}")
    print(f"  'в районі' in lower: {'в районі' in lower}")
    print(f"  UAV course condition: {'бпла' in lower and ('курс' in lower or 'в районі' in lower)}")
    print()
    
    # Test area pattern
    pat_area = re.compile(r'(\d+)?[xх]?\s*бпла\s+в\s+районі\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'\s]{3,40}?)(?=[,\.\n;:!\?]|$)', re.IGNORECASE)
    
    lines = test_message.split('\n')
    print("Line-by-line analysis:")
    for i, line in enumerate(lines):
        print(f"  Line {i}: {repr(line)}")
        
        # Check if line contains UAV
        if 'бпла' in line.lower():
            print(f"    Contains БпЛА: Yes")
            
            # Test area pattern
            matches = list(pat_area.finditer(line))
            print(f"    Area pattern matches: {len(matches)}")
            
            for match in matches:
                print(f"      Match: {match.groups()}")
                if match.group(1):
                    count = int(match.group(1))
                    city = match.group(2)
                else:
                    count = 1
                    city = match.group(2) if len(match.groups()) >= 2 else match.group(1)
                print(f"      Parsed: count={count}, city='{city}'")
            
            # Test course pattern
            pat_course = re.compile(r'бпла.*?на\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-'ʼ`\s]{3,40}?)(?=[,\.\n;:!\?]|$)', re.IGNORECASE)
            course_matches = list(pat_course.finditer(line))
            print(f"    Course pattern matches: {len(course_matches)}")
            
            for match in course_matches:
                print(f"      Course match: {match.groups()}")
                
        else:
            print(f"    Contains БпЛА: No")
        print()

if __name__ == "__main__":
    test_uav_patterns()

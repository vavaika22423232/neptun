#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re

# All patterns
pat_count_course = re.compile(
    r'^(\d+)\s*[xх]?\s*бпла(?:\s+пролетіли)?.*?курс(?:ом)?\s+на\s+(?:н\.п\.?\s*)?([A-Za-zА-Яа-яЇїІіЄєҐґ\-'ʼ`\s]{3,40}?)(?=[,\.\n;:!\?]|$)',
    re.IGNORECASE
)

pat_course = re.compile(
    r'бпла(?:\s+пролетіли)?.*?курс(?:ом)?\s+на\s+(?:н\.п\.?\s*)?([A-Za-zА-Яа-яЇїІіЄєҐґ\-'ʼ`\s]{3,40}?)(?=[,\.\n;:!\?]|$)',
    re.IGNORECASE
)

pat_sektor = re.compile(
    r'(\d+)?[xх]?\s*бпла\s+в\s+секторі\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,40}?)(?=[,\.\n;:!\?]|$)',
    re.IGNORECASE
)

# Test messages from user
test_msg = """3х БпЛА курсом на Васильківку	дніпропетровщина: 4х бпла в секторі павлоград. по інших областях без загроз.|napramok

БпЛА курсом на Петропавлівку	napramok"""

print("=" * 70)
print("FULL MESSAGE TEST")
print("=" * 70)
print(f"Message:\n{test_msg}\n")
print("=" * 70)

# Split by lines
lines = [l.strip() for l in test_msg.split('\n') if l.strip()]

for line in lines:
    print(f"\n📝 Line: {line}")
    lower = line.lower()
    
    # Check trigger
    has_bpla = 'бпла' in lower
    has_kurs = 'курс' in lower
    has_sektor = 'сектор' in lower
    
    print(f"   Triggers: бпла={has_bpla}, курс={has_kurs}, сектор={has_sektor}")
    
    if has_bpla and (has_kurs or has_sektor):
        print(f"   ✓ UAV course parser would be triggered")
        
        # Split by region
        if 'дніпропетровщина:' in lower:
            parts = line.split('дніпропетровщина:')
            region = 'дніпропетровщина'
            content_parts = parts[1].strip() if len(parts) > 1 else parts[0]
            print(f"   Region: {region}")
            print(f"   Content: {content_parts}")
            
            # Further split by semicolons or periods
            subparts = [p.strip() for p in re.split(r'[;\.]+', content_parts) if p.strip() and 'napramok' not in p]
            
            for subpart in subparts:
                print(f"\n   Subpart: {subpart}")
                sub_lower = subpart.lower()
                
                # Test patterns
                m1 = pat_count_course.search(sub_lower)
                if m1:
                    print(f"      ✓ pat_count_course: count={m1.group(1)}, city='{m1.group(2)}'")
                    continue
                
                m2 = pat_sektor.search(sub_lower)
                if m2:
                    print(f"      ✓ pat_sektor: count={m2.group(1)}, city='{m2.group(2)}'")
                    continue
                
                m3 = pat_course.search(sub_lower)
                if m3:
                    print(f"      ✓ pat_course: city='{m3.group(1)}'")
                    continue
                
                print(f"      ✗ No pattern matched")
        else:
            # No region, test directly
            m1 = pat_count_course.search(lower)
            if m1:
                print(f"   ✓ pat_count_course: count={m1.group(1)}, city='{m1.group(2)}'")
            else:
                m2 = pat_course.search(lower)
                if m2:
                    print(f"   ✓ pat_course: city='{m2.group(1)}'")
                else:
                    print(f"   ✗ No pattern matched")
    else:
        print(f"   ✗ Parser would NOT be triggered")

print("\n" + "=" * 70)

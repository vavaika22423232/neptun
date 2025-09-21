#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re

def test_region_patterns():
    """Test region name patterns."""
    regions = [
        "донеччини",    # problem case
        "харківщину",   # target case
        "полтавщини",   # should work
        "київщина",     # should work
        "черкащину",    # should work
    ]
    
    patterns = [
        r"[а-яіїєґ]+щин[ауиі]",           # current
        r"[а-яіїєґ]+[щч]чин[ауиі]",       # with double ch
        r"[а-яіїєґ]+(щин|ччин)[ауиі]",    # explicit alternatives
        r"[а-яіїєґ]+[щч]*ин[ауиі]",       # flexible
    ]
    
    for region in regions:
        print(f"\nTesting '{region}':")
        for i, pattern in enumerate(patterns, 1):
            match = re.search(pattern, region, re.IGNORECASE)
            print(f"  Pattern {i}: {'✅' if match else '❌'}")

if __name__ == "__main__":
    test_region_patterns()

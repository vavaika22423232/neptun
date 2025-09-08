#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Debug why Shahed multi-line parser is not working for Odesa line
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_detection_logic():
    print("=== Тестування логіки детекції багаторядкових Шахедів ===")
    
    test_message = """на одещині 10 шахедів на вилкове
на дніпропетровщина 1 шахед на чаплине"""
    
    text_lines = test_message.split('\n')
    print(f"Рядки: {text_lines}")
    
    # Перевіряємо region_count
    region_count = sum(1 for line in text_lines if any(region in line.lower() for region in ['щина:', 'щина]', 'область:', 'край:']) or (
        'щина' in line.lower() and line.lower().strip().endswith(':')
    ))
    print(f"region_count: {region_count}")
    
    # Перевіряємо shahed_region_lines
    shahed_region_lines = [line for line in text_lines if 
                          ('шахед' in line.lower() or 'shahed' in line.lower()) and 
                          ('щина' in line.lower() or 'щину' in line.lower() or 'щині' in line.lower())]
    shahed_count = len(shahed_region_lines)
    
    print(f"shahed_region_lines: {shahed_region_lines}")
    print(f"shahed_count: {shahed_count}")
    
    # Перевіряємо кожен рядок окремо
    for i, line in enumerate(text_lines, 1):
        print(f"\nРядок {i}: '{line}'")
        line_lower = line.lower()
        
        has_shahed = 'шахед' in line_lower or 'shahed' in line_lower
        has_region = 'щина' in line_lower or 'щину' in line_lower or 'щині' in line_lower
        
        print(f"  has_shahed: {has_shahed}")
        print(f"  has_region: {has_region}")
        print(f"  кваліфікується: {has_shahed and has_region}")
    
    # Умова спрацьовування
    should_trigger = shahed_count >= 2
    print(f"\nПовинен спрацювати багаторядковий парсер: {should_trigger} (shahed_count >= 2)")

if __name__ == "__main__":
    test_detection_logic()

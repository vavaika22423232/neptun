#!/usr/bin/env python3
# -*- coding: utf-8 -*-

def test_immediate_conditions():
    text = """🛵 Інформація щодо руху ворожих ударних БпЛА:
1. БпЛА з акваторії Чорного моря курсом на н.п.Вилково (Одещина);
2. БпЛА на сході Чернігівщини курсом на н.п.Батурин.
3. БпЛА на південному заході Дніпропетровщини, курс - південно-західний/південно-східний."""
    
    import re
    
    # Підрахунок регіонів
    OBLAST_CENTERS = {
        'Одеська область': (46.5197, 30.7495),
        'Чернігівська область': (51.4982, 31.3044),
        'Дніпропетровська область': (48.45, 35.0),
    }
    
    text_lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
    
    # Region counting logic (improved to match app.py)
    region_mentions = sum(1 for line in text_lines if any(region in line.lower() for region in ['щина:', 'щина]', 'область:', 'край:']) or (
        'щина' in line.lower() and line.lower().strip().endswith(':')
    ) or any(region in line.lower() for region in ['щина)', 'щини', 'щину', 'одещина', 'чернігівщина', 'дніпропетровщина', 'харківщина', 'київщина']))
    
    # UAV counting logic
    uav_lines = [line for line in text_lines if 'бпла' in line.lower() and ('курс' in line.lower() or 'на ' in line.lower())]
    
    print("=== Аналіз умов для immediate multi-regional ===")
    print(f"Рядки:")
    for i, line in enumerate(text_lines, 1):
        print(f"  {i}. {line}")
    
    print(f"\nРегіони згадані: {region_mentions}")
    print(f"UAV рядки (з 'бпла' + ('курс' або 'на')): {len(uav_lines)}")
    for i, line in enumerate(uav_lines, 1):
        print(f"  UAV{i}: {line}")
    
    print(f"\nУмова immediate multi-regional:")
    print(f"  region_count >= 2: {region_mentions >= 2} (actual: {region_mentions})")
    print(f"  uav_lines >= 3: {len(uav_lines) >= 3} (actual: {len(uav_lines)})")
    print(f"  Overall condition: {region_mentions >= 2 and len(uav_lines) >= 3}")

if __name__ == "__main__":
    test_immediate_conditions()

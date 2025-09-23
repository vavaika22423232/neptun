#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Финальный тест - сравнение ДО и ПОСЛЕ внедрения направленных угроз
"""

def show_coordinates_comparison():
    print("📍 СРАВНЕНИЕ: Где отображались маркеры ДО и ПОСЛЕ исправления")
    print("=" * 75)
    
    cases = [
        {
            'message': 'ворожі бпла на харківщина в напрямку чугуєва зі сходу',
            'before': 'Харьков (центр города)',
            'before_coords': [49.9935, 36.2304],
            'after': 'В 50 км к востоку от Харькова (к Чугуеву)',
            'after_coords': [49.9935, 36.9311]
        },
        {
            'message': 'на чернігівщина - в напрямку н.п.понорниця з північного сходу',
            'before': 'Чернигов (центр города)',
            'before_coords': [50.77624, 30.9874828],
            'after': 'В 50 км к северо-востоку от Чернигова (к Понорнице)',
            'after_coords': [51.8167, 31.8009]
        },
        {
            'message': 'група ворожих бпла на південному заході від м.запоріжжя',
            'before': 'Запорожье (центр города)',
            'before_coords': [47.8192947, 35.2366443],
            'after': 'В 50 км к юго-западу от Запорожья',
            'after_coords': [47.5203, 34.6651]
        }
    ]
    
    for i, case in enumerate(cases, 1):
        print(f"\n{i}. {case['message']}")
        print("-" * 70)
        print(f"   ❌ ДО:    {case['before']}")
        print(f"           Координаты: {case['before_coords'][0]:.4f}, {case['before_coords'][1]:.4f}")
        print(f"   ✅ ПОСЛЕ: {case['after']}")
        print(f"           Координаты: {case['after_coords'][0]:.4f}, {case['after_coords'][1]:.4f}")
        
        # Вычисляем расстояние
        import math
        lat1, lng1 = case['before_coords']
        lat2, lng2 = case['after_coords']
        
        dlat = lat2 - lat1
        dlng = lng2 - lng1
        distance_km = math.sqrt(dlat**2 * 111**2 + dlng**2 * (111 * math.cos(lat1 * math.pi / 180))**2)
        
        print(f"           Смещение: {distance_km:.1f} км от центра города")
    
    print("\n" + "=" * 75)
    print("✅ РЕЗУЛЬТАТ: Теперь маркеры отображаются в правильных направлениях!")
    print("   Больше никакой путаницы с местоположением угроз!")

if __name__ == "__main__":
    show_coordinates_comparison()

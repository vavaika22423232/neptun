#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест для перевірки всіх міст з повідомлення
"""

# Міста з повідомлення
cities_from_message = [
    'шостка', 'ямпіль', 'хутір-михайлівський', 'буринь', "дубов'язівка", 'конотоп', 'терни',
    'понорниця', 'холми', 'ічня', 'ніжин', 'носівка', 'олишівка',
    'макарів', 'житомир', 'берестин', 'краснопавлівка', 'савинці', 'балаклія',
    'нові санжари', 'полтава'
]

def main():
    print("Перевірка міст з повідомлення...")
    print("=" * 50)
    
    # Імпортуємо функції з app.py
    import app
    
    missing_cities = []
    found_cities = []
    
    for city in cities_from_message:
        # Нормалізуємо назву
        normalized = app.normalize_city_name(city) if hasattr(app, 'normalize_city_name') else city.lower().strip()
        
        # Перевіряємо через UA_CITY_NORMALIZE
        if normalized in app.UA_CITY_NORMALIZE:
            normalized = app.UA_CITY_NORMALIZE[normalized]
        
        # Перевіряємо координати
        coords = app.ensure_city_coords(normalized)
        if coords:
            lat, lng, approx = coords
            approx_text = " (approximate)" if approx else ""
            found_cities.append(city)
            print(f"✅ {city} -> {normalized}: ({lat}, {lng}){approx_text}")
        else:
            missing_cities.append(city)
            print(f"❌ {city} -> {normalized}: NO COORDINATES")
    
    print("\n" + "=" * 50)
    print(f"Результат: {len(found_cities)}/{len(cities_from_message)} міст знайдено")
    
    if missing_cities:
        print(f"\n❌ Відсутні міста ({len(missing_cities)}):")
        for city in missing_cities:
            print(f"   {city}")
    else:
        print("\n🎉 Всі міста знайдено!")

if __name__ == '__main__':
    main()

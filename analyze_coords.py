#!/usr/bin/env python3
"""
Check if there might be other markers affecting display
"""

def analyze_coordinates():
    print("АНАЛІЗ КООРДИНАТ:")
    print("="*50)
    
    # Current marker coordinates
    marker_lat = 48.535
    marker_lng = 35.87
    
    # Reference coordinates
    pavlohrad_lat = 48.515
    pavlohrad_lng = 35.866
    
    dnipro_lat = 48.4647
    dnipro_lng = 35.0462
    
    print(f"Marker position: {marker_lat}, {marker_lng}")
    print(f"Павлоград: {pavlohrad_lat}, {pavlohrad_lng}")
    print(f"Дніпро: {dnipro_lat}, {dnipro_lng}")
    print()
    
    # Calculate distances
    import math
    
    def distance(lat1, lng1, lat2, lng2):
        return math.sqrt((lat1-lat2)**2 + (lng1-lng2)**2)
    
    dist_to_pavlohrad = distance(marker_lat, marker_lng, pavlohrad_lat, pavlohrad_lng)
    dist_to_dnipro = distance(marker_lat, marker_lng, dnipro_lat, dnipro_lng)
    
    print(f"Відстань до Павлограда: {dist_to_pavlohrad:.3f} градусів")
    print(f"Відстань до Дніпра: {dist_to_dnipro:.3f} градусів")
    print()
    
    if dist_to_pavlohrad < dist_to_dnipro:
        print("✅ Мітка ближче до Павлограда")
        print(f"   Різниця: в {dist_to_dnipro/dist_to_pavlohrad:.1f} разів ближче до Павлограда")
    else:
        print("❌ Мітка ближче до Дніпра")
    
    print()
    print("МОЖЛИВІ ПРИЧИНИ ПЛУТАНИНИ:")
    print("1. Zoom level карти - на великому масштабі мітки можуть здаватися близько")
    print("2. Кілька міток поруч - інша мітка може бути в Дніпрі")  
    print("3. Кешування - стара мітка все ще відображається")
    print("4. Павлоградський район великий - мітка може бути не в центрі міста")

if __name__ == "__main__":
    analyze_coordinates()

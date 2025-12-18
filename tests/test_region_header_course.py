"""Test that region-to-region course from header doesn't create misleading markers"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import extract_threats

def test_dnipro_region_header_to_zaporizhzhia():
    """дніпропетровщина: БпЛА курсом на Запоріжжя - should NOT create marker in Dnipro city"""
    msg = "дніпропетровщина: БпЛА курсом на Запоріжжя"
    threats = extract_threats(msg, 'test', 'test', '2024-01-01')
    
    # Should create marker in Zaporizhzhia (destination), NOT in Dnipro
    assert len(threats) == 1, f"Expected 1 threat, got {len(threats)}"
    
    threat = threats[0]
    assert threat['place'].lower() == 'запоріжжя', f"Expected Запоріжжя, got {threat['place']}"
    # Zaporizhzhia coords are approximately 47.8388, 35.1396
    assert 47.5 < threat['lat'] < 48.0, f"Expected Zaporizhzhia latitude, got {threat['lat']}"
    assert 35.0 < threat['lng'] < 35.5, f"Expected Zaporizhzhia longitude, got {threat['lng']}"
    
    print(f"✓ Region header course: {threat['place']} at ({threat['lat']}, {threat['lng']})")

def test_dnipro_region_multiple_courses():
    """3х БпЛА курсом на Павлоград | 2х БпЛА курсом на Гірницьке - should create markers at destinations"""
    msg = "дніпропетровщина: 3х БпЛА курсом на Павлоград | дніпропетровщина: 2х БпЛА курсом на Гірницьке | дніпропетровщина: БпЛА курсом на Запоріжжя"
    threats = extract_threats(msg, 'test', 'test', '2024-01-01')
    
    assert len(threats) >= 3, f"Expected at least 3 threats, got {len(threats)}"
    
    places = [t['place'].lower() for t in threats]
    print(f"✓ Found threats at: {places}")
    
    # Should have markers at destination cities, not in Dnipro
    assert any('павлоград' in p for p in places), f"Missing Pavlohrad in {places}"
    assert any('запоріжжя' in p for p in places), f"Missing Zaporizhzhia in {places}"

if __name__ == '__main__':
    test_dnipro_region_header_to_zaporizhzhia()
    test_dnipro_region_multiple_courses()
    print("\n✓ All tests passed!")

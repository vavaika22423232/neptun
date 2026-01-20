#!/usr/bin/env python3
"""Test the trajectory parsing fixes"""
import sys

sys.path.insert(0, '/Users/vladimirmalik/Desktop/render2')

# Import the actual functions from app.py
exec(open('app.py').read())

# Test _get_region_center
print("=== Тест _get_region_center ===")
tests = [
    'вінницькою областю',
    'миколаївською областю',
    'київською областю',
    'вінницька область',
    'вінницька',
]
for t in tests:
    result = _get_region_center(t)
    print(f"  '{t}' -> {result}")

# Test _get_city_coords
print("\n=== Тест _get_city_coords ===")
city_tests = [
    'миколаєва',
    'миколаїв',
    'київ',
    'києва',
]
for t in city_tests:
    result = _get_city_coords(t)
    print(f"  '{t}' -> {result}")

# Test full patterns
print("\n=== Тест parse_trajectory_from_message ===")
test_messages = [
    "над вінницькою областю курсом на північ",
    "дрон миколаївщина в напрямку миколаєва",
    "шахед над київщиною курсом на захід",
    "БпЛА над полтавщиною курсом на схід",
    "ударний БпЛА миколаївщина в напрямку одеси",
]
for msg in test_messages:
    result = parse_trajectory_from_message(msg)
    print(f"  '{msg[:50]}...' -> {result}")

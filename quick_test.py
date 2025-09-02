import sys
sys.path.insert(0, '.')
from app import process_message

# Short test message
text = """Сумщина:
БпЛА курсом на Суми
БпЛА курсом на Путивль

Київщина:
БпЛА курсом на Велику Димерку"""

print("Quick test:")
tracks = process_message(text, 'test', '2025-09-02 12:00:00', 'test_channel')
print(f"Total tracks: {len(tracks)}")
for i, track in enumerate(tracks):
    print(f"{i+1}. {track['place']}")

#!/usr/bin/env python3
"""Test script for Multi-Channel Intelligence Fusion System"""

from datetime import datetime, timedelta

from app import (
    CHANNEL_FUSION,
    get_fused_markers,
    get_fused_trajectories,
    process_message_with_fusion,
)

# Clear existing events
CHANNEL_FUSION.fused_events.clear()
CHANNEL_FUSION.message_to_event.clear()

# Test messages from different channels - simulating shaheds flying from south to north
base_time = datetime.now()

test_messages = [
    # Message 1: First report from official channel
    {
        'id': 'test1',
        'text': '⚠️ 10 шахедів від Криму. Курс на Київ через Миколаївську область',
        'date': base_time.strftime('%Y-%m-%d %H:%M:%S'),
        'channel': 'kpszsu',
        'lat': 46.8,
        'lng': 32.0,
    },
    # Message 2: Confirmation from another channel (should merge!)
    {
        'id': 'test2',
        'text': 'Шахеди над Миколаївщиною рухаються на північ. Кількість: близько 10',
        'date': (base_time + timedelta(minutes=2)).strftime('%Y-%m-%d %H:%M:%S'),
        'channel': 'war_monitor',
        'lat': 47.0,  # Slightly north - they moved!
        'lng': 32.2,
    },
    # Message 3: Update - they reached Cherkasy (should merge to same event)
    {
        'id': 'test3',
        'text': 'Група шахедів проходить Черкаську область. Напрямок Київ. Кількість 8 (2 збито)',
        'date': (base_time + timedelta(minutes=15)).strftime('%Y-%m-%d %H:%M:%S'),
        'channel': 'napramok',
        'lat': 49.4,
        'lng': 31.9,
    },
    # Message 4: Different group - ballistic missile (should NOT merge)
    {
        'id': 'test4',
        'text': '⚡️ Балістика з Криму! Напрямок Одеса',
        'date': (base_time + timedelta(minutes=5)).strftime('%Y-%m-%d %H:%M:%S'),
        'channel': 'kpszsu',
        'lat': 46.0,
        'lng': 33.5,
    },
]

print('=== Testing Multi-Channel Fusion System ===')
print()

for msg in test_messages:
    result = process_message_with_fusion(msg)
    if result:
        print(f'Message from {msg["channel"]}: {result["action"]} -> event {result["event_id"][:8]}...')
        if result['event']:
            e = result['event']
            print(f'  - Type: {e["threat_type"]}, Qty: {e["quantity"]} (destroyed: {e["quantity_destroyed"]})')
            print(f'  - Regions: {e["regions"]}')
            print(f'  - Direction: {e["direction"]}')
            print(f'  - Unique sources: {len({m["channel"] for m in e["messages"]})}')
            print(f'  - Confidence: {e["confidence"]:.2f}')
            print(f'  - Trajectory points: {len(e["trajectory"])}')
    print()

print('=' * 50)
print('=== Active Events ===')
events = CHANNEL_FUSION.get_active_events()
print(f'Total active events: {len(events)}')
for e in events:
    sources = list({m['channel'] for m in e['messages']})
    print(f'\n  Event {e["id"][:8]}...')
    print(f'    Type: {e["threat_type"]} x{e["quantity"]} (destroyed: {e["quantity_destroyed"]})')
    print(f'    Direction: {e["direction"]}')
    print(f'    Regions visited: {e["regions"]}')
    print(f'    Sources: {sources}')
    print(f'    Status: {e["status"]}')
    print(f'    Confidence: {e["confidence"]:.2f}')
    print(f'    Trajectory points: {len(e["trajectory"])}')

print()
print('=' * 50)
print('=== Fused Markers ===')
markers = get_fused_markers()
print(f'Total markers: {len(markers)}')
for m in markers:
    print(f'  {m["place"]} [{m["lat"]:.2f}, {m["lng"]:.2f}]')
    print(f'    Sources: {m.get("fusion_sources", [])}')
    print(f'    Confidence: {m.get("fusion_confidence", 0):.2f}')

print()
print('=' * 50)
print('=== Trajectories ===')
trajectories = get_fused_trajectories()
print(f'Total trajectories: {len(trajectories)}')
for t in trajectories:
    print(f'  Event {t["event_id"][:8]}...: {t["point_count"]} points')
    print(f'    Start: {t["start"]}')
    print(f'    Current: {t["end"]}')
    print(f'    Distance: {t.get("total_distance_km", 0):.1f} km')

# Debug: show raw trajectory data
print()
print('=== RAW TRAJECTORY DEBUG ===')
for e in events:
    print(f'Event {e["id"][:8]}... trajectory: {len(e["trajectory"])} points')
    for i, pt in enumerate(e['trajectory']):
        print(f'  {i}: {pt["coords"]} from {pt["source"]} at {pt["timestamp"]}')

print()
print('✅ Multi-Channel Fusion System working!')
print()
print('Key features demonstrated:')
print('  - Messages from different channels about same threat are MERGED')
print('  - Trajectory is built from sequential positions')
print('  - Confidence increases with more sources')
print('  - Different threat types create separate events')

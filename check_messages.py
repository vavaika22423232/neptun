#!/usr/bin/env python3
"""Check if messages are being processed and stored correctly."""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app import load_messages, process_message
import json

def check_recent_messages():
    print("Loading recent messages from database...")
    messages = load_messages()
    
    # Find recent messages with course patterns
    course_messages = []
    for msg in messages[-20:]:  # Last 20 messages
        text = msg.get('text', '').lower()
        if 'бпла' in text and 'курс' in text and ' на ' in text:
            course_messages.append(msg)
    
    print(f"Found {len(course_messages)} recent messages with course patterns:")
    
    for i, msg in enumerate(course_messages[-5:], 1):  # Last 5 only
        print(f"\n{i}. Message ID: {msg.get('id')}")
        print(f"   Date: {msg.get('date')}")
        print(f"   Channel: {msg.get('channel', msg.get('source', 'N/A'))}")
        print(f"   Has lat/lng: {bool(msg.get('lat') and msg.get('lng'))}")
        print(f"   List only: {msg.get('list_only', False)}")
        print(f"   Source match: {msg.get('source_match', 'N/A')}")
        
        # Show first few lines of text
        text_lines = (msg.get('text') or '').split('\n')[:3]
        for line in text_lines:
            if line.strip():
                print(f"   Text: {line.strip()[:80]}...")
                break
        
        # Try to reparse this message
        try:
            tracks = process_message(msg.get('text', ''), msg.get('id'), msg.get('date'), msg.get('channel', ''))
            if isinstance(tracks, list):
                geo_tracks = [t for t in tracks if not t.get('list_only')]
                print(f"   Reparse result: {len(tracks)} total tracks, {len(geo_tracks)} geo tracks")
                if geo_tracks:
                    print(f"   First geo track: {geo_tracks[0].get('place')} at {geo_tracks[0].get('lat')},{geo_tracks[0].get('lng')}")
            else:
                print(f"   Reparse failed: {type(tracks)}")
        except Exception as e:
            print(f"   Reparse error: {e}")

if __name__ == '__main__':
    check_recent_messages()

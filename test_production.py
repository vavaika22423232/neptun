#!/usr/bin/env python3
"""Test production /data endpoint to see current tracks."""

import requests
import json

def test_production_data():
    url = "https://neptun-7ua9.onrender.com/data"
    
    try:
        print("Fetching current tracks from production...")
        response = requests.get(url, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            tracks = data.get('tracks', [])
            events = data.get('events', [])
            
            print(f"Total tracks: {len(tracks)}")
            print(f"Total events: {len(events)}")
            
            # Look for shahed markers
            shahed_tracks = [t for t in tracks if t.get('threat_type') == 'shahed']
            print(f"Shahed tracks: {len(shahed_tracks)}")
            
            # Look for course-related markers
            course_tracks = [t for t in tracks if 'multiline_oblast_city' in (t.get('source_match') or '')]
            print(f"Course-related tracks (multiline_oblast_city): {len(course_tracks)}")
            
            # Show recent events that might contain course patterns
            course_events = []
            for event in events[:10]:  # Check last 10 events
                text = (event.get('text') or '').lower()
                if 'бпла' in text and 'курс' in text and ' на ' in text:
                    course_events.append(event)
            
            print(f"Recent events with course patterns: {len(course_events)}")
            
            if course_events:
                print("\nFound course events (should have markers but don't):")
                for i, event in enumerate(course_events[:3], 1):
                    print(f"{i}. Date: {event.get('date')}")
                    print(f"   Channel: {event.get('channel', 'N/A')}")
                    lines = (event.get('text') or '').split('\n')[:3]
                    for line in lines:
                        if line.strip():
                            print(f"   Text: {line.strip()[:80]}...")
                            break
            
            if shahed_tracks:
                print("\nSample shahed tracks:")
                for i, track in enumerate(shahed_tracks[:3], 1):
                    print(f"{i}. {track.get('place')} at {track.get('lat')},{track.get('lng')}")
                    print(f"   Source: {track.get('source_match')}")
                    print(f"   Date: {track.get('date')}")
            
        else:
            print(f"HTTP {response.status_code}: {response.text}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    test_production_data()

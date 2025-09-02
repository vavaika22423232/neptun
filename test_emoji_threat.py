#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test emoji-prefixed threat message parsing"""

import requests
import json

test_message = "🛸 Звягель (Житомирська обл.) Загроза застосування БПЛА"

def test_emoji_threat():
    print(f"Testing emoji threat message: {test_message}")
    
    try:
        response = requests.post(
            'http://localhost:5000/debug_parse',
            json={'text': test_message},
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            tracks = result.get('tracks', [])
            
            print(f"Response received: {len(tracks)} tracks")
            
            if tracks:
                for i, track in enumerate(tracks, 1):
                    print(f"\nTrack {i}:")
                    print(f"  Place: {track.get('place', 'N/A')}")
                    print(f"  Type: {track.get('type', 'N/A')}")
                    print(f"  Threat Type: {track.get('threat_type', 'N/A')}")
                    print(f"  Icon: {track.get('marker_icon', 'N/A')}")
                    print(f"  Coordinates: {track.get('lat', 'N/A')}, {track.get('lon', 'N/A')}")
                    print(f"  Source: {track.get('source', 'N/A')}")
                    print(f"  Text: {track.get('text', 'N/A')}")
                
                # Check if we got expected result
                if len(tracks) == 1:
                    track = tracks[0]
                    if (track.get('place') == 'Звягель' and 
                        track.get('marker_icon') == 'shahed.png' and
                        track.get('threat_type') == 'загроза застосування бпла'):
                        print("\n✅ SUCCESS: Emoji threat message parsed correctly!")
                        return True
                    else:
                        print("\n❌ FAIL: Track found but wrong details")
                        return False
                else:
                    print(f"\n❌ FAIL: Expected 1 track, got {len(tracks)}")
                    return False
            else:
                print("\n❌ FAIL: No tracks found")
                print(f"Raw response: {result}")
                return False
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

if __name__ == "__main__":
    success = test_emoji_threat()
    exit(0 if success else 1)

#!/usr/bin/env python3
"""
NEPTUN Alarm App - Migration Test Script
Run this to verify the modular app works correctly.

Usage:
    python test_migration.py
"""

import sys
import os

def main():
    print("=" * 60)
    print("NEPTUN ALARM APP - MIGRATION VERIFICATION")
    print("=" * 60)
    
    errors = []
    
    # 1. Import test
    print("\n[1/6] Testing app import...")
    try:
        from app import app
        print("  ✅ Main app imports OK")
    except Exception as e:
        errors.append(f"Import error: {e}")
        print(f"  ❌ Import failed: {e}")
        return 1
    
    # 2. Route count
    print("\n[2/6] Checking routes...")
    routes = set(r.rule for r in app.url_map.iter_rules())
    print(f"  ✅ {len(routes)} unique routes registered")
    
    # 3. Blueprint count
    print("\n[3/6] Checking blueprints...")
    bps = list(app.blueprints.keys())
    expected_bps = ['alarms', 'payments', 'blackout', 'chat', 'family', 
                    'admin', 'pages', 'devices', 'geocoding', 'messages',
                    'analytics', 'telegram', 'comments', 'stream']
    missing_bps = [b for b in expected_bps if b not in bps]
    if missing_bps:
        errors.append(f"Missing blueprints: {missing_bps}")
        print(f"  ⚠️ Missing blueprints: {missing_bps}")
    else:
        print(f"  ✅ All {len(expected_bps)} blueprints registered")
    
    # 4. Critical endpoints
    print("\n[4/6] Checking critical endpoints...")
    critical = [
        '/', '/api/alarms', '/api/alarm-status', '/api/alarm-history',
        '/api/messages', '/api/events', '/api/stats',
        '/healthz', '/admin', '/stream', '/comments',
        '/api/register-device', '/api/family/sos',
        '/api/search_cities', '/api/get_schedule', '/locate'
    ]
    missing = [r for r in critical if r not in routes]
    if missing:
        errors.append(f"Missing routes: {missing}")
        print(f"  ⚠️ Missing {len(missing)} routes: {missing}")
    else:
        print(f"  ✅ All {len(critical)} critical endpoints present")
    
    # 5. Module functions
    print("\n[5/6] Checking module functions...")
    try:
        from routes import (
            load_messages, save_messages,
            ensure_city_coords, geocode_with_photon,
            broadcast_new, broadcast_alarm,
            init_visits_db, record_visit_sql,
            load_hidden, save_hidden
        )
        print("  ✅ All key functions importable")
    except ImportError as e:
        errors.append(f"Function import error: {e}")
        print(f"  ❌ Function import failed: {e}")
    
    # 6. File sizes
    print("\n[6/6] Code statistics...")
    try:
        app_size = os.path.getsize('app.py')
        old_size = os.path.getsize('app_old.py') if os.path.exists('app_old.py') else 0
        routes_size = sum(
            os.path.getsize(os.path.join('routes', f)) 
            for f in os.listdir('routes') 
            if f.endswith('.py')
        )
        print(f"  📁 app.py (new):     {app_size:,} bytes")
        if old_size:
            print(f"  📁 app_old.py:       {old_size:,} bytes")
            print(f"  📊 Entry point reduced by {(old_size - app_size) / old_size * 100:.1f}%")
        print(f"  📁 routes/*.py:      {routes_size:,} bytes")
    except Exception as e:
        print(f"  ⚠️ Could not calculate sizes: {e}")
    
    # Summary
    print("\n" + "=" * 60)
    if errors:
        print(f"⚠️ COMPLETED WITH {len(errors)} ISSUES:")
        for e in errors:
            print(f"  - {e}")
        return 1
    else:
        print("✅ ALL TESTS PASSED - MIGRATION SUCCESSFUL!")
        print("\nThe app is ready for deployment.")
        return 0

if __name__ == '__main__':
    sys.exit(main())

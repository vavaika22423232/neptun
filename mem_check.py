#!/usr/bin/env python3
"""
Memory usage checker for Neptune app.
Run: python3 mem_check.py
"""

import sys
import gc

def get_size(obj, seen=None):
    """Recursively calculate size of objects"""
    size = sys.getsizeof(obj)
    if seen is None:
        seen = set()
    obj_id = id(obj)
    if obj_id in seen:
        return 0
    seen.add(obj_id)
    if isinstance(obj, dict):
        size += sum([get_size(v, seen) for v in obj.values()])
        size += sum([get_size(k, seen) for k in obj.keys()])
    elif hasattr(obj, '__dict__'):
        size += get_size(obj.__dict__, seen)
    elif hasattr(obj, '__iter__') and not isinstance(obj, (str, bytes, bytearray)):
        size += sum([get_size(i, seen) for i in obj])
    return size

def format_bytes(size):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} TB"

def check_memory():
    """Check memory usage of key objects"""
    print("=" * 60)
    print("MEMORY USAGE REPORT")
    print("=" * 60)
    
    gc.collect()
    
    try:
        import app
        
        checks = [
            ('RESPONSE_CACHE._cache', getattr(getattr(app, 'RESPONSE_CACHE', None), '_cache', {})),
            ('_MESSAGES_CACHE', getattr(app, '_MESSAGES_CACHE', {})),
            ('SENT_NOTIFICATIONS_CACHE', getattr(app, 'SENT_NOTIFICATIONS_CACHE', {})),
            ('_region_topic_cache', getattr(app, '_region_topic_cache', {})),
            ('_threat_classification_cache', getattr(app, '_threat_classification_cache', {})),
            ('_mapstransler_geocode_cache', getattr(app, '_mapstransler_geocode_cache', {})),
            ('ACTIVE_VISITORS', getattr(app, 'ACTIVE_VISITORS', {})),
            ('VISIT_STATS', getattr(app, 'VISIT_STATS', None) or {}),
            ('DEBUG_LOGS', getattr(app, 'DEBUG_LOGS', [])),
            ('FALLBACK_REPARSE_CACHE', getattr(app, 'FALLBACK_REPARSE_CACHE', set())),
        ]
        
        total = 0
        for name, obj in checks:
            if obj is not None:
                size = get_size(obj)
                total += size
                count = len(obj) if hasattr(obj, '__len__') else 'N/A'
                print(f"{name:40} {format_bytes(size):>12}  items: {count}")
        
        print("-" * 60)
        print(f"{'TOTAL tracked':40} {format_bytes(total):>12}")
        
    except Exception as e:
        print(f"Error importing app: {e}")
    
    try:
        import psutil
        process = psutil.Process()
        mem = process.memory_info()
        print()
        print("PROCESS MEMORY:")
        print(f"  RSS (Resident):  {format_bytes(mem.rss)}")
        print(f"  VMS (Virtual):   {format_bytes(mem.vms)}")
    except ImportError:
        print("\nInstall psutil for process memory: pip install psutil")

if __name__ == '__main__':
    check_memory()

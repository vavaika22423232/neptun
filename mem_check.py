#!/usr/bin/env python3
"""Memory analysis script"""
import sys
import gc

print("=== Memory Analysis ===")

# Check process memory
try:
    import psutil
    process = psutil.Process()
    print(f"Initial memory: {process.memory_info().rss / 1024 / 1024:.1f} MB")
except ImportError:
    print("psutil not available")

# Import app
print("\nImporting app...")
import app
gc.collect()

try:
    process = psutil.Process()
    print(f"After import: {process.memory_info().rss / 1024 / 1024:.1f} MB")
except:
    pass

# Check large objects
print("\n=== Large data structures ===")
objects_to_check = [
    'UKRAINE_ALL_SETTLEMENTS',
    'UKRAINE_SETTLEMENTS_BY_OBLAST', 
    'UKRAINE_ADDRESSES_DB',
    'UKRAINE_CITIES',
    'REGION_MAPPING',
    'request_counts',
    '_groq_cache',
    '_mapstransler_geocode_cache',
    'ACTIVE_VISITORS',
]

for name in objects_to_check:
    obj = getattr(app, name, None)
    if obj is not None:
        if isinstance(obj, dict):
            print(f"{name}: {len(obj)} keys")
        elif isinstance(obj, (list, set)):
            print(f"{name}: {len(obj)} items")
        else:
            print(f"{name}: {type(obj)}")

# Deep size estimation
print("\n=== Deep size estimation ===")
def deep_getsizeof(obj, seen=None):
    size = sys.getsizeof(obj)
    if seen is None:
        seen = set()
    obj_id = id(obj)
    if obj_id in seen:
        return 0
    seen.add(obj_id)
    if isinstance(obj, dict):
        size += sum([deep_getsizeof(v, seen) for v in obj.values()])
        size += sum([deep_getsizeof(k, seen) for k in obj.keys()])
    elif hasattr(obj, '__iter__') and not isinstance(obj, (str, bytes)):
        try:
            size += sum([deep_getsizeof(i, seen) for i in obj])
        except:
            pass
    return size

for name in ['UKRAINE_ALL_SETTLEMENTS', 'UKRAINE_SETTLEMENTS_BY_OBLAST']:
    obj = getattr(app, name, None)
    if obj:
        try:
            size_mb = deep_getsizeof(obj) / 1024 / 1024
            print(f"{name}: ~{size_mb:.1f} MB")
        except Exception as e:
            print(f"{name}: error - {e}")

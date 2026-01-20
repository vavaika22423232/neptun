"""
Tests for utility modules.
"""
import pytest
import threading
import time
from datetime import datetime, timezone

from utils.threading import AtomicValue, ThreadSafeDict, ThreadSafeListSimple as ThreadSafeList, TTLCache
from utils.rate_limiter import TokenBucketLimiter as TokenBucket, SlidingWindowLimiter as RateLimiter


class TestAtomicValue:
    """Tests for AtomicValue."""
    
    def test_get_set(self):
        av = AtomicValue(10)
        assert av.get() == 10
        
        av.set(20)
        assert av.get() == 20
    
    def test_default_value(self):
        av = AtomicValue(None)
        assert av.get() is None
    
    def test_compare_and_set(self):
        av = AtomicValue(10)
        
        # Should succeed
        result = av.compare_and_set(10, 20)
        assert result is True
        assert av.get() == 20
        
        # Should fail
        result = av.compare_and_set(10, 30)  # Expected 10, but is 20
        assert result is False
        assert av.get() == 20
    
    def test_update(self):
        av = AtomicValue(10)
        new_value = av.update(lambda x: x * 2)
        
        # update() returns the NEW value after applying the function
        assert new_value == 20
        assert av.get() == 20
    
    def test_thread_safety(self):
        av = AtomicValue(0)
        errors = []
        
        def increment():
            try:
                for _ in range(1000):
                    av.update(lambda x: x + 1)
            except Exception as e:
                errors.append(e)
        
        threads = [threading.Thread(target=increment) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert len(errors) == 0
        assert av.get() == 10000


class TestThreadSafeDict:
    """Tests for ThreadSafeDict."""
    
    def test_get_set(self):
        d = ThreadSafeDict()
        d.set("key", "value")
        assert d.get("key") == "value"
    
    def test_get_default(self):
        d = ThreadSafeDict()
        assert d.get("nonexistent") is None
        assert d.get("nonexistent", "default") == "default"
    
    def test_delete(self):
        d = ThreadSafeDict()
        d.set("key", "value")
        d.delete("key")
        assert d.get("key") is None
    
    def test_contains(self):
        d = ThreadSafeDict()
        d.set("key", "value")
        assert "key" in d
        assert "other" not in d
    
    def test_len(self):
        d = ThreadSafeDict()
        d.set("a", 1)
        d.set("b", 2)
        assert len(d) == 2
    
    def test_items(self):
        d = ThreadSafeDict()
        d.set("a", 1)
        d.set("b", 2)
        
        items = list(d.items())
        assert len(items) == 2
        assert ("a", 1) in items
        assert ("b", 2) in items
    
    def test_keys_values(self):
        d = ThreadSafeDict()
        d.set("a", 1)
        d.set("b", 2)
        
        assert set(d.keys()) == {"a", "b"}
        assert set(d.values()) == {1, 2}
    
    def test_clear(self):
        d = ThreadSafeDict()
        d.set("a", 1)
        d.set("b", 2)
        d.clear()
        assert len(d) == 0
    
    def test_thread_safety(self):
        d = ThreadSafeDict()
        errors = []
        
        def writer():
            try:
                for i in range(1000):
                    d.set(f"key_{threading.current_thread().name}_{i}", i)
            except Exception as e:
                errors.append(e)
        
        def reader():
            try:
                for _ in range(1000):
                    list(d.items())
            except Exception as e:
                errors.append(e)
        
        threads = [
            *[threading.Thread(target=writer) for _ in range(5)],
            *[threading.Thread(target=reader) for _ in range(5)],
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert len(errors) == 0


class TestThreadSafeList:
    """Tests for ThreadSafeList."""
    
    def test_append(self):
        lst = ThreadSafeList()
        lst.append(1)
        lst.append(2)
        assert len(lst) == 2
    
    def test_extend(self):
        lst = ThreadSafeList()
        lst.extend([1, 2, 3])
        assert len(lst) == 3
    
    def test_pop(self):
        lst = ThreadSafeList()
        lst.extend([1, 2, 3])
        
        item = lst.pop()
        assert item == 3
        assert len(lst) == 2
    
    def test_getitem(self):
        lst = ThreadSafeList()
        lst.extend([1, 2, 3])
        assert lst[0] == 1
        assert lst[-1] == 3
    
    def test_iteration(self):
        lst = ThreadSafeList()
        lst.extend([1, 2, 3])
        
        items = list(lst)
        assert items == [1, 2, 3]
    
    def test_snapshot(self):
        lst = ThreadSafeList()
        lst.extend([1, 2, 3])
        
        snapshot = lst.snapshot()
        lst.append(4)
        
        assert snapshot == [1, 2, 3]
        assert len(lst) == 4


class TestTTLCache:
    """Tests for TTLCache."""
    
    def test_get_set(self):
        cache = TTLCache(default_ttl=60)
        cache.set("key", "value")
        assert cache.get("key") == "value"
    
    def test_expiration(self):
        cache = TTLCache(default_ttl=0.1)  # 100ms TTL
        cache.set("key", "value")
        
        assert cache.get("key") == "value"
        
        time.sleep(0.15)
        assert cache.get("key") is None
    
    def test_custom_ttl(self):
        cache = TTLCache(default_ttl=60)
        cache.set("short", "value", ttl=0.1)
        cache.set("long", "value", ttl=60)
        
        time.sleep(0.15)
        assert cache.get("short") is None
        assert cache.get("long") == "value"
    
    def test_cleanup(self):
        cache = TTLCache(default_ttl=0.1)
        for i in range(100):
            cache.set(f"key_{i}", i)
        
        time.sleep(0.15)
        cache.cleanup()
        
        # All should be expired and cleaned
        assert len(cache) == 0
    
    def test_max_size(self):
        cache = TTLCache(default_ttl=60, max_size=5)
        
        for i in range(10):
            cache.set(f"key_{i}", i)
        
        assert len(cache) <= 5


class TestRateLimiter:
    """Tests for RateLimiter (SlidingWindowLimiter)."""
    
    def test_basic_limiting(self):
        limiter = RateLimiter(window_seconds=1.0, max_requests=10)
        
        # Should allow first requests
        for _ in range(10):
            assert limiter.allow() is True
        
        # Should block next request
        assert limiter.allow() is False
    
    def test_refill(self):
        limiter = RateLimiter(window_seconds=0.1, max_requests=10)
        
        # Use all tokens
        for _ in range(10):
            limiter.allow()
        
        # Wait for window to reset
        time.sleep(0.15)
        
        # Should allow again
        assert limiter.allow() is True
    
    def test_wait_time(self):
        limiter = RateLimiter(window_seconds=0.1, max_requests=10)
        
        # Use all tokens
        for _ in range(10):
            limiter.allow()
        
        # wait_time should return how long to wait
        wait = limiter.wait_time()
        assert wait >= 0
        
        # Wait and try again
        time.sleep(0.15)
        result = limiter.allow()
        assert result is True


class TestTokenBucket:
    """Tests for TokenBucket (TokenBucketLimiter)."""
    
    def test_initial_tokens(self):
        bucket = TokenBucket(capacity=10, rate=1.0)
        
        # Should have full capacity initially
        for _ in range(10):
            assert bucket.acquire(blocking=False) is True
        
        assert bucket.acquire(blocking=False) is False
    
    def test_refill(self):
        bucket = TokenBucket(capacity=10, rate=100.0)  # 100 tokens/sec
        
        # Empty the bucket
        for _ in range(10):
            bucket.acquire(blocking=False)
        
        # Wait for refill
        time.sleep(0.1)  # Should add ~10 tokens
        
        # Should be able to consume again
        assert bucket.acquire(blocking=False) is True
    
    def test_available_tokens(self):
        bucket = TokenBucket(capacity=10, rate=1.0)
        
        bucket.acquire(5, blocking=False)
        available = bucket.available_tokens
        
        # Due to floating point refill, allow small margin
        assert available <= 5.1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

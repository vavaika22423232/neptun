"""
Thread-safe containers and state management.

Замість глобальних dict/list які мутуються з різних потоків,
використовуємо thread-safe контейнери з атомарними операціями.
"""
import threading
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Callable, Generic, Optional, TypeVar

T = TypeVar('T')


class AtomicValue(Generic[T]):
    """
    Thread-safe container for a single value.

    Замість:
        global SOME_VALUE
        SOME_VALUE = new_value  # Race condition!

    Використовуємо:
        state = AtomicValue(initial)
        state.set(new_value)  # Thread-safe
        value = state.get()   # Thread-safe
    """

    def __init__(self, initial: T):
        self._value: T = initial
        self._lock = threading.RLock()

    def get(self) -> T:
        """Get current value (thread-safe)."""
        with self._lock:
            return self._value

    def set(self, value: T) -> None:
        """Set new value (thread-safe)."""
        with self._lock:
            self._value = value

    def update(self, func: Callable[[T], T]) -> T:
        """
        Atomically update value using function.

        Example:
            counter.update(lambda x: x + 1)
        """
        with self._lock:
            self._value = func(self._value)
            return self._value

    def compare_and_set(self, expected: T, new_value: T) -> bool:
        """
        Set value only if current equals expected.
        Returns True if set was successful.
        """
        with self._lock:
            if self._value == expected:
                self._value = new_value
                return True
            return False


class ThreadSafeDict(Generic[T]):
    """
    Thread-safe dictionary with atomic operations.

    Замість:
        global CACHE
        CACHE[key] = value  # Race condition!

    Використовуємо:
        cache = ThreadSafeDict()
        cache.set(key, value)  # Thread-safe
    """

    def __init__(self):
        self._data: dict[str, T] = {}
        self._lock = threading.RLock()

    def get(self, key: str, default: Optional[T] = None) -> Optional[T]:
        with self._lock:
            return self._data.get(key, default)

    def set(self, key: str, value: T) -> None:
        with self._lock:
            self._data[key] = value

    def delete(self, key: str) -> bool:
        with self._lock:
            if key in self._data:
                del self._data[key]
                return True
            return False

    def pop(self, key: str, default: Optional[T] = None) -> Optional[T]:
        with self._lock:
            return self._data.pop(key, default)

    def keys(self) -> list:
        with self._lock:
            return list(self._data.keys())

    def values(self) -> list:
        with self._lock:
            return list(self._data.values())

    def items(self) -> list:
        with self._lock:
            return list(self._data.items())

    def copy(self) -> dict[str, T]:
        with self._lock:
            return deepcopy(self._data)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._data)

    def __contains__(self, key: str) -> bool:
        with self._lock:
            return key in self._data

    def get_or_create(self, key: str, factory: Callable[[], T]) -> T:
        """Get value or create using factory if missing."""
        with self._lock:
            if key not in self._data:
                self._data[key] = factory()
            return self._data[key]

    def update_if_exists(self, key: str, func: Callable[[T], T]) -> bool:
        """Update value if key exists. Returns True if updated."""
        with self._lock:
            if key in self._data:
                self._data[key] = func(self._data[key])
                return True
            return False


class ThreadSafeSet:
    """Thread-safe set with size limit."""

    def __init__(self, max_size: int = 1000):
        self._data: set = set()
        self._lock = threading.RLock()
        self._max_size = max_size

    def add(self, item: Any) -> bool:
        """Add item. Returns False if already exists."""
        with self._lock:
            if item in self._data:
                return False

            # Evict oldest if at capacity (simple FIFO via list conversion)
            if len(self._data) >= self._max_size:
                items = list(self._data)
                self._data = set(items[len(items)//2:])

            self._data.add(item)
            return True

    def __contains__(self, item: Any) -> bool:
        with self._lock:
            return item in self._data

    def remove(self, item: Any) -> bool:
        with self._lock:
            if item in self._data:
                self._data.remove(item)
                return True
            return False

    def clear(self) -> None:
        with self._lock:
            self._data.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._data)


class BoundedList(Generic[T]):
    """
    Thread-safe list with maximum size.

    Для логів, debug info тощо - автоматично видаляє старі записи.
    """

    def __init__(self, max_size: int = 100):
        self._data: list = []
        self._lock = threading.RLock()
        self._max_size = max_size

    def append(self, item: T) -> None:
        with self._lock:
            self._data.append(item)
            if len(self._data) > self._max_size:
                self._data = self._data[-self._max_size:]

    def get_all(self) -> list:
        with self._lock:
            return list(self._data)

    def get_last(self, n: int) -> list:
        with self._lock:
            return list(self._data[-n:])

    def clear(self) -> None:
        with self._lock:
            self._data.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._data)


# Alias for compatibility
ThreadSafeList = BoundedList


class ThreadSafeListSimple(Generic[T]):
    """Simple thread-safe list without size limit."""

    def __init__(self):
        self._data: list = []
        self._lock = threading.RLock()

    def append(self, item: T) -> None:
        with self._lock:
            self._data.append(item)

    def extend(self, items) -> None:
        with self._lock:
            self._data.extend(items)

    def pop(self, index: int = -1) -> T:
        with self._lock:
            return self._data.pop(index)

    def __getitem__(self, index: int) -> T:
        with self._lock:
            return self._data[index]

    def __len__(self) -> int:
        with self._lock:
            return len(self._data)

    def __iter__(self):
        with self._lock:
            return iter(list(self._data))

    def snapshot(self) -> list:
        """Return a copy of current list."""
        with self._lock:
            return list(self._data)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()


@dataclass
class TTLValue(Generic[T]):
    """Value with expiration timestamp."""
    value: T
    expires_at: float


class TTLCache(Generic[T]):
    """
    Thread-safe cache with TTL (Time To Live).

    Замість:
        if time.time() > cache_expires:
            cache = fetch_new_data()  # Race condition!

    Використовуємо:
        cache = TTLCache(ttl=60)
        cache.set('key', value)
        value = cache.get('key')  # Returns None if expired
    """

    def __init__(self, default_ttl: float = 60.0, max_size: int = 1000):
        self._data: dict[str, TTLValue[T]] = {}
        self._lock = threading.RLock()
        self._default_ttl = default_ttl
        self._max_size = max_size

    def get(self, key: str) -> Optional[T]:
        """Get value if exists and not expired."""
        import time
        with self._lock:
            entry = self._data.get(key)
            if entry is None:
                return None
            if time.time() > entry.expires_at:
                del self._data[key]
                return None
            return entry.value

    def set(self, key: str, value: T, ttl: Optional[float] = None) -> None:
        """Set value with TTL."""
        import time
        ttl = ttl if ttl is not None else self._default_ttl
        with self._lock:
            self._data[key] = TTLValue(
                value=value,
                expires_at=time.time() + ttl
            )
            # Enforce max size
            if len(self._data) > self._max_size:
                self.cleanup()

    def delete(self, key: str) -> bool:
        with self._lock:
            if key in self._data:
                del self._data[key]
                return True
            return False

    def cleanup(self) -> int:
        """Remove all expired entries and enforce max size. Returns count removed."""
        import time
        now = time.time()
        with self._lock:
            # First remove expired
            expired = [k for k, v in self._data.items() if now > v.expires_at]
            for k in expired:
                del self._data[k]
            removed = len(expired)

            # Then enforce max size by removing oldest entries
            if len(self._data) > self._max_size:
                # Sort by expires_at and keep only max_size newest
                sorted_items = sorted(
                    self._data.items(),
                    key=lambda x: x[1].expires_at,
                    reverse=True  # newest first
                )
                keys_to_keep = {k for k, v in sorted_items[:self._max_size]}
                keys_to_remove = [k for k in self._data.keys() if k not in keys_to_keep]
                for k in keys_to_remove:
                    del self._data[k]
                removed += len(keys_to_remove)

            return removed

    # Alias for tests
    clear_expired = cleanup

    def __len__(self) -> int:
        with self._lock:
            return len(self._data)

    def stats(self) -> dict[str, int]:
        """Get cache statistics."""
        import time
        now = time.time()
        with self._lock:
            total = len(self._data)
            valid = sum(1 for v in self._data.values() if now <= v.expires_at)
            return {
                'total': total,
                'valid': valid,
                'expired': total - valid,
            }

"""
Rate limiting utilities.

Централізований rate limiting замість розкиданих по коду
глобальних змінних і time.sleep().
"""
import threading
import time
from dataclasses import dataclass
from functools import wraps
from typing import Callable, Optional, TypeVar

T = TypeVar('T')


@dataclass
class RateLimitConfig:
    """Configuration for rate limiter."""
    requests_per_minute: int = 60
    requests_per_second: float = 1.0
    burst_size: int = 5
    cooldown_seconds: float = 60.0


class TokenBucketLimiter:
    """
    Token bucket rate limiter.

    Дозволяє burst (всплеск) запитів, але обмежує середню швидкість.
    Thread-safe.
    """

    def __init__(
        self,
        rate: float = 1.0,  # tokens per second
        capacity: int = 10,  # max burst size
    ):
        self._rate = rate
        self._capacity = capacity
        self._tokens = float(capacity)
        self._last_update = time.time()
        self._lock = threading.Lock()

    def acquire(self, tokens: int = 1, blocking: bool = True) -> bool:
        """
        Try to acquire tokens.

        Args:
            tokens: Number of tokens to acquire
            blocking: If True, wait until tokens available

        Returns:
            True if tokens acquired, False if non-blocking and unavailable
        """
        with self._lock:
            self._refill()

            if self._tokens >= tokens:
                self._tokens -= tokens
                return True

            if not blocking:
                return False

            # Calculate wait time
            needed = tokens - self._tokens
            wait_time = needed / self._rate

        # Wait outside lock
        time.sleep(wait_time)

        with self._lock:
            self._refill()
            if self._tokens >= tokens:
                self._tokens -= tokens
                return True
            return False

    def _refill(self) -> None:
        """Add tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self._last_update
        self._tokens = min(
            self._capacity,
            self._tokens + elapsed * self._rate
        )
        self._last_update = now

    @property
    def available_tokens(self) -> float:
        with self._lock:
            self._refill()
            return self._tokens


class SlidingWindowLimiter:
    """
    Sliding window rate limiter.

    Рахує запити за останні N секунд.
    Більш точний ніж token bucket для strict rate limiting.
    """

    def __init__(
        self,
        max_requests: int,
        window_seconds: float = 60.0,
    ):
        self._max_requests = max_requests
        self._window = window_seconds
        self._requests: list = []
        self._lock = threading.Lock()

    def allow(self) -> bool:
        """Check if request is allowed and record it."""
        now = time.time()
        cutoff = now - self._window

        with self._lock:
            # Remove old requests
            self._requests = [t for t in self._requests if t > cutoff]

            if len(self._requests) < self._max_requests:
                self._requests.append(now)
                return True
            return False

    def wait_time(self) -> float:
        """Get time to wait until next request allowed."""
        now = time.time()
        cutoff = now - self._window

        with self._lock:
            self._requests = [t for t in self._requests if t > cutoff]

            if len(self._requests) < self._max_requests:
                return 0.0

            # Wait until oldest request expires
            oldest = min(self._requests)
            return max(0.0, oldest + self._window - now)

    @property
    def current_count(self) -> int:
        now = time.time()
        cutoff = now - self._window
        with self._lock:
            return sum(1 for t in self._requests if t > cutoff)


class CooldownManager:
    """
    Manages cooldown periods after errors.

    Замість:
        global _groq_daily_cooldown_until, _groq_429_backoff

    Використовуємо:
        cooldown = CooldownManager()
        if cooldown.is_active('groq'):
            return None  # Skip
        try:
            result = call_api()
        except RateLimitError:
            cooldown.activate('groq', backoff=True)
    """

    def __init__(self, base_cooldown: float = 60.0, max_backoff: float = 3600.0):
        self._cooldowns: dict = {}
        self._backoff_counts: dict = {}
        self._base_cooldown = base_cooldown
        self._max_backoff = max_backoff
        self._lock = threading.Lock()

    def is_active(self, key: str) -> bool:
        """Check if cooldown is active for key."""
        with self._lock:
            until = self._cooldowns.get(key, 0)
            return time.time() < until

    def activate(self, key: str, duration: Optional[float] = None, backoff: bool = False) -> float:
        """
        Activate cooldown for key.

        Args:
            key: Identifier for this cooldown
            duration: Explicit duration (overrides backoff)
            backoff: Use exponential backoff based on error count

        Returns:
            Actual cooldown duration applied
        """
        with self._lock:
            if duration is not None:
                actual_duration = duration
            elif backoff:
                count = self._backoff_counts.get(key, 0) + 1
                self._backoff_counts[key] = count
                actual_duration = min(
                    self._base_cooldown * (2 ** (count - 1)),
                    self._max_backoff
                )
            else:
                actual_duration = self._base_cooldown

            self._cooldowns[key] = time.time() + actual_duration
            return actual_duration

    def reset(self, key: str) -> None:
        """Reset cooldown and backoff counter for key."""
        with self._lock:
            self._cooldowns.pop(key, None)
            self._backoff_counts.pop(key, None)

    def remaining(self, key: str) -> float:
        """Get remaining cooldown time (0 if not active)."""
        with self._lock:
            until = self._cooldowns.get(key, 0)
            return max(0.0, until - time.time())


def rate_limited(limiter: TokenBucketLimiter):
    """
    Decorator for rate-limited functions.

    Usage:
        limiter = TokenBucketLimiter(rate=0.5, capacity=3)

        @rate_limited(limiter)
        def call_external_api():
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            limiter.acquire(blocking=True)
            return func(*args, **kwargs)
        return wrapper
    return decorator


def with_cooldown(cooldown: CooldownManager, key: str, exceptions: tuple = (Exception,)):
    """
    Decorator that handles cooldown on errors.

    Usage:
        cooldown = CooldownManager()

        @with_cooldown(cooldown, 'api', exceptions=(RateLimitError,))
        def call_api():
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., Optional[T]]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Optional[T]:
            if cooldown.is_active(key):
                return None
            try:
                result = func(*args, **kwargs)
                cooldown.reset(key)
                return result
            except exceptions:
                cooldown.activate(key, backoff=True)
                raise
        return wrapper
    return decorator

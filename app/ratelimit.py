"""A tiny in-memory sliding-window limiter used to slow down password guessing.

It is per-process, which is fine for a single container. For several instances,
move the counters to a shared store such as Redis.
"""

import time
from threading import Lock

from fastapi import HTTPException, status

from app.config import get_settings


class LoginRateLimiter:
    def __init__(self, max_attempts: int, window_seconds: int) -> None:
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._failures: dict[str, list[float]] = {}
        self._lock = Lock()

    def _recent(self, key: str, now: float) -> list[float]:
        cutoff = now - self.window_seconds
        recent = [t for t in self._failures.get(key, []) if t > cutoff]
        if recent:
            self._failures[key] = recent
        else:
            self._failures.pop(key, None)
        return recent

    def check(self, key: str) -> None:
        """Raise HTTP 429 if this key has too many recent failures."""
        with self._lock:
            now = time.monotonic()
            recent = self._recent(key, now)
            if len(recent) >= self.max_attempts:
                retry_after = int(self.window_seconds - (now - recent[0])) + 1
                raise HTTPException(
                    status.HTTP_429_TOO_MANY_REQUESTS,
                    "Too many failed login attempts. Please try again later.",
                    headers={"Retry-After": str(retry_after)},
                )

    def register_failure(self, key: str) -> None:
        with self._lock:
            now = time.monotonic()
            self._recent(key, now)
            self._failures.setdefault(key, []).append(now)

    def clear(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)

    def reset(self) -> None:
        with self._lock:
            self._failures.clear()


_settings = get_settings()
login_limiter = LoginRateLimiter(_settings.login_max_attempts, _settings.login_window_seconds)

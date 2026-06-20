"""Async circuit breaker for external job source clients.

States:
    CLOSED    — normal, all calls go through
    OPEN      — source is failing, calls rejected immediately (returns [])
    HALF_OPEN — one test call allowed after recovery_timeout;
                success → CLOSED, failure → OPEN again

Usage:
    result = await get_breaker("jsearch").call(jsearch_client.search(...), timeout=6.0)
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import structlog

log = structlog.get_logger("circuit_breaker")


class State(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreaker:
    name: str
    failure_threshold: int = 5      # failures before OPEN
    recovery_timeout: float = 60.0  # seconds before OPEN → HALF_OPEN

    _state: State = field(default=State.CLOSED, init=False, repr=False)
    _failures: int = field(default=0, init=False, repr=False)
    _opened_at: float = field(default=0.0, init=False, repr=False)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False, repr=False)

    def _maybe_recover(self) -> None:
        if self._state == State.OPEN:
            if time.monotonic() - self._opened_at >= self.recovery_timeout:
                self._state = State.HALF_OPEN
                log.info("circuit_breaker.half_open", source=self.name)

    async def call(self, coro: Any, timeout: float) -> list[dict[str, Any]]:
        """Run coro with deadline. Track result for circuit state transitions."""
        async with self._lock:
            self._maybe_recover()
            if self._state == State.OPEN:
                log.debug("circuit_breaker.rejected", source=self.name)
                return []

        try:
            result: list[dict[str, Any]] = await asyncio.wait_for(coro, timeout=timeout)
            async with self._lock:
                if result:
                    self._failures = 0
                    if self._state == State.HALF_OPEN:
                        self._state = State.CLOSED
                        log.info("circuit_breaker.closed", source=self.name)
            return result if isinstance(result, list) else []

        except asyncio.TimeoutError:
            await self._record_failure("timeout")
            log.warning("circuit_breaker.timeout", source=self.name, timeout=timeout)
            return []

        except Exception as exc:
            await self._record_failure("exception")
            log.warning("circuit_breaker.error", source=self.name, error=str(exc))
            return []

    async def _record_failure(self, reason: str) -> None:
        async with self._lock:
            self._failures += 1
            if self._failures >= self.failure_threshold:
                self._state = State.OPEN
                self._opened_at = time.monotonic()
                log.warning(
                    "circuit_breaker.opened",
                    source=self.name,
                    reason=reason,
                    failures=self._failures,
                )

    @property
    def state(self) -> str:
        self._maybe_recover()
        return self._state.value


# Module-level registry — one breaker per source, shared across all requests
_registry: dict[str, CircuitBreaker] = {}


def get_breaker(name: str) -> CircuitBreaker:
    if name not in _registry:
        _registry[name] = CircuitBreaker(name=name)
    return _registry[name]

"""Gate de concurrencia: limita transcripciones simultaneas."""

import asyncio
from contextlib import asynccontextmanager

from app.config import get_settings


class Gate:
    def __init__(self, max_concurrent: int):
        self._sem = asyncio.Semaphore(max_concurrent)
        self._max = max_concurrent

    @asynccontextmanager
    async def acquire(self):
        async with self._sem:
            yield

    @property
    def max_concurrent(self) -> int:
        return self._max


_gate_instance: Gate | None = None


def get_gate() -> Gate:
    """Singleton Gate, inicializado con MAX_CONCURRENT_REQUESTS."""
    global _gate_instance
    if _gate_instance is None:
        _gate_instance = Gate(max_concurrent=get_settings().MAX_CONCURRENT_REQUESTS)
    return _gate_instance


def reset_gate_for_tests() -> None:
    """Helper SOLO para tests."""
    global _gate_instance
    _gate_instance = None

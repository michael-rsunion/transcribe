import asyncio

import pytest

from app.services.concurrency import Gate, get_gate, reset_gate_for_tests


@pytest.mark.asyncio
async def test_gate_max_two_simultaneous():
    gate = Gate(max_concurrent=2)
    held: list[int] = []

    async def task(i: int):
        async with gate.acquire():
            held.append(i)
            await asyncio.sleep(0.05)
            held.append(-i)

    await asyncio.gather(task(1), task(2), task(3))
    # Los primeros dos en entrar son 1 y 2 (no los tres simultaneos)
    first_two_positives = [x for x in held if x > 0][:2]
    assert set(first_two_positives) == {1, 2}


def test_get_gate_returns_singleton():
    reset_gate_for_tests()
    g1 = get_gate()
    g2 = get_gate()
    assert g1 is g2
    reset_gate_for_tests()

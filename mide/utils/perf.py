"""Tiny helpers to measure time and peak memory of a call."""

from __future__ import annotations

import time
import tracemalloc
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass
class Measure:
    """Result of :func:`measure`."""

    seconds: float
    peak_mb: float
    result: Any


def measure(func: Callable[[], Any]) -> Measure:
    """Run ``func`` and report elapsed time and peak Python allocation (MB)."""
    tracemalloc.start()
    start = time.perf_counter()
    try:
        result = func()
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    return Measure(time.perf_counter() - start, peak / 1e6, result)

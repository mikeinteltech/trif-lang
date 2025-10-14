"""Threading helpers for Trif."""
from __future__ import annotations

import concurrent.futures
import time
from typing import Any, Callable

_executor = concurrent.futures.ThreadPoolExecutor()


def spawn(func: Callable[[], Any]) -> None:
    _executor.submit(func)


def parallel_map(func: Callable[[Any], Any], items: list[Any]) -> list[Any]:
    futures = [_executor.submit(func, item) for item in items]
    return [future.result() for future in futures]


def sleep(seconds: float) -> None:
    time.sleep(seconds)


__all__ = ["spawn", "parallel_map", "sleep"]

"""I/O utilities."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def println(value: Any) -> None:
    print(value)


def read_text(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def write_text(path: str, data: str) -> None:
    Path(path).write_text(data, encoding="utf-8")


def read_json(path: str) -> Any:
    return json.loads(read_text(path))


def write_json(path: str, data: Any) -> None:
    write_text(path, json.dumps(data, indent=2))


def prompt(message: str) -> str:
    return input(message)


__all__ = ["println", "read_text", "write_text", "read_json", "write_json", "prompt"]

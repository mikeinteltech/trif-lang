"""Data processing helpers."""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Callable, Iterable, List


def load_csv(path: str) -> List[dict[str, str]]:
    with Path(path).open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        return list(reader)


def save_csv(path: str, rows: Iterable[dict[str, Any]]) -> None:
    rows = list(rows)
    if not rows:
        Path(path).write_text("", encoding="utf-8")
        return
    with Path(path).open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


def filter_rows(rows: Iterable[dict[str, Any]], predicate: Callable[[dict[str, Any]], bool]) -> List[dict[str, Any]]:
    return [row for row in rows if predicate(row)]


def map_rows(rows: Iterable[dict[str, Any]], mapper: Callable[[dict[str, Any]], dict[str, Any]]) -> List[dict[str, Any]]:
    return [mapper(row) for row in rows]


def to_json(data: Any) -> str:
    return json.dumps(data, indent=2)


__all__ = ["load_csv", "save_csv", "filter_rows", "map_rows", "to_json"]

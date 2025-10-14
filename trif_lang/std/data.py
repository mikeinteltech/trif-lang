"""Data processing helpers."""
from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any, Callable, Dict, Iterable, List, Mapping, Sequence, Tuple, TypeVar

T = TypeVar("T")
K = TypeVar("K")


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


def group_rows(
    rows: Iterable[dict[str, Any]],
    key: Callable[[dict[str, Any]], K],
) -> Dict[K, List[dict[str, Any]]]:
    """Group *rows* according to *key* returning a dictionary of lists."""

    grouped: Dict[K, List[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[key(row)].append(row)
    return dict(grouped)


def sort_rows(
    rows: Iterable[dict[str, Any]],
    key: Callable[[dict[str, Any]], Any],
    *,
    reverse: bool = False,
) -> List[dict[str, Any]]:
    """Return a list of *rows* sorted using *key*."""

    return sorted(rows, key=key, reverse=reverse)


def select_columns(rows: Iterable[Mapping[str, Any]], columns: Sequence[str]) -> List[dict[str, Any]]:
    """Project *rows* to the provided *columns*."""

    column_set = list(columns)
    return [{column: row.get(column) for column in column_set} for row in rows]


def summarize_numeric(rows: Iterable[Mapping[str, Any]], columns: Sequence[str]) -> Dict[str, Dict[str, float]]:
    """Compute summary statistics for numeric *columns* within *rows*."""

    extracted: Dict[str, List[float]] = {column: [] for column in columns}
    for row in rows:
        for column in columns:
            value = row.get(column)
            if isinstance(value, (int, float)):
                extracted[column].append(float(value))
    summary: Dict[str, Dict[str, float]] = {}
    for column, values in extracted.items():
        if values:
            summary[column] = {
                "count": float(len(values)),
                "min": min(values),
                "max": max(values),
                "mean": mean(values),
            }
        else:
            summary[column] = {"count": 0.0, "min": float("nan"), "max": float("nan"), "mean": float("nan")}
    return summary


def distinct(rows: Iterable[Mapping[str, Any]], *, key: Callable[[Mapping[str, Any]], T] | None = None) -> List[Mapping[str, Any]]:
    """Return unique rows preserving order."""

    seen: set[Any] = set()
    unique_rows: List[Mapping[str, Any]] = []
    for row in rows:
        value = key(row) if key is not None else tuple(sorted(row.items()))
        if value in seen:
            continue
        seen.add(value)
        unique_rows.append(row)
    return unique_rows


def join_rows(
    left: Iterable[Mapping[str, Any]],
    right: Iterable[Mapping[str, Any]],
    *,
    left_key: Callable[[Mapping[str, Any]], K],
    right_key: Callable[[Mapping[str, Any]], K] | None = None,
) -> List[Dict[str, Any]]:
    """Perform an inner join between *left* and *right* using the provided keys."""

    right_lookup: Dict[K, List[Mapping[str, Any]]] = defaultdict(list)
    effective_right_key = right_key or left_key
    for row in right:
        right_lookup[effective_right_key(row)].append(row)

    joined_rows: List[Dict[str, Any]] = []
    for left_row in left:
        key_value = left_key(left_row)
        matches = right_lookup.get(key_value, [])
        for right_row in matches:
            merged: Dict[str, Any] = {}
            merged.update(left_row)
            merged.update(right_row)
            joined_rows.append(merged)
    return joined_rows


def window(rows: Sequence[T], size: int, *, step: int = 1) -> List[Tuple[T, ...]]:
    """Return sliding windows across *rows*."""

    if size <= 0:
        raise ValueError("Window size must be positive.")
    if step <= 0:
        raise ValueError("Window step must be positive.")
    result: List[Tuple[T, ...]] = []
    for index in range(0, max(len(rows) - size + 1, 0), step):
        result.append(tuple(rows[index : index + size]))
    return result


__all__ = [
    "load_csv",
    "save_csv",
    "filter_rows",
    "map_rows",
    "to_json",
    "group_rows",
    "sort_rows",
    "select_columns",
    "summarize_numeric",
    "distinct",
    "join_rows",
    "window",
]

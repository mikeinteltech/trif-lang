"""I/O utilities."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


def _ensure_sequence(value: Any) -> Sequence[Any]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return value
    return [value]


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


def read_binary(path: str) -> bytes:
    """Return the raw bytes stored at *path*."""

    return Path(path).read_bytes()


def write_binary(path: str, data: bytes | bytearray | memoryview) -> None:
    """Persist *data* to *path* ensuring parents exist."""

    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_bytes(bytes(data))


def append_text(path: str, data: str, *, newline: bool = True) -> None:
    """Append *data* to the end of *path* creating the file if required."""

    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with file_path.open("a", encoding="utf-8") as fh:
        fh.write(data)
        if newline:
            fh.write("\n")


def print_table(
    rows: Sequence[Mapping[str, Any]] | Sequence[Sequence[Any]],
    headers: Sequence[str] | None = None,
) -> None:
    """Pretty-print a table of *rows* to stdout."""

    rows = list(rows)
    if not rows:
        println("(empty)")
        return

    display_rows: list[list[str]]
    column_headers: Sequence[str]
    first = rows[0]
    if isinstance(first, Mapping):
        if headers is not None:
            column_headers = list(headers)
            access_keys: Sequence[Any] = column_headers
        else:
            ordered_keys: list[Any] = []
            seen: set[Any] = set()
            for row in rows:  # type: ignore[assignment]
                for key in row.keys():
                    if key not in seen:
                        seen.add(key)
                        ordered_keys.append(key)
            access_keys = ordered_keys
            column_headers = [str(key) for key in ordered_keys]
        display_rows = [
            [str(row.get(key, "")) for key in access_keys]
            for row in rows  # type: ignore[assignment]
        ]
    else:
        row_sequences = [list(_ensure_sequence(row)) for row in rows]
        if headers is not None and any(len(row) != len(headers) for row in row_sequences):
            raise ValueError("Header count must match row length when headers are provided.")
        column_count = max((len(row) for row in row_sequences), default=0)
        column_headers = headers if headers is not None else [str(index) for index in range(column_count)]
        display_rows = [
            [str(value) for value in row] + [""] * (column_count - len(row))
            for row in row_sequences
        ]

    widths = [len(str(header)) for header in column_headers]
    if not widths:
        println("(no columns)")
        return
    for row in display_rows:
        for idx, cell in enumerate(row):
            if idx >= len(widths):
                widths.append(len(cell))
            else:
                widths[idx] = max(widths[idx], len(cell))

    header_line = " | ".join(str(header).ljust(widths[idx]) for idx, header in enumerate(column_headers))
    separator = "-+-".join("-" * width for width in widths)
    println(header_line)
    println(separator)
    for row in display_rows:
        println(" | ".join(cell.ljust(widths[idx]) for idx, cell in enumerate(row)))


def print_lines(lines: Iterable[Any]) -> None:
    """Emit every value from *lines* on its own line."""

    for line in lines:
        println(line)


__all__ = [
    "println",
    "read_text",
    "write_text",
    "read_json",
    "write_json",
    "prompt",
    "read_binary",
    "write_binary",
    "append_text",
    "print_table",
    "print_lines",
]

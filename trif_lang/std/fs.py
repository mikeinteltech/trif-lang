"""Filesystem utilities for Trif programs."""
from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, List


@dataclass(frozen=True)
class DirectoryEntry:
    """Information about an entry returned from :func:`scan`."""

    path: str
    is_file: bool
    is_dir: bool
    size: int


def _ensure_path(value: str | os.PathLike[str]) -> Path:
    return Path(value)


def readText(path: str | os.PathLike[str], *, encoding: str = "utf-8") -> str:
    """Read a text file using the provided encoding."""

    return _ensure_path(path).read_text(encoding=encoding)


def writeText(
    path: str | os.PathLike[str],
    content: str,
    *,
    encoding: str = "utf-8",
    exist_ok: bool = True,
) -> None:
    """Write the string *content* to *path*.

    Parameters
    ----------
    path:
        Target file location.
    content:
        The string that will be written to the file.
    encoding:
        Encoding used when serialising the string. Defaults to UTF-8.
    exist_ok:
        When ``False`` and the target file already exists, a :class:`FileExistsError`
        will be raised. Defaults to ``True``.
    """

    file_path = _ensure_path(path)
    if not exist_ok and file_path.exists():
        raise FileExistsError(f"File already exists: {file_path}")
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding=encoding)


def readBytes(path: str | os.PathLike[str]) -> bytes:
    """Read the complete contents of *path* as raw bytes."""

    return _ensure_path(path).read_bytes()


def writeBytes(path: str | os.PathLike[str], data: bytes | bytearray | memoryview) -> None:
    """Persist *data* to *path* creating parents as required."""

    file_path = _ensure_path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_bytes(bytes(data))


def exists(path: str | os.PathLike[str]) -> bool:
    """Return ``True`` when *path* exists."""

    return _ensure_path(path).exists()


def makeDirs(path: str | os.PathLike[str], *, exist_ok: bool = True) -> None:
    """Create directory structure rooted at *path*."""

    _ensure_path(path).mkdir(parents=True, exist_ok=exist_ok)


def remove(path: str | os.PathLike[str], *, recursive: bool = False) -> None:
    """Delete a file or directory.

    When *recursive* is ``True`` directories are removed recursively.
    """

    target = _ensure_path(path)
    if target.is_dir() and recursive:
        shutil.rmtree(target)
    else:
        target.unlink()


def copy(src: str | os.PathLike[str], dest: str | os.PathLike[str], *, overwrite: bool = True) -> None:
    """Copy *src* to *dest*.

    Directories are copied recursively while files use :func:`shutil.copy2` to
    preserve metadata.
    """

    src_path = _ensure_path(src)
    dest_path = _ensure_path(dest)
    if dest_path.exists() and not overwrite:
        raise FileExistsError(f"Destination already exists: {dest_path}")
    if src_path.is_dir():
        if dest_path.exists() and dest_path.is_file():
            raise IsADirectoryError(f"Cannot copy directory into file: {dest_path}")
        if dest_path.exists():
            shutil.rmtree(dest_path)
        shutil.copytree(src_path, dest_path)
    else:
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_path, dest_path)


def move(src: str | os.PathLike[str], dest: str | os.PathLike[str], *, overwrite: bool = True) -> None:
    """Move *src* to *dest* optionally overwriting the target."""

    dest_path = _ensure_path(dest)
    if dest_path.exists() and not overwrite:
        raise FileExistsError(f"Destination already exists: {dest_path}")
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dest))


def join(*parts: str | os.PathLike[str]) -> str:
    """Join *parts* using the platform specific path separator."""

    return str(Path().joinpath(*map(Path, parts)))


def resolve(path: str | os.PathLike[str]) -> str:
    """Return the absolute, normalised representation of *path*."""

    return str(_ensure_path(path).resolve())


def stat(path: str | os.PathLike[str]) -> os.stat_result:
    """Expose :func:`os.stat` for the given *path*."""

    return _ensure_path(path).stat()


def scan(
    path: str | os.PathLike[str],
    *,
    recursive: bool = False,
    include_files: bool = True,
    include_dirs: bool = True,
) -> Iterator[DirectoryEntry]:
    """Iterate entries from *path* yielding :class:`DirectoryEntry` objects."""

    base = _ensure_path(path)
    if recursive:
        for entry in base.rglob("*"):
            if entry.is_file() and include_files:
                yield DirectoryEntry(str(entry), True, False, entry.stat().st_size)
            elif entry.is_dir() and include_dirs:
                yield DirectoryEntry(str(entry), False, True, 0)
    else:
        for entry in base.iterdir():
            if entry.is_file() and include_files:
                yield DirectoryEntry(str(entry), True, False, entry.stat().st_size)
            elif entry.is_dir() and include_dirs:
                yield DirectoryEntry(str(entry), False, True, 0)


def readLines(path: str | os.PathLike[str], *, encoding: str = "utf-8") -> List[str]:
    """Return the contents of *path* split into lines."""

    return _ensure_path(path).read_text(encoding=encoding).splitlines()


def touch(path: str | os.PathLike[str], *, exist_ok: bool = True) -> None:
    """Create the file at *path* if it does not already exist."""

    file_path = _ensure_path(path)
    if file_path.exists() and not exist_ok:
        raise FileExistsError(f"File already exists: {file_path}")
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.touch(exist_ok=True)


def currentDir() -> str:
    """Return the current working directory."""

    return str(Path.cwd())


def changeDir(path: str | os.PathLike[str]) -> None:
    """Change the active working directory to *path*."""

    os.chdir(_ensure_path(path))


__all__ = [
    "DirectoryEntry",
    "readText",
    "writeText",
    "readBytes",
    "writeBytes",
    "exists",
    "makeDirs",
    "remove",
    "copy",
    "move",
    "join",
    "resolve",
    "stat",
    "scan",
    "readLines",
    "touch",
    "currentDir",
    "changeDir",
]

"""Memory manipulation helpers for experimentation and tooling."""
from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import Iterable


@dataclass
class MemoryRegion:
    _buffer: bytearray

    def write32(self, offset: int, value: int) -> None:
        self._buffer[offset : offset + 4] = struct.pack("<I", value & 0xFFFFFFFF)

    def read32(self, offset: int) -> int:
        return struct.unpack("<I", self._buffer[offset : offset + 4])[0]

    def write_bytes(self, offset: int, data: bytes | Iterable[int]) -> None:
        block = data if isinstance(data, bytes) else bytes(data)
        self._buffer[offset : offset + len(block)] = block

    def read_bytes(self, offset: int, length: int) -> bytes:
        return bytes(self._buffer[offset : offset + length])

    def fill(self, value: int) -> None:
        self._buffer[:] = bytes([value & 0xFF] * len(self._buffer))

    def search(self, pattern: bytes) -> int:
        return self._buffer.find(pattern)

    def to_bytes(self) -> bytes:
        return bytes(self._buffer)


def openBuffer(size: int) -> MemoryRegion:
    return MemoryRegion(bytearray(size))


def formatHex(value: int, width: int = 8) -> str:
    return f"0x{value:0{width}X}"


__all__ = ["MemoryRegion", "openBuffer", "formatHex"]

"""Cryptography and secure random helpers."""
from __future__ import annotations

import hashlib
import hmac
import secrets
import uuid
from typing import Iterable


def _ensure_bytes(data: str | bytes | bytearray | memoryview | Iterable[int]) -> bytes:
    if isinstance(data, (bytes, bytearray, memoryview)):
        return bytes(data)
    if isinstance(data, str):
        return data.encode("utf-8")
    return bytes(data)


def sha256(data: str | bytes | bytearray | memoryview | Iterable[int]) -> str:
    """Return the hexadecimal SHA-256 digest for *data*."""

    return hashlib.sha256(_ensure_bytes(data)).hexdigest()


def sha1(data: str | bytes | bytearray | memoryview | Iterable[int]) -> str:
    """Return the hexadecimal SHA-1 digest for *data*."""

    return hashlib.sha1(_ensure_bytes(data)).hexdigest()


def md5(data: str | bytes | bytearray | memoryview | Iterable[int]) -> str:
    """Return the hexadecimal MD5 digest for *data*."""

    return hashlib.md5(_ensure_bytes(data)).hexdigest()


def hmacSha256(key: str | bytes, data: str | bytes) -> str:
    """Return an HMAC-SHA256 signature for *data* using *key*."""

    return hmac.new(_ensure_bytes(key), _ensure_bytes(data), hashlib.sha256).hexdigest()


def randomBytes(length: int) -> bytes:
    """Return *length* cryptographically secure random bytes."""

    return secrets.token_bytes(length)


def randomHex(length: int) -> str:
    """Return a random hexadecimal string of *length* bytes."""

    return secrets.token_hex(length)


def uuid4() -> str:
    """Return a random UUID4 string."""

    return str(uuid.uuid4())


__all__ = [
    "sha256",
    "sha1",
    "md5",
    "hmacSha256",
    "randomBytes",
    "randomHex",
    "uuid4",
]

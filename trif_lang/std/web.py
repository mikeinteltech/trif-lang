"""Client side web helpers."""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Mapping


@dataclass(frozen=True)
class Response:
    """Lightweight HTTP response container."""

    url: str
    status: int
    headers: Dict[str, str]
    body: bytes

    def text(self, encoding: str | None = None) -> str:
        charset = encoding or self.headers.get("Content-Type", "").split("charset=")[-1]
        if not charset or "charset=" not in self.headers.get("Content-Type", ""):
            charset = encoding or "utf-8"
        return self.body.decode(charset, errors="replace")

    def json(self) -> Any:
        return json.loads(self.text())


class _NoRedirect(urllib.request.HTTPErrorProcessor):
    def http_response(self, request, response):  # type: ignore[override]
        return response

    https_response = http_response


def fetch(
    url: str,
    *,
    method: str | None = None,
    headers: Mapping[str, str] | None = None,
    data: bytes | str | Mapping[str, str] | None = None,
    timeout: float | None = None,
    allow_redirects: bool = True,
) -> Response:
    """Perform an HTTP request returning a :class:`Response`."""

    payload: bytes | None
    if isinstance(data, Mapping):
        payload = urllib.parse.urlencode(data).encode("utf-8")
        headers = {"Content-Type": "application/x-www-form-urlencoded", **(headers or {})}
    elif isinstance(data, str):
        payload = data.encode("utf-8")
    else:
        payload = data

    request = urllib.request.Request(url, data=payload, method=method)
    if headers:
        for key, value in headers.items():
            request.add_header(key, value)
    handlers = []
    if not allow_redirects:
        handlers.append(_NoRedirect())
    handler = urllib.request.build_opener(*handlers)
    with handler.open(request, timeout=timeout) as response:
        body = response.read()
        header_map = {key: value for key, value in response.headers.items()}
        return Response(response.geturl(), response.getcode(), header_map, body)


def urlEncode(data: Mapping[str, str] | Iterable[tuple[str, str]]) -> str:
    """Return a URL encoded query string."""

    return urllib.parse.urlencode(data)


def joinUrl(base: str, *parts: str, query: Mapping[str, str] | None = None) -> str:
    """Compose URLs while normalising redundant separators."""

    parsed = urllib.parse.urlparse(base)
    path = "/".join(filter(None, [parsed.path.rstrip("/")] + [part.strip("/") for part in parts]))
    query_string = urllib.parse.urlencode(query) if query else parsed.query
    rebuilt = parsed._replace(path=path, query=query_string)
    return urllib.parse.urlunparse(rebuilt)


def parseQuery(query: str) -> Dict[str, str]:
    """Parse a query string into a dictionary."""

    return {key: value[0] if isinstance(value, list) else value for key, value in urllib.parse.parse_qs(query).items()}


__all__ = ["Response", "fetch", "urlEncode", "joinUrl", "parseQuery"]

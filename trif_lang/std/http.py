"""Express-style HTTP helpers."""
from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable, Dict, List, Optional


@dataclass
class HttpResponse:
    body: bytes
    status: int = HTTPStatus.OK
    headers: Dict[str, str] | None = None


class HttpContext:
    def __init__(self, handler: BaseHTTPRequestHandler) -> None:
        self._handler = handler
        self.headers: Dict[str, str] = {}

    def text(self, text: str, *, status: int = HTTPStatus.OK) -> HttpResponse:
        return HttpResponse(text.encode("utf-8"), status, {"Content-Type": "text/plain; charset=utf-8"})

    def html(self, html: str, *, status: int = HTTPStatus.OK) -> HttpResponse:
        return HttpResponse(html.encode("utf-8"), status, {"Content-Type": "text/html; charset=utf-8"})

    def json(self, payload: Any, *, status: int = HTTPStatus.OK) -> HttpResponse:
        return HttpResponse(
            json.dumps(payload).encode("utf-8"),
            status,
            {"Content-Type": "application/json; charset=utf-8"},
        )

    def send(self, body: str | bytes, *, status: int = HTTPStatus.OK, content_type: str = "text/plain") -> HttpResponse:
        data = body.encode("utf-8") if isinstance(body, str) else body
        return HttpResponse(data, status, {"Content-Type": f"{content_type}; charset=utf-8"})


class HttpServer:
    def __init__(self, host: str = "0.0.0.0", port: int = 5000) -> None:
        self.host = host
        self.port = port
        self.routes: List[tuple[str, str, Callable[[HttpContext], Any]]] = []
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self.router = self

    def add_route(self, method: str, path: str, handler: Callable[[HttpContext], Any]) -> None:
        self.routes.append((method.upper(), path, handler))

    def get(self, path: str, handler: Callable[[HttpContext], Any]) -> None:
        self.add_route("GET", path, handler)

    def post(self, path: str, handler: Callable[[HttpContext], Any]) -> None:
        self.add_route("POST", path, handler)

    def put(self, path: str, handler: Callable[[HttpContext], Any]) -> None:
        self.add_route("PUT", path, handler)

    def delete(self, path: str, handler: Callable[[HttpContext], Any]) -> None:
        self.add_route("DELETE", path, handler)

    def listen(self) -> None:
        if self._server is not None:
            return

        server = self

        class Handler(BaseHTTPRequestHandler):
            def _dispatch(self, method: str) -> None:
                for registered_method, registered_path, callback in server.routes:
                    if registered_method == method and registered_path == self.path:
                        ctx = HttpContext(self)
                        result = callback(ctx)
                        response = server._coerce_response(result)
                        self.send_response(response.status)
                        headers = response.headers or {}
                        for key, value in headers.items():
                            self.send_header(key, value)
                        self.end_headers()
                        self.wfile.write(response.body)
                        return
                self.send_error(HTTPStatus.NOT_FOUND)

            def do_GET(self) -> None:  # noqa: N802 - mandated by BaseHTTPRequestHandler
                self._dispatch("GET")

            def do_POST(self) -> None:  # noqa: N802
                self._dispatch("POST")

            def do_PUT(self) -> None:  # noqa: N802
                self._dispatch("PUT")

            def do_DELETE(self) -> None:  # noqa: N802
                self._dispatch("DELETE")

            def log_message(self, format: str, *args: Any) -> None:  # noqa: A003 - signature fixed
                return

        self._server = ThreadingHTTPServer((self.host, self.port), Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def close(self) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
            self._server = None
        if self._thread is not None:
            self._thread.join(timeout=1)
            self._thread = None

    def _coerce_response(self, result: Any) -> HttpResponse:
        if isinstance(result, HttpResponse):
            return result
        if isinstance(result, bytes):
            return HttpResponse(result)
        if isinstance(result, str):
            return HttpResponse(result.encode("utf-8"))
        if result is None:
            return HttpResponse(b"")
        return HttpResponse(json.dumps(result).encode("utf-8"), headers={"Content-Type": "application/json"})


def createServer(config: Optional[Dict[str, Any]] = None) -> HttpServer:
    config = config or {}
    host = config.get("host", "0.0.0.0")
    port = int(config.get("port", 5000))
    return HttpServer(host=host, port=port)


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())


__all__ = ["HttpServer", "HttpContext", "createServer", "now", "HttpResponse"]

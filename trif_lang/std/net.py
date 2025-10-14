"""Networking helpers using the Python standard library."""
from __future__ import annotations

import json
import socket
import threading
from typing import Any, Callable


def start_tcp_server(host: str, port: int, handler: Callable[[socket.socket, tuple[str, int]], None]) -> None:
    def server() -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((host, port))
            sock.listen()
            while True:
                client, addr = sock.accept()
                threading.Thread(target=handler, args=(client, addr), daemon=True).start()

    threading.Thread(target=server, daemon=True).start()


def send_tcp_message(host: str, port: int, message: str) -> None:
    with socket.create_connection((host, port)) as sock:
        sock.sendall(message.encode("utf-8"))


def broadcast_json(host: str, port: int, payload: Any) -> None:
    send_tcp_message(host, port, json.dumps(payload))


__all__ = ["start_tcp_server", "send_tcp_message", "broadcast_json"]

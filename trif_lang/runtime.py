"""Runtime utilities for executing compiled Trif code."""
from __future__ import annotations

import importlib
import sys
import threading
from types import ModuleType
from typing import Any, Callable, Dict, Iterable, List


class Runtime:
    def __init__(self) -> None:
        self.registry: Dict[str, Callable[[], ModuleType]] = {}
        self.register_stdlib()

    def register_stdlib(self) -> None:
        from .std import io, net, data, threading as trif_threading

        self.registry.update(
            {
                "std.io": lambda: io,
                "std.net": lambda: net,
                "std.data": lambda: data,
                "std.threading": lambda: trif_threading,
            }
        )

    def import_module(self, name: str) -> ModuleType:
        if name in self.registry:
            return self.registry[name]()
        return importlib.import_module(name)

    def execute_python(self, code: str, *, argv: List[str] | None = None) -> None:
        module_globals: Dict[str, Any] = {"runtime": runtime, "__name__": "__trif__"}
        argv = argv or []
        old_argv = sys.argv
        sys.argv = ["trif"] + argv
        try:
            exec(code, module_globals)
            if "main" in module_globals and callable(module_globals["main"]):
                module_globals["main"]()
            else:
                default_entry_point(module_globals)
        finally:
            sys.argv = old_argv

    def iterate(self, value: Any) -> Iterable[Any]:
        if isinstance(value, dict):
            return value.items()
        return value

    def spawn(self, callable_obj: Callable[[], Any]) -> None:
        thread = threading.Thread(target=callable_obj)
        thread.daemon = True
        thread.start()

    def default_entry_point(self, env: Dict[str, Any]) -> None:
        main = env.get("main")
        if callable(main):
            main()


runtime = Runtime()


def default_entry_point(env: Dict[str, Any]) -> None:
    runtime.default_entry_point(env)


__all__ = ["Runtime", "runtime", "default_entry_point"]

"""Runtime utilities for executing compiled Trif code."""
from __future__ import annotations

import importlib
import sys
import threading
from pathlib import Path
from types import ModuleType
from typing import Any, Callable, Dict, Iterable, List, Optional, Set


class ModuleProxy:
    """Lightweight proxy exposing Trif module exports."""

    def __init__(self, module: ModuleType, exports: Dict[str, Any] | None, default: Any | None) -> None:
        self._module = module
        self._exports = exports or {}
        self._default = default

    def __getattr__(self, item: str) -> Any:
        if item in self._exports:
            return self._exports[item]
        return getattr(self._module, item)

    def get_export(self, name: str) -> Any:
        if name in self._exports:
            return self._exports[name]
        if hasattr(self._module, name):
            return getattr(self._module, name)
        raise AttributeError(f"Export '{name}' not found")

    def get_default(self) -> Any:
        if self._default is not None:
            return self._default
        return self._module

    @property
    def module(self) -> ModuleType:
        return self._module


class Runtime:
    def __init__(self) -> None:
        self.registry: Dict[str, Callable[[], ModuleProxy]] = {}
        self.exports: Dict[str, Dict[str, Any]] = {}
        self.default_exports: Dict[str, Any] = {}
        self.project_roots: Set[Path] = set()
        self.search_roots: Set[Path] = set()
        self.search_roots.add(Path.cwd())
        self.register_stdlib()

    def register_stdlib(self) -> None:
        from .std import (
            data,
            fs,
            http,
            io,
            managers,
            memory,
            mobile,
            net,
            process,
            crypto,
            reverse,
            threading as trif_threading,
            web,
        )

        self._register_static_module("std.io", io)
        self._register_static_module("std.net", net)
        self._register_static_module("std.data", data)
        self._register_static_module("std.threading", trif_threading)
        self._register_static_module("std.http", http)
        self._register_static_module("std.mobile", mobile)
        self._register_static_module("std.memory", memory)
        self._register_static_module("std.reverse", reverse)
        self._register_static_module("std.managers", managers)
        self._register_static_module("std.fs", fs)
        self._register_static_module("std.process", process)
        self._register_static_module("std.crypto", crypto)
        self._register_static_module("std.web", web)

    def import_module(self, name: str) -> ModuleProxy:
        self.prepare_project_environment(Path.cwd())
        if name in self.registry:
            return self.registry[name]()
        try:
            module = importlib.import_module(name)
        except ModuleNotFoundError as exc:
            module = self._compile_trif_module(name)
            if module is None:
                raise exc
        return self._wrap_module(module)

    def execute_python(self, code: str, *, argv: List[str] | None = None) -> None:
        module_globals: Dict[str, Any] = {"runtime": runtime, "__name__": "__trif__"}
        argv = argv or []
        old_argv = sys.argv
        sys.argv = ["trif"] + argv
        try:
            self.prepare_project_environment(Path.cwd())
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

    def register_module_exports(
        self, module_name: str, exports: Dict[str, Any], default: Any | None
    ) -> None:
        self.exports[module_name] = dict(exports)
        self.default_exports[module_name] = default

    def extract_export(self, module_proxy: ModuleProxy, name: str) -> Any:
        return module_proxy.get_export(name)

    def extract_default(self, module_proxy: ModuleProxy) -> Any:
        return module_proxy.get_default()

    def prepare_project_environment(self, root: Path) -> None:
        root = root.resolve()
        if root not in self.project_roots:
            self.project_roots.add(root)
        candidates = {root, root / "trif_pkg"}
        for candidate in candidates:
            if candidate.exists() and candidate.is_dir():
                if str(candidate) not in sys.path:
                    sys.path.insert(0, str(candidate))
                self.search_roots.add(candidate)

    def _register_static_module(
        self,
        alias: str,
        module: ModuleType,
        *,
        default: Any | None = None,
    ) -> None:
        exports = self._module_public_exports(module)
        self.registry[alias] = lambda module=module, exports=exports, default=default: ModuleProxy(
            module, exports, default
        )

    def _module_public_exports(self, module: ModuleType) -> Dict[str, Any]:
        names = getattr(module, "__all__", None)
        if names is None:
            names = [name for name in dir(module) if not name.startswith("_")]
        result: Dict[str, Any] = {}
        for name in names:
            try:
                result[name] = getattr(module, name)
            except AttributeError:
                continue
        return result

    def _wrap_module(self, module: ModuleType) -> ModuleProxy:
        module_name = module.__name__
        exports = self.exports.get(module_name)
        default = self.default_exports.get(module_name)
        if exports is None:
            exports = self._module_public_exports(module)
        return ModuleProxy(module, exports, default)

    def _compile_trif_module(self, name: str) -> Optional[ModuleType]:
        module_path = Path(*name.split("."))
        for base in list(self.search_roots):
            candidate = (base / module_path).with_suffix(".trif")
            if candidate.exists():
                from .compiler import Compiler

                compiler = Compiler()
                code = compiler.compile_file(candidate, target="python")
                module = ModuleType(name)
                package = name.rpartition(".")[0] or None
                module_dict = module.__dict__
                module_dict.update({"__name__": name, "__package__": package})
                exec(code, module_dict)
                sys.modules[name] = module
                return module
        return None


runtime = Runtime()


def default_entry_point(env: Dict[str, Any]) -> None:
    runtime.default_entry_point(env)


__all__ = ["Runtime", "runtime", "default_entry_point"]

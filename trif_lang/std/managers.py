"""Manual managers for state, tasks, and lifecycle orchestration."""
from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Callable, Deque, Dict, List, Optional


class TaskManager:
    def __init__(self) -> None:
        self._tasks: List[tuple[str, Callable[[Any], Any]]] = []

    def add(self, name: str, func: Callable[[Any], Any]) -> None:
        self._tasks.append((name, func))

    def run_all(self, context: Any | None = None) -> List[Dict[str, Any]]:
        results = []
        for name, func in self._tasks:
            outcome = func(context)
            results.append({"task": name, "result": outcome})
        return results


@dataclass
class StateManager:
    state: Dict[str, Any] = field(default_factory=dict)
    history: List[Dict[str, Any]] = field(default_factory=list)

    def update(self, **changes: Any) -> Dict[str, Any]:
        self.state.update(changes)
        snapshot = dict(self.state)
        self.history.append(snapshot)
        return snapshot

    def undo(self) -> Dict[str, Any]:
        if self.history:
            self.history.pop()
        self.state = dict(self.history[-1]) if self.history else {}
        return dict(self.state)


class ResourceManager:
    def __init__(self) -> None:
        self._enter: List[Callable[[], Any]] = []
        self._exit: List[Callable[[Any], None]] = []

    def manage(self, enter: Callable[[], Any], exit: Callable[[Any], None]) -> None:
        self._enter.append(enter)
        self._exit.append(exit)

    def execute(self, action: Callable[[List[Any]], Any]) -> Any:
        resources: List[Any] = []
        try:
            for fn in self._enter:
                resources.append(fn())
            return action(resources)
        finally:
            for resource, closer in zip(reversed(resources), reversed(self._exit)):
                closer(resource)


class EventManager:
    """Publish/subscribe manager with manual lifecycle control."""

    def __init__(self) -> None:
        self._handlers: Dict[str, List[Callable[[Any], Any]]] = defaultdict(list)

    def on(self, event: str, handler: Callable[[Any], Any]) -> None:
        self._handlers[event].append(handler)

    def off(self, event: str, handler: Callable[[Any], Any] | None = None) -> None:
        if handler is None:
            self._handlers.pop(event, None)
            return
        listeners = self._handlers.get(event, [])
        self._handlers[event] = [fn for fn in listeners if fn != handler]
        if not self._handlers[event]:
            self._handlers.pop(event, None)

    def emit(self, event: str, payload: Any | None = None) -> List[Any]:
        results: List[Any] = []
        for handler in list(self._handlers.get(event, [])):
            results.append(handler(payload))
        return results

    def clear(self) -> None:
        self._handlers.clear()


class LifecycleManager:
    """Coordinate ordered lifecycle hooks such as start/stop."""

    def __init__(self) -> None:
        self._phases: Dict[str, List[Callable[[], Any]]] = defaultdict(list)

    def hook(self, phase: str, handler: Callable[[], Any]) -> None:
        self._phases[phase].append(handler)

    def run(self, phase: str) -> List[Any]:
        results: List[Any] = []
        for handler in self._phases.get(phase, []):
            results.append(handler())
        return results

    def phases(self) -> List[str]:
        return sorted(self._phases.keys())


class ResourcePool:
    """Manual pool manager for expensive resources like connections."""

    def __init__(
        self,
        create: Callable[[], Any],
        destroy: Callable[[Any], None],
        *,
        max_size: int = 8,
    ) -> None:
        self._create = create
        self._destroy = destroy
        self._max_size = max_size
        self._idle: Deque[Any] = deque()
        self._in_use: List[Any] = []

    def acquire(self) -> Any:
        if self._idle:
            resource = self._idle.popleft()
        elif len(self._in_use) < self._max_size:
            resource = self._create()
        else:
            raise RuntimeError("ResourcePool exhausted")
        self._in_use.append(resource)
        return resource

    def release(self, resource: Any) -> None:
        if resource not in self._in_use:
            return
        self._in_use.remove(resource)
        if len(self._idle) < self._max_size:
            self._idle.append(resource)
        else:
            self._destroy(resource)

    def drain(self) -> None:
        while self._idle:
            self._destroy(self._idle.popleft())
        for resource in list(self._in_use):
            self._destroy(resource)
        self._in_use.clear()


class PipelineManager:
    """Compose ordered transformation steps with manual execution."""

    def __init__(self) -> None:
        self._steps: List[Callable[[Any], Any]] = []

    def step(self, handler: Callable[[Any], Any]) -> None:
        self._steps.append(handler)

    def run(self, payload: Any) -> Any:
        value = payload
        for handler in self._steps:
            value = handler(value)
        return value

    def clear(self) -> None:
        self._steps.clear()


class ConfigurationManager:
    """Manual configuration manager with layered overrides."""

    def __init__(self, defaults: Optional[Dict[str, Any]] = None) -> None:
        self._layers: List[Dict[str, Any]] = [defaults or {}]

    def push(self, overrides: Dict[str, Any]) -> None:
        self._layers.append(dict(overrides))

    def pop(self) -> Dict[str, Any]:
        if len(self._layers) == 1:
            raise RuntimeError("Cannot remove base configuration layer")
        return self._layers.pop()

    def get(self, key: str, default: Any | None = None) -> Any:
        for layer in reversed(self._layers):
            if key in layer:
                return layer[key]
        return default

    def merged(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        for layer in self._layers:
            result.update(layer)
        return result


__all__ = [
    "TaskManager",
    "StateManager",
    "ResourceManager",
    "EventManager",
    "LifecycleManager",
    "ResourcePool",
    "PipelineManager",
    "ConfigurationManager",
]

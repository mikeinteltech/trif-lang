"""Utilities for building mobile-ready bundles."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List


class MobileScreen:
    def __init__(self, name: str) -> None:
        self.name = name
        self.components: List[Dict[str, Any]] = []

    def header(self, text: str) -> None:
        self.components.append({"type": "header", "text": text})

    def text(self, text: str) -> None:
        self.components.append({"type": "text", "text": text})

    def button(self, label: str, action: str | None = None) -> None:
        self.components.append({"type": "button", "label": label, "action": action or "log"})

    def export(self) -> Dict[str, Any]:
        return {"name": self.name, "components": self.components}


class MobileApp:
    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config
        self._screens: Dict[str, Dict[str, Any]] = {}

    def screen(self, name: str, builder) -> None:
        screen = MobileScreen(name)
        builder(screen)
        self._screens[name] = screen.export()

    def export(self) -> Dict[str, Any]:
        return {"config": self.config, "screens": self._screens}


def createApp(config: Dict[str, Any] | None = None) -> MobileApp:
    config = config or {"title": "Trif Mobile"}
    return MobileApp(config)


def build(app: MobileApp, options: Dict[str, Any] | None = None) -> Path:
    options = options or {}
    out_dir = Path(options.get("outDir", "build/mobile")).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    bundle = {
        "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
        "app": app.export(),
        "platform": options.get("platform", "pwa"),
    }
    bundle_path = out_dir / "bundle.json"
    bundle_path.write_text(json.dumps(bundle, indent=2), encoding="utf-8")
    return bundle_path


__all__ = ["MobileApp", "MobileScreen", "createApp", "build"]

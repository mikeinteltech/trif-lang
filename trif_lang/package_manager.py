"""Local filesystem based package manager for Trif."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, List


REGISTRY_ROOT = Path.home() / ".trif" / "registry"
INSTALL_ROOT = Path.home() / ".trif" / "packages"


class PackageManager:
    def __init__(self) -> None:
        self.registry_root = REGISTRY_ROOT
        self.install_root = INSTALL_ROOT
        self.registry_root.mkdir(parents=True, exist_ok=True)
        self.install_root.mkdir(parents=True, exist_ok=True)

    def init(self, path: Path) -> None:
        path = path.resolve()
        path.mkdir(parents=True, exist_ok=True)
        manifest = {
            "name": path.name,
            "version": "0.1.0",
            "description": "A new Trif package",
            "entry": "main.trif",
            "dependencies": {},
        }
        (path / "trif.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        sample = """// main.trif\nfn main() {\n    print(\"Hello from package\")\n}\n"""
        (path / "main.trif").write_text(sample, encoding="utf-8")
        print(f"Initialised package at {path}")

    def publish(self, path: Path) -> None:
        path = path.resolve()
        manifest_path = path / "trif.json"
        if not manifest_path.exists():
            raise FileNotFoundError("trif.json not found")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        package_dir = self.registry_root / manifest["name"] / manifest["version"]
        package_dir.mkdir(parents=True, exist_ok=True)
        for file in path.glob("*.trif"):
            target = package_dir / file.name
            target.write_text(file.read_text(encoding="utf-8"), encoding="utf-8")
        (package_dir / "trif.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        print(f"Published {manifest['name']}@{manifest['version']}")

    def install(self, package: str) -> None:
        parts = package.split("@")
        name = parts[0]
        version = parts[1] if len(parts) > 1 else self._latest_version(name)
        if version is None:
            raise ValueError(f"No versions available for {name}")
        source = self.registry_root / name / version
        if not source.exists():
            raise FileNotFoundError(f"Package {name}@{version} not found in registry")
        target = self.install_root / name / version
        target.mkdir(parents=True, exist_ok=True)
        for file in source.glob("*.trif"):
            (target / file.name).write_text(file.read_text(encoding="utf-8"), encoding="utf-8")
        (target / "trif.json").write_text(
            (source / "trif.json").read_text(encoding="utf-8"), encoding="utf-8"
        )
        print(f"Installed {name}@{version}")

    def list_installed(self) -> Dict[str, List[str]]:
        packages: Dict[str, List[str]] = {}
        if not self.install_root.exists():
            return packages
        for pkg in self.install_root.iterdir():
            versions = [v.name for v in pkg.iterdir() if v.is_dir()]
            packages[pkg.name] = versions
        return packages

    def _latest_version(self, name: str) -> str | None:
        pkg_dir = self.registry_root / name
        if not pkg_dir.exists():
            return None
        versions = sorted([v.name for v in pkg_dir.iterdir() if v.is_dir()])
        return versions[-1] if versions else None


__all__ = ["PackageManager"]

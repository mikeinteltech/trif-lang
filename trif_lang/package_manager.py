"""Package management utilities inspired by npm."""
from __future__ import annotations

import json
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Any, Dict, Tuple
from urllib.parse import urljoin, urlparse
from urllib.request import urlopen

from .compiler import Compiler


CONFIG_ROOT = Path.home() / ".trif"
LOCAL_REGISTRY = CONFIG_ROOT / "registry"
CONFIG_PATH = CONFIG_ROOT / "config.json"
OFFLINE_REGISTRY = Path(__file__).resolve().parent.parent / "registry" / "offline"


class PackageManager:
    """Manage Trif packages with a workflow similar to npm."""

    def __init__(self, project_root: Path | None = None, registry_url: str | None = None) -> None:
        self.project_root = (project_root or Path.cwd()).resolve()
        self.pkg_dir = self.project_root / "trif_pkg"
        self.pkg_dir.mkdir(parents=True, exist_ok=True)
        CONFIG_ROOT.mkdir(parents=True, exist_ok=True)
        LOCAL_REGISTRY.mkdir(parents=True, exist_ok=True)
        self.compiler = Compiler()
        self.registry_url = registry_url or self._load_registry_url()
        self._registry_cache: Dict[str, Any] | None = None

    # ------------------------------------------------------------------
    # Public commands
    def init(self, path: Path) -> None:
        path = path.resolve()
        path.mkdir(parents=True, exist_ok=True)
        manifest = {
            "name": path.name,
            "version": "0.1.0",
            "description": "A fresh Trif package",
            "entry": "src/main.trif",
            "dependencies": {},
        }
        (path / "trif.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        src = path / "src"
        src.mkdir(exist_ok=True)
        sample = (
            "import std.io as io;\n"
            "export function main() {\n"
            "    io.println(\"Hello from Trif!\");\n"
            "}\n"
        )
        (src / "main.trif").write_text(sample, encoding="utf-8")
        (path / "trif_pkg").mkdir(exist_ok=True)
        print(f"Initialised Trif package at {path}")

    def install(self, spec: str) -> None:
        if spec.startswith("file:") or Path(spec).expanduser().exists():
            source = spec.replace("file:", "", 1)
            self._install_from_directory(Path(source))
            return
        name, version = self._parse_spec(spec)
        release = self._resolve_release(name, version)
        url = self._resolve_url(release["tarball"])
        with tempfile.TemporaryDirectory() as tmp:
            archive_path = Path(tmp) / "package.zip"
            self._download_file(url, archive_path)
            with zipfile.ZipFile(archive_path) as zf:
                zf.extractall(Path(tmp) / "package")
            self._install_from_directory(Path(tmp) / "package", expected_name=name)

    def publish(self, path: Path) -> Path:
        path = path.resolve()
        manifest = self._read_manifest(path)
        package_root = LOCAL_REGISTRY / manifest["name"] / manifest["version"]
        package_root.mkdir(parents=True, exist_ok=True)
        archive_path = package_root / "package.zip"
        with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for file in path.rglob("*"):
                if file.is_file():
                    zf.write(file, file.relative_to(path))
        manifest_path = package_root / "package.json"
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        self._update_local_index(manifest["name"], manifest["version"], archive_path)
        print(f"Published {manifest['name']}@{manifest['version']} to local registry")
        return archive_path

    def list_installed(self) -> Dict[str, str]:
        installed: Dict[str, str] = {}
        if not self.pkg_dir.exists():
            return installed
        for package in self.pkg_dir.iterdir():
            manifest_path = package / "trif.json"
            if manifest_path.exists():
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                installed[manifest["name"]] = manifest.get("version", "0.0.0")
        return installed

    def use_registry(self, url: str) -> None:
        self.registry_url = url
        data = {"registry": url}
        CONFIG_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
        self._registry_cache = None
        print(f"Using registry {url}")

    # ------------------------------------------------------------------
    # Internal helpers
    def _load_registry_url(self) -> str:
        if CONFIG_PATH.exists():
            config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            if "registry" in config:
                return config["registry"]
        offline_index = OFFLINE_REGISTRY / "index.json"
        return offline_index.as_uri()

    def _parse_spec(self, spec: str) -> Tuple[str, str | None]:
        if "@" in spec:
            name, version = spec.split("@", 1)
            return name, version or None
        return spec, None

    def _resolve_release(self, name: str, version: str | None) -> Dict[str, Any]:
        index = self._load_registry_index()
        packages = index.get("packages", {})
        if name not in packages:
            raise ValueError(f"Package {name} not found in registry")
        versions: Dict[str, Any] = packages[name]
        if not versions:
            raise ValueError(f"No versions published for {name}")
        if version is None:
            version = sorted(versions.keys())[-1]
        if version not in versions:
            raise ValueError(f"Version {version} not available for {name}")
        return versions[version]

    def _install_from_directory(self, source: Path, expected_name: str | None = None) -> None:
        source = source.resolve()
        manifest = self._read_manifest(source)
        if expected_name and manifest["name"] != expected_name:
            raise ValueError(
                f"Expected package {expected_name} but manifest contains {manifest['name']}"
            )
        target = self.pkg_dir / manifest["name"]
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(source, target)
        self._compile_package(target, manifest)
        self._write_lock(manifest["name"], manifest["version"])
        print(f"Installed {manifest['name']}@{manifest['version']}")

    def _compile_package(self, package_dir: Path, manifest: Dict[str, Any]) -> None:
        trif_files = list(package_dir.rglob("*.trif"))
        for trif_file in trif_files:
            code = self.compiler.compile_file(trif_file, target="python")
            trif_file.with_suffix(".py").write_text(code, encoding="utf-8")
        entry = Path(manifest.get("entry", "index.trif"))
        entry_module = ".".join(entry.with_suffix("").parts)
        init_path = package_dir / "__init__.py"
        init_lines = [
            "import importlib",
            f"_entry = importlib.import_module('.{entry_module}', __name__)",
            "_exports = getattr(_entry, '__trif_exports__', {})",
            "__all__ = list(_exports.keys())",
            "globals().update(_exports)",
            "default = getattr(_entry, '__trif_default_export__', None)",
        ]
        init_path.write_text("\n".join(init_lines) + "\n", encoding="utf-8")

    def _write_lock(self, name: str, version: str) -> None:
        lock_path = self.project_root / "trif.lock.json"
        if lock_path.exists():
            lock = json.loads(lock_path.read_text(encoding="utf-8"))
        else:
            lock = {}
        lock[name] = {"version": version}
        lock_path.write_text(json.dumps(lock, indent=2), encoding="utf-8")

    def _read_manifest(self, path: Path) -> Dict[str, Any]:
        manifest_path = path / "trif.json"
        if not manifest_path.exists():
            raise FileNotFoundError(f"Manifest not found at {manifest_path}")
        return json.loads(manifest_path.read_text(encoding="utf-8"))

    def _resolve_url(self, resource: str) -> str:
        parsed = urlparse(resource)
        if parsed.scheme:
            return resource
        base = self.registry_url
        if base.endswith("index.json"):
            base = base.rsplit("/", 1)[0] + "/"
        if not base.endswith("/"):
            base += "/"
        return urljoin(base, resource)

    def _download_file(self, url: str, target: Path) -> None:
        parsed = urlparse(url)
        if parsed.scheme == "file":
            source = Path(parsed.path)
            shutil.copyfile(source, target)
            return
        with urlopen(url) as response, target.open("wb") as fh:
            shutil.copyfileobj(response, fh)

    def _load_registry_index(self) -> Dict[str, Any]:
        if self._registry_cache is not None:
            return self._registry_cache
        url = self.registry_url
        if not url.endswith("index.json"):
            if urlparse(url).scheme:
                url = url.rstrip("/") + "/index.json"
            else:
                url = str(Path(url) / "index.json")
        parsed = urlparse(url)
        if parsed.scheme == "file":
            path = Path(parsed.path)
            data = json.loads(path.read_text(encoding="utf-8"))
        elif parsed.scheme in {"http", "https"}:
            with urlopen(url) as response:
                data = json.loads(response.read().decode("utf-8"))
        else:
            data = json.loads(Path(url).read_text(encoding="utf-8"))
        self._registry_cache = data
        return data

    def _update_local_index(self, name: str, version: str, archive_path: Path) -> None:
        index_path = LOCAL_REGISTRY / "index.json"
        if index_path.exists():
            index = json.loads(index_path.read_text(encoding="utf-8"))
        else:
            index = {"packages": {}}
        packages = index.setdefault("packages", {})
        versions = packages.setdefault(name, {})
        versions[version] = {
            "tarball": archive_path.as_uri(),
        }
        index_path.write_text(json.dumps(index, indent=2), encoding="utf-8")


__all__ = ["PackageManager", "LOCAL_REGISTRY", "OFFLINE_REGISTRY"]

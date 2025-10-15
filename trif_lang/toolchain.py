"""High level orchestration helpers for the Trif toolchain."""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Sequence

from .compiler import Compiler
from .package_manager import PackageManager
from .runtime import Runtime

_VALID_TARGETS = {
    "python": ".py",
    "javascript": ".js",
    "bytecode": ".trifc",
}


@dataclass
class BuildOptions:
    """Options that control how a build is executed."""

    targets: Sequence[str] = field(default_factory=lambda: ("python",))
    optimize: bool = True
    encrypt: str | None = None
    build_dir: Path = field(default_factory=lambda: Path("build"))


@dataclass
class BuildArtifact:
    """Metadata describing a produced build artifact."""

    target: str
    path: Path
    size: int


class Toolchain:
    """Coordinate compilation, runtime execution, and package management."""

    def __init__(self, project_root: Path | None = None) -> None:
        self.project_root = (project_root or Path.cwd()).resolve()
        self.compiler = Compiler()
        self.runtime = Runtime()
        self.package_manager = PackageManager(project_root=self.project_root)
        self.runtime.prepare_project_environment(self.project_root)

    # ------------------------------------------------------------------
    # Build pipeline
    def build(self, source: Path, *, options: BuildOptions | None = None) -> List[BuildArtifact]:
        """Compile ``source`` into the configured build directory.

        Returns a list of :class:`BuildArtifact` objects describing the emitted
        files. The build directory layout mirrors ``<build>/<target>/...`` to
        keep outputs isolated per backend.
        """

        opts = options or BuildOptions()
        targets = self._normalize_targets(opts.targets)
        build_root = self.resolve_build_directory(opts.build_dir)
        build_root.mkdir(parents=True, exist_ok=True)

        source_path = self._resolve_source(source)
        if not source_path.exists():
            raise FileNotFoundError(f"Source file {source_path} does not exist")

        artifacts: List[BuildArtifact] = []
        for target in targets:
            extension = _VALID_TARGETS[target]
            target_dir = build_root / target
            target_dir.mkdir(parents=True, exist_ok=True)
            relative = self._relative_to_project(source_path).with_suffix(extension)
            output_path = target_dir / relative
            output_path.parent.mkdir(parents=True, exist_ok=True)

            compiled = self.compiler.compile_file(source_path, target=target, optimize=opts.optimize)
            if target == "bytecode":
                assert isinstance(compiled, (bytes, bytearray))
                data = bytes(compiled)
                output_path.write_bytes(data)
                size = len(data)
            else:
                assert isinstance(compiled, str)
                text = compiled
                if opts.encrypt:
                    text = self.compiler.encrypt_output(text, opts.encrypt)
                output_path.write_text(text, encoding="utf-8")
                size = len(text.encode("utf-8"))

            artifacts.append(BuildArtifact(target=target, path=output_path, size=size))

        return artifacts

    def resolve_build_directory(self, path: Path | str) -> Path:
        candidate = Path(path)
        if not candidate.is_absolute():
            candidate = self.project_root / candidate
        return candidate

    def format_build_summary(self, artifacts: Sequence[BuildArtifact]) -> str:
        if not artifacts:
            return "No build artifacts were produced."

        header = ("Target", "Output", "Size")
        rows: List[tuple[str, str, str]] = [header]
        for artifact in artifacts:
            output_path = artifact.path
            try:
                display_path = output_path.relative_to(self.project_root)
            except ValueError:
                display_path = output_path
            rows.append(
                (
                    artifact.target,
                    str(display_path),
                    self._format_size(artifact.size),
                )
            )

        widths = [max(len(row[i]) for row in rows) for i in range(len(header))]
        lines: List[str] = []
        for idx, row in enumerate(rows):
            padded = [row[i].ljust(widths[i]) for i in range(len(header))]
            lines.append("  ".join(padded))
            if idx == 0:
                lines.append("  ".join("-" * width for width in widths))
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Runtime helpers
    def run(self, source: Path, *, optimize: bool = True, argv: Iterable[str] | None = None) -> None:
        source_path = self._resolve_source(source)
        code = self.compiler.compile_file(source_path, target="python", optimize=optimize)
        assert isinstance(code, str)
        self.runtime.execute_python(code, argv=list(argv or []))

    # ------------------------------------------------------------------
    # Internal helpers
    def _normalize_targets(self, targets: Sequence[str]) -> List[str]:
        if not targets:
            return ["python"]
        unique: List[str] = []
        for target in targets:
            if target not in _VALID_TARGETS:
                raise ValueError(f"Unknown target '{target}'")
            if target not in unique:
                unique.append(target)
        return unique

    def _resolve_source(self, source: Path) -> Path:
        candidate = Path(source)
        if not candidate.is_absolute():
            candidate = self.project_root / candidate
        return candidate.resolve()

    def _relative_to_project(self, path: Path) -> Path:
        try:
            return path.relative_to(self.project_root)
        except ValueError:
            return Path(path.name)

    def _format_size(self, size: int) -> str:
        units = ["B", "KB", "MB", "GB"]
        value = float(size)
        for unit in units:
            if value < 1024 or unit == units[-1]:
                if unit == "B":
                    return f"{int(value)} {unit}"
                return f"{value:.1f} {unit}"
            value /= 1024
        return f"{int(size)} B"


__all__ = ["BuildArtifact", "BuildOptions", "Toolchain"]

"""Trif Language package providing compiler, runtime, and tooling."""

from .cli import main
from .toolchain import BuildArtifact, BuildOptions, Toolchain

__all__ = ["main", "BuildArtifact", "BuildOptions", "Toolchain"]

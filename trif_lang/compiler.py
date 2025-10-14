"""Compiler and transpiler for the Trif language."""
from __future__ import annotations

import base64
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from . import lexer
from . import parser
from .ast_nodes import Module
from .codegen import PythonGenerator, JavaScriptGenerator
from .optimizer import Optimizer


@dataclass
class CompileResult:
    module: Module
    python: Optional[str] = None
    javascript: Optional[str] = None
    bytecode: Optional[bytes] = None


class Compiler:
    """High level interface around parsing, optimisation, and code generation."""

    def __init__(self) -> None:
        self.optimizer = Optimizer()

    def compile_source(self, source: str, target: str = "python", *, optimize: bool = True) -> str | bytes:
        tokens = lexer.tokenize(source)
        module = parser.parse(tokens)
        if optimize:
            module = self.optimizer.optimize(module)
        if target == "python":
            generator = PythonGenerator()
            return generator.generate(module)
        if target == "javascript":
            generator = JavaScriptGenerator()
            return generator.generate(module)
        if target == "bytecode":
            return self._to_bytecode(module)
        raise ValueError(f"Unknown target {target}")

    def compile_file(self, path: Path, *, target: str = "python", optimize: bool = True) -> str | bytes:
        source = path.read_text(encoding="utf-8")
        return self.compile_source(source, target=target, optimize=optimize)

    def encrypt_output(self, text: str, password: str) -> str:
        key = hashlib.sha256(password.encode("utf-8")).digest()
        data = text.encode("utf-8")
        encrypted = bytes(b ^ key[i % len(key)] for i, b in enumerate(data))
        return base64.urlsafe_b64encode(encrypted).decode("ascii")

    def decrypt_output(self, encoded: str, password: str) -> str:
        key = hashlib.sha256(password.encode("utf-8")).digest()
        data = base64.urlsafe_b64decode(encoded)
        decrypted = bytes(b ^ key[i % len(key)] for i, b in enumerate(data))
        return decrypted.decode("utf-8")

    def _to_bytecode(self, module: Module) -> bytes:
        python_code = PythonGenerator().generate(module)
        return python_code.encode("utf-8")


__all__ = ["Compiler", "CompileResult"]

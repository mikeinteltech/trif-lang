"""Code generators for Trif AST to target languages."""
from __future__ import annotations

from typing import List

from .ast_nodes import (
    Assign,
    Attribute,
    BinaryOp,
    Boolean,
    Call,
    DictLiteral,
    Expression,
    For,
    FunctionDef,
    If,
    Import,
    Let,
    ListLiteral,
    Module,
    Name,
    Null,
    Number,
    Return,
    Spawn,
    String,
    UnaryOp,
    While,
)


class BaseGenerator:
    def generate(self, module: Module) -> str:
        raise NotImplementedError


class PythonGenerator(BaseGenerator):
    """Generate Python code from a Trif module."""

    def __init__(self) -> None:
        self.lines: List[str] = []
        self.indent = 0

    def emit(self, line: str) -> None:
        self.lines.append("    " * self.indent + line)

    def generate(self, module: Module) -> str:
        self.emit("import pathlib")
        self.emit("import sys")
        self.emit("_trif_origin = pathlib.Path(__file__).resolve().parent if '__file__' in globals() else pathlib.Path.cwd()")
        self.emit("for _candidate in (_trif_origin, _trif_origin.parent):")
        self.indent += 1
        self.emit("candidate_pkg = _candidate / 'trif_lang'")
        self.emit("if candidate_pkg.exists():")
        self.indent += 1
        self.emit("if str(_candidate) not in sys.path:")
        self.indent += 1
        self.emit("sys.path.insert(0, str(_candidate))")
        self.indent -= 1
        self.emit("break")
        self.indent -= 1
        self.indent -= 1
        self.emit("from trif_lang.runtime import runtime")
        self.emit("")
        for stmt in module.body:
            self.visit(stmt)
        self.emit("")
        self.emit("if __name__ == '__main__':")
        self.indent += 1
        self.emit("runtime.default_entry_point(locals())")
        self.indent -= 1
        return "\n".join(self.lines)

    def visit(self, node):
        method = getattr(self, f"visit_{type(node).__name__}", None)
        if method is not None:
            return method(node)
        if isinstance(node, Expression):
            self.emit(self.visit_expression(node))
            return None
        raise TypeError(f"Unsupported node {type(node).__name__}")

    def visit_Module(self, node: Module):  # pragma: no cover - unused
        for stmt in node.body:
            self.visit(stmt)

    def visit_Import(self, node: Import):
        target = node.alias or node.module
        self.emit(f"{target} = runtime.import_module('{node.module}')")

    def visit_Let(self, node: Let):
        self.emit(f"{node.name} = {self.visit_expression(node.value)}")

    def visit_Assign(self, node: Assign):
        self.emit(f"{self.visit_expression(node.target)} = {self.visit_expression(node.value)}")

    def visit_FunctionDef(self, node: FunctionDef):
        params = ", ".join(node.params)
        self.emit(f"def {node.name}({params}):")
        self.indent += 1
        for stmt in node.body:
            self.visit(stmt)
        if not node.body or not isinstance(node.body[-1], Return):
            self.emit("return None")
        self.indent -= 1
        self.emit("")

    def visit_Return(self, node: Return):
        if node.value is None:
            self.emit("return None")
        else:
            self.emit(f"return {self.visit_expression(node.value)}")

    def visit_If(self, node: If):
        self.emit(f"if {self.visit_expression(node.test)}:")
        self.indent += 1
        for stmt in node.body:
            self.visit(stmt)
        if not node.body:
            self.emit("pass")
        self.indent -= 1
        if node.orelse:
            self.emit("else:")
            self.indent += 1
            for stmt in node.orelse:
                self.visit(stmt)
            if not node.orelse:
                self.emit("pass")
            self.indent -= 1

    def visit_While(self, node: While):
        self.emit(f"while {self.visit_expression(node.test)}:")
        self.indent += 1
        for stmt in node.body:
            self.visit(stmt)
        if not node.body:
            self.emit("pass")
        self.indent -= 1

    def visit_For(self, node: For):
        self.emit(f"for {node.target} in runtime.iterate({self.visit_expression(node.iterator)}):")
        self.indent += 1
        for stmt in node.body:
            self.visit(stmt)
        if not node.body:
            self.emit("pass")
        self.indent -= 1

    def visit_Spawn(self, node: Spawn):
        call_expr = self.visit_expression(node.call)
        self.emit(f"runtime.spawn(lambda: {call_expr})")

    def visit_expression(self, node: Expression) -> str:
        method = getattr(self, f"expr_{type(node).__name__}")
        return method(node)

    def expr_Name(self, node: Name) -> str:
        return node.id

    def expr_Number(self, node: Number) -> str:
        if node.value.is_integer():
            return str(int(node.value))
        return repr(node.value)

    def expr_String(self, node: String) -> str:
        return repr(node.value)

    def expr_Boolean(self, node: Boolean) -> str:
        return "True" if node.value else "False"

    def expr_Null(self, node: Null) -> str:
        return "None"

    def expr_BinaryOp(self, node: BinaryOp) -> str:
        op = node.op
        if op == "&&":
            op = "and"
        elif op == "||":
            op = "or"
        return f"({self.visit_expression(node.left)} {op} {self.visit_expression(node.right)})"

    def expr_UnaryOp(self, node: UnaryOp) -> str:
        op = node.op
        if op == "!":
            op = "not "
        return f"({op}{self.visit_expression(node.operand)})"

    def expr_Call(self, node: Call) -> str:
        args = ", ".join(self.visit_expression(arg) for arg in node.args)
        return f"{self.visit_expression(node.func)}({args})"

    def expr_Attribute(self, node: Attribute) -> str:
        return f"{self.visit_expression(node.value)}.{node.attr}"

    def expr_ListLiteral(self, node: ListLiteral) -> str:
        return "[" + ", ".join(self.visit_expression(e) for e in node.elements) + "]"

    def expr_DictLiteral(self, node: DictLiteral) -> str:
        pairs = ", ".join(
            f"{self.visit_expression(k)}: {self.visit_expression(v)}" for k, v in node.pairs
        )
        return "{" + pairs + "}"


class JavaScriptGenerator(BaseGenerator):
    """Generate JavaScript code from a Trif module."""

    def __init__(self) -> None:
        self.lines: List[str] = []
        self.indent = 0

    def emit(self, line: str) -> None:
        self.lines.append("    " * self.indent + line)

    def generate(self, module: Module) -> str:
        self.emit("import { runtime } from './trif_runtime.mjs';")
        for stmt in module.body:
            self.visit(stmt)
        if not any(isinstance(stmt, FunctionDef) and stmt.name == "main" for stmt in module.body):
            self.emit("runtime.defaultEntryPoint(globalThis);")
        return "\n".join(self.lines)

    def visit(self, node):
        method = getattr(self, f"visit_{type(node).__name__}", None)
        if method is not None:
            return method(node)
        if isinstance(node, Expression):
            self.emit(self.visit_expression(node) + ";")
            return None
        raise TypeError(f"Unsupported node {type(node).__name__}")

    def visit_Import(self, node: Import):
        target = node.alias or node.module
        self.emit(f"const {target} = runtime.importModule('{node.module}');")

    def visit_Let(self, node: Let):
        self.emit(f"let {node.name} = {self.visit_expression(node.value)};")

    def visit_Assign(self, node: Assign):
        self.emit(f"{self.visit_expression(node.target)} = {self.visit_expression(node.value)};")

    def visit_FunctionDef(self, node: FunctionDef):
        params = ", ".join(node.params)
        self.emit(f"function {node.name}({params}) {{")
        self.indent += 1
        for stmt in node.body:
            self.visit(stmt)
        if not node.body or not isinstance(node.body[-1], Return):
            self.emit("return null;")
        self.indent -= 1
        self.emit("}")

    def visit_Return(self, node: Return):
        if node.value is None:
            self.emit("return null;")
        else:
            self.emit(f"return {self.visit_expression(node.value)};")

    def visit_If(self, node: If):
        self.emit(f"if ({self.visit_expression(node.test)}) {{")
        self.indent += 1
        for stmt in node.body:
            self.visit(stmt)
        if not node.body:
            self.emit("return null;")
        self.indent -= 1
        if node.orelse:
            self.emit("} else {")
            self.indent += 1
            for stmt in node.orelse:
                self.visit(stmt)
            if not node.orelse:
                self.emit("return null;")
            self.indent -= 1
        self.emit("}")

    def visit_While(self, node: While):
        self.emit(f"while ({self.visit_expression(node.test)}) {{")
        self.indent += 1
        for stmt in node.body:
            self.visit(stmt)
        self.indent -= 1
        self.emit("}")

    def visit_For(self, node: For):
        iterator = self.visit_expression(node.iterator)
        self.emit(f"for (const {node.target} of runtime.iterate({iterator})) {{")
        self.indent += 1
        for stmt in node.body:
            self.visit(stmt)
        self.indent -= 1
        self.emit("}")

    def visit_Spawn(self, node: Spawn):
        call_expr = self.visit_expression(node.call)
        self.emit(f"runtime.spawn(() => {call_expr});")

    def visit_expression(self, node: Expression) -> str:
        method = getattr(self, f"expr_{type(node).__name__}")
        return method(node)

    def expr_Name(self, node: Name) -> str:
        return node.id

    def expr_Number(self, node: Number) -> str:
        if node.value.is_integer():
            return str(int(node.value))
        return repr(node.value)

    def expr_String(self, node: String) -> str:
        return repr(node.value)

    def expr_Boolean(self, node: Boolean) -> str:
        return "true" if node.value else "false"

    def expr_Null(self, node: Null) -> str:
        return "null"

    def expr_BinaryOp(self, node: BinaryOp) -> str:
        op = node.op
        if op == "&&":
            op = "&&"
        elif op == "||":
            op = "||"
        return f"({self.visit_expression(node.left)} {op} {self.visit_expression(node.right)})"

    def expr_UnaryOp(self, node: UnaryOp) -> str:
        op = node.op
        if op == "!":
            op = "!"
        return f"({op}{self.visit_expression(node.operand)})"

    def expr_Call(self, node: Call) -> str:
        args = ", ".join(self.visit_expression(arg) for arg in node.args)
        return f"{self.visit_expression(node.func)}({args})"

    def expr_Attribute(self, node: Attribute) -> str:
        return f"{self.visit_expression(node.value)}.{node.attr}"

    def expr_ListLiteral(self, node: ListLiteral) -> str:
        return "[" + ", ".join(self.visit_expression(e) for e in node.elements) + "]"

    def expr_DictLiteral(self, node: DictLiteral) -> str:
        pairs = ", ".join(
            f"[{self.visit_expression(k)}, {self.visit_expression(v)}]" for k, v in node.pairs
        )
        return f"runtime.makeMap([{pairs}])"


__all__ = ["PythonGenerator", "JavaScriptGenerator"]

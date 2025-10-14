"""Optimisation passes for Trif AST."""
from __future__ import annotations

from .ast_nodes import (
    BinaryOp,
    Boolean,
    DictLiteral,
    Expression,
    ListLiteral,
    Module,
    Name,
    Null,
    Number,
    String,
    UnaryOp,
)


class Optimizer:
    """Perform small AST optimisations such as constant folding."""

    def optimize(self, module: Module) -> Module:
        body = [self._optimize_node(stmt) for stmt in module.body]
        return Module(body)

    def _optimize_node(self, node):
        method = getattr(self, f"opt_{type(node).__name__}", self._identity)
        return method(node)

    def _identity(self, node):
        return node

    # Expressions
    def opt_BinaryOp(self, node: BinaryOp):
        left = self._optimize_expr(node.left)
        right = self._optimize_expr(node.right)
        if isinstance(left, Number) and isinstance(right, Number):
            if node.op == "+":
                return Number(left.value + right.value)
            if node.op == "-":
                return Number(left.value - right.value)
            if node.op == "*":
                return Number(left.value * right.value)
            if node.op == "/" and right.value != 0:
                return Number(left.value / right.value)
        if isinstance(left, String) and isinstance(right, String) and node.op == "+":
            return String(left.value + right.value)
        return BinaryOp(left, node.op, right)

    def opt_UnaryOp(self, node: UnaryOp):
        operand = self._optimize_expr(node.operand)
        if isinstance(operand, Number) and node.op == "-":
            return Number(-operand.value)
        if isinstance(operand, Boolean) and node.op == "!":
            return Boolean(not operand.value)
        return UnaryOp(node.op, operand)

    def opt_ListLiteral(self, node: ListLiteral):
        return ListLiteral([self._optimize_expr(e) for e in node.elements])

    def opt_DictLiteral(self, node: DictLiteral):
        return DictLiteral([(self._optimize_expr(k), self._optimize_expr(v)) for k, v in node.pairs])

    def opt_Number(self, node: Number):  # pragma: no cover - trivial
        return node

    def opt_String(self, node: String):  # pragma: no cover - trivial
        return node

    def opt_Boolean(self, node: Boolean):  # pragma: no cover
        return node

    def opt_Null(self, node: Null):  # pragma: no cover
        return node

    def opt_Name(self, node: Name):  # pragma: no cover
        return node

    def _optimize_expr(self, expr: Expression):
        return self._optimize_node(expr)


"""AST node definitions for the Trif language."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Node:
    pass


@dataclass
class Module(Node):
    body: List[Node]


@dataclass
class Import(Node):
    module: str
    alias: Optional[str] = None


@dataclass
class Let(Node):
    name: str
    value: "Expression"


@dataclass
class Assign(Node):
    target: "Expression"
    value: "Expression"


@dataclass
class FunctionDef(Node):
    name: str
    params: List[str]
    body: List[Node]


@dataclass
class Return(Node):
    value: Optional["Expression"]


@dataclass
class If(Node):
    test: "Expression"
    body: List[Node]
    orelse: List[Node] = field(default_factory=list)


@dataclass
class While(Node):
    test: "Expression"
    body: List[Node]


@dataclass
class For(Node):
    target: str
    iterator: "Expression"
    body: List[Node]


@dataclass
class Spawn(Node):
    call: "Call"


@dataclass
class Expression(Node):
    pass


@dataclass
class Name(Expression):
    id: str


@dataclass
class Number(Expression):
    value: float


@dataclass
class String(Expression):
    value: str


@dataclass
class Boolean(Expression):
    value: bool


@dataclass
class Null(Expression):
    pass


@dataclass
class BinaryOp(Expression):
    left: Expression
    op: str
    right: Expression


@dataclass
class UnaryOp(Expression):
    op: str
    operand: Expression


@dataclass
class Call(Expression):
    func: Expression
    args: List[Expression]


@dataclass
class Attribute(Expression):
    value: Expression
    attr: str


@dataclass
class ListLiteral(Expression):
    elements: List[Expression]


@dataclass
class DictLiteral(Expression):
    pairs: List[tuple[Expression, Expression]]


__all__ = [
    "Module",
    "Import",
    "Let",
    "Assign",
    "FunctionDef",
    "Return",
    "If",
    "While",
    "For",
    "Spawn",
    "Expression",
    "Name",
    "Number",
    "String",
    "Boolean",
    "Null",
    "BinaryOp",
    "UnaryOp",
    "Call",
    "Attribute",
    "ListLiteral",
    "DictLiteral",
]

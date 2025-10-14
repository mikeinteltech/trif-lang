"""Recursive descent parser for the Trif language."""
from __future__ import annotations

from typing import List, Sequence

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
from .lexer import Token


class Parser:
    def __init__(self, tokens: Sequence[Token]):
        self.tokens = tokens
        self.index = 0

    @property
    def current(self) -> Token:
        return self.tokens[self.index]

    def consume(self, expected: str | None = None) -> Token:
        token = self.current
        if expected and token.type != expected:
            raise SyntaxError(f"Expected {expected} but got {token.type} at line {token.line}")
        self.index += 1
        return token

    def match(self, *types: str) -> bool:
        if self.current.type in types:
            self.index += 1
            return True
        return False

    def parse_dotted_name(self) -> str:
        name = self.consume("NAME").value
        parts = [name]
        while self.current.type == "DOT":
            self.consume("DOT")
            parts.append(self.consume("NAME").value)
        return ".".join(parts)

    def parse(self) -> Module:
        body: List = []
        while self.current.type != "EOF":
            if self.current.type == "NEWLINE":
                self.consume()
                continue
            body.append(self.parse_statement())
        return Module(body)

    def parse_block(self) -> List:
        self.consume("LBRACE")
        body: List = []
        while self.current.type != "RBRACE":
            if self.current.type == "NEWLINE":
                self.consume()
                continue
            body.append(self.parse_statement())
        self.consume("RBRACE")
        return body

    def parse_statement(self):
        tok = self.current
        if tok.type == "IMPORT":
            self.consume()
            module_name = self.parse_dotted_name()
            alias = None
            if self.match("AS"):
                alias = self.consume("NAME").value
            self.optional_newline()
            return Import(module_name, alias)
        if tok.type == "LET":
            self.consume()
            name = self.consume("NAME").value
            op = self.consume("OP")
            if op.value != "=":
                raise SyntaxError("Expected '=' in let statement")
            value = self.parse_expression()
            self.optional_newline()
            return Let(name, value)
        if tok.type == "FN":
            self.consume()
            name = self.consume("NAME").value
            self.consume("LPAREN")
            params: List[str] = []
            if self.current.type != "RPAREN":
                while True:
                    params.append(self.consume("NAME").value)
                    if not self.match("COMMA"):
                        break
            self.consume("RPAREN")
            body = self.parse_block()
            self.optional_newline()
            return FunctionDef(name, params, body)
        if tok.type == "RETURN":
            self.consume()
            if self.current.type not in {"NEWLINE", "RBRACE", "EOF"}:
                value = self.parse_expression()
            else:
                value = None
            self.optional_newline()
            return Return(value)
        if tok.type == "IF":
            self.consume()
            test = self.parse_expression()
            body = self.parse_block()
            orelse: List = []
            if self.match("ELSE"):
                orelse = self.parse_block()
            self.optional_newline()
            return If(test, body, orelse)
        if tok.type == "WHILE":
            self.consume()
            test = self.parse_expression()
            body = self.parse_block()
            self.optional_newline()
            return While(test, body)
        if tok.type == "FOR":
            self.consume()
            target = self.consume("NAME").value
            self.consume("IN")
            iterator = self.parse_expression()
            body = self.parse_block()
            self.optional_newline()
            return For(target, iterator, body)
        if tok.type == "SPAWN":
            self.consume()
            call_expr = self.parse_expression()
            if not isinstance(call_expr, Call):
                raise SyntaxError("spawn expects a function call")
            self.optional_newline()
            return Spawn(call_expr)
        expr = self.parse_expression()
        if isinstance(expr, (Name, Attribute)) and self.current.type == "OP" and self.current.value == "=":
            self.consume("OP")
            value = self.parse_expression()
            self.optional_newline()
            return Assign(expr, value)
        self.optional_newline()
        return expr

    def optional_newline(self) -> None:
        while self.current.type == "NEWLINE":
            self.consume()

    def parse_expression(self) -> Expression:
        return self.parse_or()

    def parse_or(self) -> Expression:
        expr = self.parse_and()
        while self.current.type == "OP" and self.current.value == "||":
            op = self.consume("OP").value
            right = self.parse_and()
            expr = BinaryOp(expr, op, right)
        return expr

    def parse_and(self) -> Expression:
        expr = self.parse_equality()
        while self.current.type == "OP" and self.current.value == "&&":
            op = self.consume("OP").value
            right = self.parse_equality()
            expr = BinaryOp(expr, op, right)
        return expr

    def parse_equality(self) -> Expression:
        expr = self.parse_comparison()
        while self.current.type == "OP" and self.current.value in {"==", "!="}:
            op = self.consume("OP").value
            right = self.parse_comparison()
            expr = BinaryOp(expr, op, right)
        return expr

    def parse_comparison(self) -> Expression:
        expr = self.parse_term()
        while self.current.type == "OP" and self.current.value in {"<", ">", "<=", ">="}:
            op = self.consume("OP").value
            right = self.parse_term()
            expr = BinaryOp(expr, op, right)
        return expr

    def parse_term(self) -> Expression:
        expr = self.parse_factor()
        while self.current.type == "OP" and self.current.value in {"+", "-"}:
            op = self.consume("OP").value
            right = self.parse_factor()
            expr = BinaryOp(expr, op, right)
        return expr

    def parse_factor(self) -> Expression:
        expr = self.parse_unary()
        while self.current.type == "OP" and self.current.value in {"*", "/", "%"}:
            op = self.consume("OP").value
            right = self.parse_unary()
            expr = BinaryOp(expr, op, right)
        return expr

    def parse_unary(self) -> Expression:
        if self.current.type == "OP" and self.current.value in {"-", "!"}:
            op = self.consume("OP").value
            operand = self.parse_unary()
            return UnaryOp(op, operand)
        return self.parse_call_expression()

    def parse_call_expression(self) -> Expression:
        expr = self.parse_primary()
        while True:
            if self.match("LPAREN"):
                args: List[Expression] = []
                if self.current.type != "RPAREN":
                    while True:
                        args.append(self.parse_expression())
                        if not self.match("COMMA"):
                            break
                self.consume("RPAREN")
                expr = Call(expr, args)
            elif self.match("DOT"):
                attr = self.consume("NAME").value
                expr = Attribute(expr, attr)
            else:
                break
        return expr

    def parse_primary(self) -> Expression:
        tok = self.current
        if tok.type == "NUMBER":
            self.consume()
            return Number(float(tok.value))
        if tok.type == "STRING":
            self.consume()
            return String(tok.value)
        if tok.type == "TRUE":
            self.consume()
            return Boolean(True)
        if tok.type == "FALSE":
            self.consume()
            return Boolean(False)
        if tok.type == "NULL":
            self.consume()
            return Null()
        if tok.type == "NAME":
            self.consume()
            return Name(tok.value)
        if tok.type == "LPAREN":
            self.consume()
            expr = self.parse_expression()
            self.consume("RPAREN")
            return expr
        if tok.type == "LBRACKET":
            self.consume()
            elements: List[Expression] = []
            if self.current.type != "RBRACKET":
                while True:
                    elements.append(self.parse_expression())
                    if not self.match("COMMA"):
                        break
            self.consume("RBRACKET")
            return ListLiteral(elements)
        if tok.type == "LBRACE":
            # dictionary literal
            self.consume()
            pairs: List[tuple[Expression, Expression]] = []
            if self.current.type != "RBRACE":
                while True:
                    key = self.parse_expression()
                    self.consume("COLON")
                    value = self.parse_expression()
                    pairs.append((key, value))
                    if not self.match("COMMA"):
                        break
            self.consume("RBRACE")
            return DictLiteral(pairs)
        raise SyntaxError(f"Unexpected token {tok.type} at line {tok.line}")


def parse(tokens: Sequence[Token]) -> Module:
    parser = Parser(tokens)
    return parser.parse()


__all__ = ["parse", "Parser"]

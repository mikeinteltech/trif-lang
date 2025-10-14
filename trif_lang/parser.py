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
    ExportDefault,
    ExportNames,
    Expression,
    For,
    FunctionDef,
    If,
    Import,
    ImportFrom,
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

    def peek(self, offset: int = 1) -> Token:
        return self.tokens[self.index + offset]

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
            if self.current.type in {"NEWLINE", "SEMICOLON"}:
                self.consume()
                continue
            body.append(self.parse_statement())
        return Module(body)

    def parse_block(self) -> List:
        self.consume("LBRACE")
        body: List = []
        while self.current.type != "RBRACE":
            if self.current.type in {"NEWLINE", "SEMICOLON"}:
                self.consume()
                continue
            body.append(self.parse_statement())
        self.consume("RBRACE")
        return body

    def parse_statement(self):
        tok = self.current
        if tok.type == "IMPORT":
            stmt = self.parse_import_statement()
            self.optional_newline()
            return stmt
        if tok.type == "EXPORT":
            stmt = self.parse_export_statement()
            self.optional_newline()
            return stmt
        if tok.type in {"LET", "CONST"}:
            mutable = tok.type == "LET"
            self.consume()
            stmt = self.parse_variable_statement(mutable=mutable)
            self.optional_newline()
            return stmt
        if tok.type in {"FN", "FUNCTION"}:
            stmt = self.parse_function_statement()
            self.optional_newline()
            return stmt
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

    def parse_import_statement(self):
        self.consume("IMPORT")
        default_target: str | None = None
        names: List[tuple[str, str]] = []
        namespace: str | None = None

        if self.current.type == "STRING":
            module_name = self.consume("STRING").value
            alias = None
            if self.match("AS"):
                alias = self.consume("NAME").value
            return Import(module_name, alias)

        if self.current.type == "NAME" and self.peek().type in {"COMMA", "FROM"}:
            default_target = self.consume("NAME").value
            if self.match("COMMA"):
                if self.current.type == "LBRACE":
                    names = self.parse_import_specifiers()
                else:
                    raise SyntaxError("Expected named import list after comma")
        elif self.current.type == "LBRACE":
            names = self.parse_import_specifiers()
        elif self.current.type == "OP" and self.current.value == "*":
            self.consume("OP")
            self.consume("AS")
            namespace = self.consume("NAME").value

        if default_target or names or namespace:
            self.consume("FROM")
            module_name = self.parse_module_specifier()
            return ImportFrom(module_name, names, default=default_target, namespace=namespace)

        module_name = self.parse_module_specifier()
        alias = None
        if self.match("AS"):
            alias = self.consume("NAME").value
        return Import(module_name, alias)

    def parse_export_statement(self):
        self.consume("EXPORT")
        if self.current.type == "DEFAULT":
            self.consume("DEFAULT")
            if self.current.type in {"FN", "FUNCTION"}:
                return self.parse_function_statement(exported=True, is_default=True)
            if self.current.type in {"LET", "CONST"}:
                mutable = self.current.type == "LET"
                self.consume()
                return self.parse_variable_statement(mutable=mutable, exported=True, is_default=True)
            value = self.parse_expression()
            return ExportDefault(value)
        if self.current.type in {"FN", "FUNCTION"}:
            return self.parse_function_statement(exported=True)
        if self.current.type in {"LET", "CONST"}:
            mutable = self.current.type == "LET"
            self.consume()
            return self.parse_variable_statement(mutable=mutable, exported=True)
        if self.current.type == "LBRACE":
            specifiers = self.parse_export_specifiers()
            source = None
            if self.match("FROM"):
                source = self.parse_module_specifier()
            return ExportNames(specifiers, source)
        raise SyntaxError("Unsupported export statement")

    def parse_import_specifiers(self) -> List[tuple[str, str]]:
        self.consume("LBRACE")
        names: List[tuple[str, str]] = []
        while self.current.type != "RBRACE":
            imported = self.consume("NAME").value
            alias = imported
            if self.match("AS"):
                alias = self.consume("NAME").value
            names.append((imported, alias))
            if not self.match("COMMA"):
                break
        self.consume("RBRACE")
        return names

    def parse_export_specifiers(self) -> List[tuple[str, str]]:
        self.consume("LBRACE")
        names: List[tuple[str, str]] = []
        while self.current.type != "RBRACE":
            local = self.consume("NAME").value
            exported = local
            if self.match("AS"):
                exported = self.consume("NAME").value
            names.append((local, exported))
            if not self.match("COMMA"):
                break
        self.consume("RBRACE")
        return names

    def parse_module_specifier(self) -> str:
        if self.current.type == "STRING":
            return self.consume("STRING").value
        return self.parse_dotted_name()

    def parse_variable_statement(
        self,
        *,
        mutable: bool,
        exported: bool = False,
        is_default: bool = False,
    ) -> Let:
        name = self.consume("NAME").value
        if self.current.type != "OP" or self.current.value != "=":
            raise SyntaxError("Expected '=' in variable declaration")
        self.consume("OP")
        value = self.parse_expression()
        return Let(name, value, mutable=mutable, exported=exported, is_default=is_default)

    def parse_function_statement(
        self,
        *,
        exported: bool = False,
        is_default: bool = False,
    ) -> FunctionDef:
        self.consume()
        name: str | None = None
        if self.current.type == "NAME":
            name = self.consume("NAME").value
        if name is None:
            if is_default:
                name = "_default_export"
            else:
                raise SyntaxError("Function declaration requires a name")
        self.consume("LPAREN")
        params: List[str] = []
        if self.current.type != "RPAREN":
            while True:
                params.append(self.consume("NAME").value)
                if not self.match("COMMA"):
                    break
        self.consume("RPAREN")
        body = self.parse_block()
        return FunctionDef(name, params, body, exported=exported, is_default=is_default)

    def optional_newline(self) -> None:
        while self.current.type in {"NEWLINE", "SEMICOLON"}:
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

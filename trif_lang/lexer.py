"""Simple lexer for the Trif language."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List


TOKEN_SPECIFICATION = [
    ("NUMBER", r"\d+(?:\.\d+)?"),
    ("STRING", r'"([^"\\]|\\.)*"|\'([^\'\\]|\\.)*\''),
    ("COMMENT", r"//[^\n]*"),
    ("MCOMMENT", r"/\*.*?\*/"),
    ("NAME", r"[A-Za-z_][A-Za-z0-9_]*"),
    ("OP", r"==|!=|<=|>=|=>|&&|\|\||[+\-*/%=<>!]") ,
    ("NEWLINE", r"\n"),
    ("SKIP", r"[ \t]+"),
    ("LPAREN", r"\("),
    ("RPAREN", r"\)"),
    ("LBRACE", r"\{"),
    ("RBRACE", r"\}"),
    ("LBRACKET", r"\["),
    ("RBRACKET", r"\]"),
    ("COMMA", r","),
    ("COLON", r":"),
    ("DOT", r"\."),
    ("SEMICOLON", r";"),
]

TOKEN_RE = re.compile("|".join(f"(?P<{name}>{regex})" for name, regex in TOKEN_SPECIFICATION), re.DOTALL)

KEYWORDS = {
    "let",
    "fn",
    "function",
    "return",
    "if",
    "else",
    "while",
    "for",
    "in",
    "true",
    "false",
    "null",
    "import",
    "as",
    "from",
    "const",
    "export",
    "default",
    "spawn",
}


@dataclass
class Token:
    type: str
    value: str
    line: int
    column: int

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"Token({self.type}, {self.value!r}, {self.line}, {self.column})"


def tokenize(source: str) -> List[Token]:
    tokens: List[Token] = []
    line = 1
    column = 1
    index = 0
    while index < len(source):
        match = TOKEN_RE.match(source, index)
        if not match:
            raise SyntaxError(f"Unexpected character {source[index]!r} at line {line} column {column}")
        kind = match.lastgroup
        value = match.group()
        if kind == "NEWLINE":
            tokens.append(Token("NEWLINE", value, line, column))
            line += 1
            column = 1
        elif kind in {"SKIP", "COMMENT"}:
            column += len(value)
        elif kind == "MCOMMENT":
            line += value.count("\n")
            last_newline = value.rfind("\n")
            if last_newline != -1:
                column = len(value) - last_newline
            else:
                column += len(value)
        else:
            if kind == "NAME" and value in KEYWORDS:
                kind = value.upper()
            if kind == "STRING":
                value = bytes(value[1:-1], "utf-8").decode("unicode_escape")
            tokens.append(Token(kind, value, line, column))
            column += len(match.group())
        index = match.end()
    tokens.append(Token("EOF", "", line, column))
    return tokens


__all__ = ["Token", "tokenize"]

"""Публичный API пакета для работы с логическими формулами.

Модуль собирает в одном месте основные сущности проекта:
- AST-узлы;
- исключения;
- функцию разбора формулы;
- функцию проверки структуры СКНФ.

Такой файл делает импорт удобным для вызывающего кода:
`from logic_parser import parse_formula, is_sknf`.
"""

from .ast_nodes import BinaryExpression, BooleanConstant, Identifier, UnaryExpression
from .errors import FormulaError, LexerError, ParserError
from .parser import parse_formula
from .sknf import is_sknf

__all__ = [
    "BinaryExpression",
    "BooleanConstant",
    "FormulaError",
    "Identifier",
    "LexerError",
    "ParserError",
    "UnaryExpression",
    "is_sknf",
    "parse_formula",
]

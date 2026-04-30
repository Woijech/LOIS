"""Лексический анализатор логических формул.

Модуль преобразует исходную строку в последовательность токенов, с которыми
дальше работает парсер. Здесь решаются задачи низкого уровня:
- пропуск пробелов;
- распознавание операторов и скобок;
- чтение имён переменных;
- распознавание логических констант `0` и `1`;
- фиксация позиции для понятных сообщений об ошибках.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .errors import LexerError


class TokenType(str, Enum):
    """Перечисление всех токенов, допустимых в грамматике формулы."""

    IDENTIFIER = "IDENTIFIER"
    CONSTANT = "CONSTANT"
    NOT = "NOT"
    AND = "AND"
    OR = "OR"
    IMPLIES = "IMPLIES"
    EQUIV = "EQUIV"
    LPAREN = "LPAREN"
    RPAREN = "RPAREN"
    EOF = "EOF"


@dataclass(frozen=True, slots=True)
class Token:
    """Один токен лексического анализа.

    Attributes:
        token_type: Категория токена, например `IDENTIFIER` или `AND`.
        value: Исходное текстовое значение токена.
        position: Позиция начала токена в исходной строке, начиная с нуля.
    """

    token_type: TokenType
    value: str
    position: int


_OPERATORS: dict[str, tuple[TokenType, str]] = {
    "->": (TokenType.IMPLIES, "->"),
    "/\\": (TokenType.AND, "/\\"),
    "\\/": (TokenType.OR, "\\/"),
    "~": (TokenType.EQUIV, "~"),
    "!": (TokenType.NOT, "!"),
    "(": (TokenType.LPAREN, "("),
    ")": (TokenType.RPAREN, ")"),
}


class Lexer:
    """Пошаговый разбор строки формулы на токены."""

    def __init__(self, text: str) -> None:
        """Сохраняет входную строку и подготавливает курсор чтения."""

        self._text = text
        self._length = len(text)
        self._position = 0

    def tokenize(self) -> list[Token]:
        """Преобразует строку формулы в список токенов.

        Returns:
            Список токенов, завершающийся служебным токеном `EOF`.

        Raises:
            LexerError: Если ввод пустой или содержит недопустимые символы.
        """

        if not self._text.strip():
            raise LexerError("Пустая строка: введите логическую формулу.")

        tokens: list[Token] = []
        while self._position < self._length:
            current = self._text[self._position]

            if current.isspace():
                self._position += 1
                continue

            operator_token = self._read_operator()
            if operator_token is not None:
                tokens.append(operator_token)
                continue

            if current.isalpha():
                tokens.append(self._read_identifier())
                continue

            if current in {"0", "1"}:
                tokens.append(Token(TokenType.CONSTANT, current, self._position))
                self._position += 1
                continue

            if current == "/":
                raise LexerError(
                    "Оператор конъюнкции должен быть записан как '/\\' "
                    f"в позиции {self._position + 1}."
                )

            if current == "\\":
                raise LexerError(
                    "Оператор дизъюнкции должен быть записан как '\\/' "
                    f"в позиции {self._position + 1}."
                )

            raise LexerError(
                f"Недопустимый символ '{current}' в позиции {self._position + 1}."
            )

        tokens.append(Token(TokenType.EOF, "", self._length))
        return tokens

    def _read_operator(self) -> Token | None:
        """Пытается распознать оператор или скобку в текущей позиции.

        Returns:
            Объект `Token`, если оператор найден, иначе `None`.
        """

        for raw in ("->", "/\\", "\\/", "~", "!", "(", ")"):
            if self._text.startswith(raw, self._position):
                token_type, value = _OPERATORS[raw]
                token = Token(token_type, value, self._position)
                self._position += len(raw)
                return token
        return None

    def _read_identifier(self) -> Token:
        """Считывает имя переменной, начинающееся с буквы.

        После первого символа допускаются буквы, цифры и символ подчёркивания.
        """

        start = self._position
        self._position += 1

        while self._position < self._length:
            current = self._text[self._position]
            if current.isalnum() or current == "_":
                self._position += 1
                continue
            break

        return Token(TokenType.IDENTIFIER, self._text[start:self._position], start)

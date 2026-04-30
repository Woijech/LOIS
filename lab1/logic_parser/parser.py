"""Синтаксический анализатор с прямым построением дерева.

Модуль реализует рекурсивный спуск для инфиксных логических выражений.
Главное ограничение задачи соблюдается здесь: формула разбирается напрямую
в AST без промежуточного перевода в ОПЗ, постфиксную запись или shunting-yard.
"""

from __future__ import annotations

from .ast_nodes import (
    BinaryExpression,
    BooleanConstant,
    Expression,
    Identifier,
    UnaryExpression,
)
from .errors import ParserError
from .lexer import Lexer, Token, TokenType

_BINARY_TOKENS = {
    TokenType.AND,
    TokenType.OR,
    TokenType.IMPLIES,
    TokenType.EQUIV,
}


class Parser:
    """Рекурсивный нисходящий парсер логических формул."""

    def __init__(self, text: str) -> None:
        """Токенизирует входную строку и ставит курсор в начало списка токенов."""

        self._tokens = Lexer(text).tokenize()
        self._index = 0

    def parse(self) -> Expression:
        """Разбирает всю формулу и возвращает корень дерева выражения.

        Returns:
            Корневой узел AST для всей формулы.

        Raises:
            ParserError: Если после корректного выражения остаются лишние токены.
        """

        expression = self._parse_equivalence()
        current = self._current()

        if current.token_type != TokenType.EOF:
            raise self._unexpected_after_expression(current)

        return expression

    def _parse_equivalence(self) -> Expression:
        """Разбирает уровень эквивалентности `~`.

        Это самый низкий приоритет среди поддерживаемых бинарных операций,
        поэтому разбор начинается именно отсюда.
        """

        expression = self._parse_implication()

        while self._match(TokenType.EQUIV):
            operator = self._previous()
            right = self._parse_implication()
            expression = BinaryExpression(operator.value, expression, right)

        return expression

    def _parse_implication(self) -> Expression:
        """Разбирает уровень импликации `->`.

        Импликация сделана правоассоциативной:
        `A -> B -> C` интерпретируется как `A -> (B -> C)`.
        """

        expression = self._parse_disjunction()

        if self._match(TokenType.IMPLIES):
            operator = self._previous()
            right = self._parse_implication()
            return BinaryExpression(operator.value, expression, right)

        return expression

    def _parse_disjunction(self) -> Expression:
        """Разбирает цепочку дизъюнкций `\\/`."""

        expression = self._parse_conjunction()

        while self._match(TokenType.OR):
            operator = self._previous()
            right = self._parse_conjunction()
            expression = BinaryExpression(operator.value, expression, right)

        return expression

    def _parse_conjunction(self) -> Expression:
        """Разбирает цепочку конъюнкций `/\\`."""

        expression = self._parse_unary()

        while self._match(TokenType.AND):
            operator = self._previous()
            right = self._parse_unary()
            expression = BinaryExpression(operator.value, expression, right)

        return expression

    def _parse_unary(self) -> Expression:
        """Разбирает унарный оператор отрицания `!`.

        Если оператор найден, сразу создаётся унарный узел дерева, а затем
        рекурсивно разбирается его операнд.
        """

        if self._match(TokenType.NOT):
            operator = self._previous()
            upcoming = self._current()
            if upcoming.token_type in _BINARY_TOKENS | {TokenType.RPAREN, TokenType.EOF}:
                raise ParserError(
                    f"Унарный оператор '!' в позиции {operator.position + 1} "
                    "должен применяться к переменной или подформуле."
                )
            return UnaryExpression(operator.value, self._parse_unary())

        return self._parse_primary()

    def _parse_primary(self) -> Expression:
        """Разбирает базовые элементы грамматики.

        К базовым элементам относятся:
        - идентификатор;
        - логическая константа `0` или `1`;
        - подформула в круглых скобках.
        """

        current = self._current()

        if self._match(TokenType.IDENTIFIER):
            return Identifier(self._previous().value)

        if self._match(TokenType.CONSTANT):
            return BooleanConstant(self._previous().value == "1")

        if self._match(TokenType.LPAREN):
            opening = self._previous()
            expression = self._parse_equivalence()
            if not self._match(TokenType.RPAREN):
                raise ParserError(
                    f"Не найдена закрывающая скобка для '(' в позиции "
                    f"{opening.position + 1}."
                )
            return expression

        if current.token_type == TokenType.RPAREN:
            raise ParserError(
                f"Лишняя закрывающая скобка ')' в позиции {current.position + 1}."
            )

        if current.token_type in _BINARY_TOKENS:
            raise ParserError(
                f"Ожидался операнд, но найден бинарный оператор '{current.value}' "
                f"в позиции {current.position + 1}."
            )

        if current.token_type == TokenType.EOF:
            raise ParserError("Ожидался операнд, но выражение закончилось.")

        raise ParserError(
            f"Мусорный ввод около позиции {current.position + 1}: '{current.value}'."
        )

    def _unexpected_after_expression(self, token: Token) -> ParserError:
        """Формирует понятную ошибку для хвоста после завершённого выражения."""

        if token.token_type in {
            TokenType.IDENTIFIER,
            TokenType.CONSTANT,
            TokenType.LPAREN,
            TokenType.NOT,
        }:
            return ParserError(
                f"После завершённого выражения найден '{token.value or token.token_type}'. "
                f"Вероятно, пропущен оператор в позиции {token.position + 1}."
            )

        if token.token_type == TokenType.RPAREN:
            return ParserError(
                f"Лишняя закрывающая скобка ')' в позиции {token.position + 1}."
            )

        return ParserError(
            f"Некорректный хвост выражения в позиции {token.position + 1}: "
            f"'{token.value}'."
        )

    def _match(self, token_type: TokenType) -> bool:
        """Проверяет текущий токен и сдвигает курсор при совпадении."""

        if self._current().token_type == token_type:
            self._index += 1
            return True
        return False

    def _current(self) -> Token:
        """Возвращает токен, на который сейчас указывает курсор разбора."""

        return self._tokens[self._index]

    def _previous(self) -> Token:
        """Возвращает токен, который был успешно прочитан последним."""

        return self._tokens[self._index - 1]


def parse_formula(text: str) -> Expression:
    """Разбирает инфиксную логическую формулу напрямую в дерево выражения.

    Это удобная точка входа для внешнего кода, скрывающая внутренний класс
    `Parser` и оставляющая простой вызов верхнего уровня.
    """

    return Parser(text).parse()

"""AST-узлы логического выражения.

Этот модуль определяет структуру дерева разбора, которое строит парсер.
Каждый класс отражает отдельный тип узла:
- `Identifier` — переменная;
- `BooleanConstant` — логическая константа;
- `UnaryExpression` — унарная операция;
- `BinaryExpression` — бинарная операция.

Классы объявлены как `dataclass`, чтобы хранить только данные и не смешивать
структуру дерева с логикой парсинга, печати или проверки СКНФ.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Expression:
    """Базовый тип для всех узлов дерева разбора.

    Класс нужен как общий контракт: функции могут принимать `Expression`,
    не зная заранее, получили они переменную, унарный или бинарный узел.
    """


@dataclass(frozen=True, slots=True)
class Identifier(Expression):
    """Лист дерева, представляющий логическую переменную.

    Attributes:
        name: Исходное имя переменной из формулы, например `A` или `VAR2`.
    """

    name: str


@dataclass(frozen=True, slots=True)
class BooleanConstant(Expression):
    """Лист дерева, представляющий логическую константу.

    Attributes:
        value: Булево значение константы: `False` для `0`, `True` для `1`.
    """

    value: bool


@dataclass(frozen=True, slots=True)
class UnaryExpression(Expression):
    """Узел унарной операции.

    В текущей задаче используется для отрицания `!`, но структура остаётся
    универсальной и позволяет хранить любой унарный оператор.

    Attributes:
        operator: Символ оператора, например `!`.
        operand: Подвыражение, к которому применяется оператор.
    """

    operator: str
    operand: Expression


@dataclass(frozen=True, slots=True)
class BinaryExpression(Expression):
    """Узел бинарной логической операции.

    Attributes:
        operator: Символ бинарного оператора, например `/\\`, `\\/`, `->`, `~`.
        left: Левое подвыражение.
        right: Правое подвыражение.
    """

    operator: str
    left: Expression
    right: Expression

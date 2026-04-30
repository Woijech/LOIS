"""Структурная проверка выражения на соответствие СКНФ.

Модуль анализирует уже построенное дерево выражения и не зависит от исходной
строки. Это важно для требований задачи: проверка выполняется по AST, а не
по регулярным выражениям, строковым шаблонам или таблице истинности.
"""

from __future__ import annotations

from .ast_nodes import BinaryExpression, Expression, Identifier, UnaryExpression


def is_sknf(node: Expression) -> bool:
    """Проверяет, соответствует ли дерево формулы структуре СКНФ.

    В рамках этого проекта под допустимой структурой понимается:
    - вся формула — конъюнкция одной или нескольких клауз;
    - каждая клауза — дизъюнкция литералов;
    - литерал — переменная или отрицание переменной.
    - в каждой клаузе каждая переменная встречается ровно один раз;
    - все клаузы содержат один и тот же набор переменных.
    """

    clauses = _collect_conjunction_terms(node)
    if not clauses:
        return False

    clause_variable_sets: list[frozenset[str]] = []

    for clause in clauses:
        variables = _extract_clause_variables(clause)
        if variables is None:
            return False
        clause_variable_sets.append(frozenset(variables))

    reference_variables = clause_variable_sets[0]
    return all(variables == reference_variables for variables in clause_variable_sets)


def _collect_conjunction_terms(node: Expression) -> list[Expression]:
    """Разворачивает дерево по оператору конъюнкции `/\\`.

    Например, выражение `(A \\/ B) /\\ C /\\ D` будет преобразовано в список
    из трёх элементов: `[(A \\/ B), C, D]`.
    """

    if isinstance(node, BinaryExpression) and node.operator == "/\\":
        return _collect_conjunction_terms(node.left) + _collect_conjunction_terms(
            node.right
        )
    return [node]


def _collect_disjunction_terms(node: Expression) -> list[Expression]:
    """Разворачивает дерево по оператору дизъюнкции `\\/`."""

    if isinstance(node, BinaryExpression) and node.operator == "\\/":
        return _collect_disjunction_terms(node.left) + _collect_disjunction_terms(
            node.right
        )
    return [node]


def _extract_clause_variables(node: Expression) -> set[str] | None:
    """Извлекает переменные из клаузы СКНФ.

    Возвращает множество имён переменных, если клауза состоит только из
    литералов и каждая переменная встречается в ней ровно один раз.
    Иначе возвращает `None`.
    """

    literals = _collect_disjunction_terms(node)
    variables: set[str] = set()

    for literal in literals:
        variable_name = _literal_variable_name(literal)
        if variable_name is None or variable_name in variables:
            return None
        variables.add(variable_name)

    return variables


def _literal_variable_name(node: Expression) -> str | None:
    """Возвращает имя переменной, если узел является литералом.

    Допустимы только два варианта:
    - переменная;
    - отрицание, применённое непосредственно к переменной.
    """

    if isinstance(node, Identifier):
        return node.name
    if isinstance(node, UnaryExpression) and node.operator == "!":
        if isinstance(node.operand, Identifier):
            return node.operand.name
    return None

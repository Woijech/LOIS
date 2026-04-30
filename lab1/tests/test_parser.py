from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from logic_parser import (
    BinaryExpression,
    BooleanConstant,
    Identifier,
    LexerError,
    ParserError,
    UnaryExpression,
    parse_formula,
)


class ParserTests(unittest.TestCase):
    def test_parse_identifier(self) -> None:
        tree = parse_formula("A")
        self.assertEqual(tree, Identifier("A"))

    def test_parse_identifier_with_digits(self) -> None:
        tree = parse_formula("VAR2")
        self.assertEqual(tree, Identifier("VAR2"))

    def test_parse_false_constant(self) -> None:
        tree = parse_formula("0")
        self.assertEqual(tree, BooleanConstant(False))

    def test_parse_true_constant(self) -> None:
        tree = parse_formula("1")
        self.assertEqual(tree, BooleanConstant(True))

    def test_parse_unary_expression(self) -> None:
        tree = parse_formula("!A")
        self.assertEqual(tree, UnaryExpression("!", Identifier("A")))

    def test_parse_parenthesized_unary_expression(self) -> None:
        tree = parse_formula("!(A \\/ B)")
        self.assertEqual(
            tree,
            UnaryExpression(
                "!",
                BinaryExpression("\\/", Identifier("A"), Identifier("B")),
            ),
        )

    def test_parse_conjunction_before_disjunction(self) -> None:
        tree = parse_formula("(A \\/ B /\\ C)")
        self.assertEqual(
            tree,
            BinaryExpression(
                "\\/",
                Identifier("A"),
                BinaryExpression("/\\", Identifier("B"), Identifier("C")),
            ),
        )

    def test_parse_parentheses_override_precedence(self) -> None:
        tree = parse_formula("((A \\/ B) /\\ C)")
        self.assertEqual(
            tree,
            BinaryExpression(
                "/\\",
                BinaryExpression("\\/", Identifier("A"), Identifier("B")),
                Identifier("C"),
            ),
        )

    def test_implication_is_right_associative(self) -> None:
        tree = parse_formula("(A -> B -> C)")
        self.assertEqual(
            tree,
            BinaryExpression(
                "->",
                Identifier("A"),
                BinaryExpression("->", Identifier("B"), Identifier("C")),
            ),
        )

    def test_equivalence_is_left_associative(self) -> None:
        tree = parse_formula("(A ~ B ~ C)")
        self.assertEqual(
            tree,
            BinaryExpression(
                "~",
                BinaryExpression("~", Identifier("A"), Identifier("B")),
                Identifier("C"),
            ),
        )

    def test_complex_expression(self) -> None:
        tree = parse_formula("(!(A /\\ B) -> C ~ D)")
        self.assertEqual(
            tree,
            BinaryExpression(
                "~",
                BinaryExpression(
                    "->",
                    UnaryExpression(
                        "!",
                        BinaryExpression("/\\", Identifier("A"), Identifier("B")),
                    ),
                    Identifier("C"),
                ),
                Identifier("D"),
            ),
        )

    def test_deep_negated_constant_expression(self) -> None:
        negation_count = 30
        formula = f"({'!(' * negation_count}0{')' * negation_count} /\\ 1)"
        tree = parse_formula(formula)
        self.assertIsInstance(tree, BinaryExpression)
        self.assertEqual(tree.operator, "/\\")
        self.assertEqual(tree.right, BooleanConstant(True))

        operand = tree.left
        for _ in range(negation_count):
            self.assertIsInstance(operand, UnaryExpression)
            self.assertEqual(operand.operator, "!")
            operand = operand.operand
        self.assertEqual(operand, BooleanConstant(False))

    def test_empty_input_raises_error(self) -> None:
        with self.assertRaisesRegex(LexerError, "Пустая строка"):
            parse_formula("   ")

    def test_invalid_character_raises_error(self) -> None:
        with self.assertRaisesRegex(LexerError, "Недопустимый символ"):
            parse_formula("A + B")

    def test_incomplete_conjunction_raises_clear_error(self) -> None:
        with self.assertRaisesRegex(LexerError, "Оператор конъюнкции"):
            parse_formula("A / B")

    def test_incomplete_disjunction_raises_clear_error(self) -> None:
        with self.assertRaisesRegex(LexerError, "Оператор дизъюнкции"):
            parse_formula("A \\ B")

    def test_missing_closing_parenthesis_raises_error(self) -> None:
        with self.assertRaisesRegex(ParserError, "Не найдена закрывающая скобка"):
            parse_formula("(A /\\ B")

    def test_extra_closing_parenthesis_raises_error(self) -> None:
        with self.assertRaisesRegex(ParserError, "Лишняя закрывающая скобка"):
            parse_formula("A)")

    def test_two_binary_operators_in_a_row_raise_error(self) -> None:
        with self.assertRaisesRegex(ParserError, "Ожидался операнд"):
            parse_formula("A /\\ \\/ B")

    def test_expression_cannot_start_with_binary_operator(self) -> None:
        with self.assertRaisesRegex(ParserError, "Ожидался операнд"):
            parse_formula("/\\ A")

    def test_unary_operator_requires_operand(self) -> None:
        with self.assertRaisesRegex(ParserError, "Унарный оператор '!'"):
            parse_formula("!")

    def test_operator_at_end_raises_error(self) -> None:
        with self.assertRaisesRegex(ParserError, "Ожидался операнд"):
            parse_formula("A ->")

    def test_binary_expression_requires_outer_parentheses(self) -> None:
        with self.assertRaisesRegex(ParserError, "внешние скобки"):
            parse_formula("A /\\ B")

    def test_user_formula_without_outer_parentheses_raises_error(self) -> None:
        formula = "!(!(!0 /\\ 1) \\/ (!!1 /\\ !0)) ~ (0 \\/ !1)"
        with self.assertRaisesRegex(ParserError, "внешние скобки"):
            parse_formula(formula)

    def test_user_formula_with_outer_parentheses_is_valid(self) -> None:
        formula = "(!(!(!0 /\\ 1) \\/ (!!1 /\\ !0)) ~ (0 \\/ !1))"
        tree = parse_formula(formula)
        self.assertIsInstance(tree, BinaryExpression)

    def test_missing_operator_between_identifiers_raises_error(self) -> None:
        with self.assertRaisesRegex(ParserError, "пропущен оператор"):
            parse_formula("A B")

    def test_missing_operator_before_parenthesis_raises_error(self) -> None:
        with self.assertRaisesRegex(ParserError, "пропущен оператор"):
            parse_formula("A(B)")

    def test_garbage_input_after_formula_raises_error(self) -> None:
        with self.assertRaisesRegex(LexerError, "Недопустимый символ"):
            parse_formula("A #")

    def test_identifier_can_contain_underscore(self) -> None:
        tree = parse_formula("(VAR_2 /\\ X1)")
        self.assertEqual(
            tree,
            BinaryExpression("/\\", Identifier("VAR_2"), Identifier("X1")),
        )

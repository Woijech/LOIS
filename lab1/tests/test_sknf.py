from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from logic_parser import is_sknf, parse_formula


class SknfTests(unittest.TestCase):
    def test_single_literal_is_sknf(self) -> None:
        self.assertTrue(is_sknf(parse_formula("A")))

    def test_negated_literal_is_sknf(self) -> None:
        self.assertTrue(is_sknf(parse_formula("!A")))

    def test_single_clause_is_sknf(self) -> None:
        self.assertTrue(is_sknf(parse_formula("(A \\/ !B \\/ C)")))

    def test_multiple_clauses_are_sknf(self) -> None:
        self.assertTrue(
            is_sknf(parse_formula("((A \\/ !B \\/ C) /\\ (!A \\/ B \\/ !C))"))
        )

    def test_nested_conjunction_with_full_clauses_is_sknf(self) -> None:
        self.assertTrue(
            is_sknf(parse_formula("((A \\/ B) /\\ (!A \\/ !B))"))
        )

    def test_clause_must_contain_all_formula_variables(self) -> None:
        self.assertFalse(is_sknf(parse_formula("(A /\\ (B \\/ !C))")))

    def test_all_clauses_must_have_same_variable_count(self) -> None:
        self.assertFalse(is_sknf(parse_formula("((A \\/ !B) /\\ (!A \\/ B \\/ C))")))

    def test_implication_is_not_sknf(self) -> None:
        self.assertFalse(is_sknf(parse_formula("(A -> B)")))

    def test_equivalence_is_not_sknf(self) -> None:
        self.assertFalse(is_sknf(parse_formula("(A ~ B)")))

    def test_negation_of_subformula_is_not_sknf(self) -> None:
        self.assertFalse(is_sknf(parse_formula("!(A \\/ B)")))

    def test_clause_cannot_contain_conjunction(self) -> None:
        self.assertFalse(is_sknf(parse_formula("(A \\/ (B /\\ C))")))

    def test_flat_disjunction_of_literals_is_single_clause(self) -> None:
        self.assertTrue(is_sknf(parse_formula("((A \\/ B) \\/ (!C \\/ D))")))

    def test_double_negation_is_not_literal(self) -> None:
        self.assertFalse(is_sknf(parse_formula("!!A")))

    def test_negation_inside_clause_must_target_identifier(self) -> None:
        self.assertFalse(is_sknf(parse_formula("(!A \\/ !(!B))")))

    def test_clause_cannot_repeat_same_variable(self) -> None:
        self.assertFalse(is_sknf(parse_formula("((A \\/ !A) /\\ (!A \\/ B))")))

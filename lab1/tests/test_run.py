from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from run import load_formula_from_file


class RunTests(unittest.TestCase):
    def test_load_formula_from_file_strips_surrounding_whitespace(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            formula_file = Path(temp_dir) / "formula.txt"
            formula_file.write_text("\n  (A \\/ !B) /\\ C  \n", encoding="utf-8")

            self.assertEqual(
                load_formula_from_file(str(formula_file)),
                "(A \\/ !B) /\\ C",
            )

    def test_load_formula_from_empty_file_raises_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            formula_file = Path(temp_dir) / "formula.txt"
            formula_file.write_text("   \n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "Файл с формулой пуст"):
                load_formula_from_file(str(formula_file))


if __name__ == "__main__":
    unittest.main()

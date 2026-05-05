from __future__ import annotations

import re
from datetime import UTC, datetime
from html import escape
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from PIL import Image


DIAGRAM_DIR = Path(__file__).resolve().parent
PNG_DIR = DIAGRAM_DIR / "png"


DOT_HEADER = """digraph G {
  graph [rankdir=TB, bgcolor=white, splines=polyline, nodesep=0.45, ranksep=0.5];
  node [
    fontname="Times New Roman",
    fontsize=12,
    color=black,
    penwidth=1.2,
    style=solid,
    margin="0.08,0.06"
  ];
  edge [
    fontname="Times New Roman",
    fontsize=11,
    color=black,
    penwidth=1.1,
    arrowsize=0.7
  ];
"""


def normalize_branch_ports(body: str) -> str:
    """Routes yes/no branches from a condition diamond through fixed sides."""

    body = re.sub(
        r"(\b[A-Za-z_][A-Za-z0-9_]*\b) -> (\b[A-Za-z_][A-Za-z0-9_]*\b) \[label=\"да\"\];",
        r'\1:e -> \2 [label="да"];',
        body,
    )
    return re.sub(
        r"(\b[A-Za-z_][A-Za-z0-9_]*\b) -> (\b[A-Za-z_][A-Za-z0-9_]*\b) \[label=\"нет\"\];",
        r'\1:w -> \2 [label="нет"];',
        body,
    )


def dot(output_name: str, body: str) -> str:
    body = normalize_branch_ports(body)
    return f"@startdot {output_name}\n{DOT_HEADER}{body}\n}}\n@enddot\n"


def activity(output_name: str, body: str) -> str:
    return dot(output_name, body.strip())


PUML: dict[str, str] = {
    "_lexer_init.puml": activity(
        "_lexer_init",
        """
  start [label="Начало", shape=oval];
  p1 [label="self._text = text", shape=box];
  p2 [label="self._length = len(text)", shape=box];
  p3 [label="self._position = 0", shape=box];
  stop [label="Конец", shape=oval];

  start -> p1 -> p2 -> p3 -> stop;
""",
    ),
    "lexer_read_identifier.puml": activity(
        "read_identifier_Lexer",
        r"""
  start [label="Начало", shape=oval];
  p1 [label="start = self._position", shape=box];
  p2 [label="self._position += 1", shape=box];
  d1 [label="self._position < self._length?", shape=diamond];
  p3 [label="current = self._text[self._position]", shape=box];
  d2 [label="current.isalnum()\nили current == '_'?", shape=diamond];
  p4 [label="self._position += 1", shape=box];
  ret [label="Возврат Token(IDENTIFIER,\ntext[start:self._position], start)", shape=parallelogram];
  stop [label="Конец", shape=oval];

  start -> p1 -> p2 -> d1;
  d1 -> p3 [label="да"];
  p3 -> d2;
  d2 -> p4 [label="да"];
  p4 -> d1;
  d2 -> ret [label="нет"];
  d1 -> ret [label="нет"];
  ret -> stop;
""",
    ),
    "lexer_read_operator.puml": activity(
        "read_operator_Lexer",
        r"""
  start [label="Начало", shape=oval];
  p1 [label="raw = первый оператор\nиз списка", shape=box];
  d1 [label="raw существует?", shape=diamond];
  d2 [label="text.startswith(raw,\nself._position)?", shape=diamond];
  p2 [label="token_type, value = _OPERATORS[raw]", shape=box];
  p3 [label="token = Token(token_type,\nvalue, self._position)", shape=box];
  p4 [label="self._position += len(raw)", shape=box];
  ret1 [label="Возврат token", shape=parallelogram];
  p5 [label="raw = следующий оператор", shape=box];
  ret2 [label="Возврат None", shape=parallelogram];
  stop [label="Конец", shape=oval];

  start -> p1 -> d1;
  d1 -> d2 [label="да"];
  d2 -> p2 [label="да"];
  p2 -> p3 -> p4 -> ret1 -> stop;
  d2 -> p5 [label="нет"];
  p5 -> d1;
  d1 -> ret2 [label="нет"];
  ret2 -> stop;
""",
    ),
    "lexer_tokenize.puml": activity(
        "tokenize_Lexer",
        r"""
  start [label="Начало", shape=oval];
  d_empty [label="not self._text.strip()?", shape=diamond];
  err_empty [label="Ошибка LexerError:\nпустая строка", shape=parallelogram];
  p_tokens [label="tokens = []", shape=box];
  d_loop [label="self._position < self._length?", shape=diamond];
  p_current [label="current = self._text[self._position]", shape=box];
  d_space [label="current.isspace()?", shape=diamond];
  p_skip [label="self._position += 1", shape=box];
  p_op [label="operator_token = self._read_operator()", shape=box];
  d_op [label="operator_token is not None?", shape=diamond];
  p_add_op [label="tokens.append(operator_token)", shape=box];
  d_id [label="current.isalpha()?", shape=diamond];
  p_id [label="tokens.append(self._read_identifier())", shape=box];
  d_const [label="current in {'0', '1'}?", shape=diamond];
  p_const [label="Добавить Token(CONSTANT)\nself._position += 1", shape=box];
  d_and [label="current == '/'?", shape=diamond];
  err_and [label="Ошибка LexerError:\nоператор должен быть '/\\'", shape=parallelogram];
  d_or [label="current == '\\\\'?", shape=diamond];
  err_or [label="Ошибка LexerError:\nоператор должен быть '\\/'", shape=parallelogram];
  err_bad [label="Ошибка LexerError:\nнедопустимый символ", shape=parallelogram];
  p_eof [label="tokens.append(Token(EOF,\n'', self._length))", shape=box];
  ret [label="Возврат tokens", shape=parallelogram];
  stop [label="Конец", shape=oval];

  start -> d_empty;
  d_empty -> err_empty [label="да"];
  err_empty -> stop;
  d_empty -> p_tokens [label="нет"];
  p_tokens -> d_loop;
  d_loop -> p_current [label="да"];
  p_current -> d_space;
  d_space -> p_skip [label="да"];
  p_skip -> d_loop;
  d_space -> p_op [label="нет"];
  p_op -> d_op;
  d_op -> p_add_op [label="да"];
  p_add_op -> d_loop;
  d_op -> d_id [label="нет"];
  d_id -> p_id [label="да"];
  p_id -> d_loop;
  d_id -> d_const [label="нет"];
  d_const -> p_const [label="да"];
  p_const -> d_loop;
  d_const -> d_and [label="нет"];
  d_and -> err_and [label="да"];
  err_and -> stop;
  d_and -> d_or [label="нет"];
  d_or -> err_or [label="да"];
  err_or -> stop;
  d_or -> err_bad [label="нет"];
  err_bad -> stop;
  d_loop -> p_eof [label="нет"];
  p_eof -> ret -> stop;
""",
    ),
    "_parser_init.puml": activity(
        "_parser_init",
        """
  start [label="Начало", shape=oval];
  p1 [label="self._tokens = Lexer(text).tokenize()", shape=box];
  p2 [label="self._index = 0", shape=box];
  stop [label="Конец", shape=oval];

  start -> p1 -> p2 -> stop;
""",
    ),
    "_parser_current.puml": activity(
        "_current_Parser",
        """
  start [label="Начало", shape=oval];
  ret [label="Возврат self._tokens[self._index]", shape=parallelogram];
  stop [label="Конец", shape=oval];

  start -> ret -> stop;
""",
    ),
    "_parser_previous.puml": activity(
        "_previous_Parser",
        """
  start [label="Начало", shape=oval];
  ret [label="Возврат self._tokens[self._index - 1]", shape=parallelogram];
  stop [label="Конец", shape=oval];

  start -> ret -> stop;
""",
    ),
    "_parser_match.puml": activity(
        "_match_Parser",
        """
  start [label="Начало", shape=oval];
  d1 [label="self._current().token_type\n== token_type?", shape=diamond];
  p1 [label="self._index += 1", shape=box];
  ret_true [label="Возврат True", shape=parallelogram];
  ret_false [label="Возврат False", shape=parallelogram];
  stop [label="Конец", shape=oval];

  start -> d1;
  d1 -> p1 [label="да"];
  p1 -> ret_true -> stop;
  d1 -> ret_false [label="нет"];
  ret_false -> stop;
""",
    ),
    "parser_parse.puml": activity(
        "parse_Parser",
        r"""
  start [label="Начало", shape=oval];
  p1 [label="expression = self._parse_equivalence()", shape=box];
  p2 [label="current = self._current()", shape=box];
  d1 [label="current.token_type\n!= TokenType.EOF?", shape=diamond];
  err_tail [label="Ошибка ParserError:\nлишний хвост выражения", shape=parallelogram];
  d2 [label="expression - BinaryExpression\nи нет внешних скобок?", shape=diamond];
  err_wrap [label="Ошибка ParserError:\nнужны внешние скобки", shape=parallelogram];
  ret [label="Возврат expression", shape=parallelogram];
  stop [label="Конец", shape=oval];

  start -> p1 -> p2 -> d1;
  d1 -> err_tail [label="да"];
  err_tail -> stop;
  d1 -> d2 [label="нет"];
  d2 -> err_wrap [label="да"];
  err_wrap -> stop;
  d2 -> ret [label="нет"];
  ret -> stop;
""",
    ),
    "parser_parse_equivalence.puml": activity(
        "parse_equivalence_Parser",
        r"""
  start [label="Начало", shape=oval];
  p1 [label="expression = self._parse_implication()", shape=box];
  d1 [label="self._match(TokenType.EQUIV)?", shape=diamond];
  p2 [label="operator = self._previous()", shape=box];
  p3 [label="right = self._parse_implication()", shape=box];
  p4 [label="expression = BinaryExpression(\noperator.value, expression, right)", shape=box];
  ret [label="Возврат expression", shape=parallelogram];
  stop [label="Конец", shape=oval];

  start -> p1 -> d1;
  d1 -> p2 [label="да"];
  p2 -> p3 -> p4 -> d1;
  d1 -> ret [label="нет"];
  ret -> stop;
""",
    ),
    "parser_parse_implication.puml": activity(
        "parse_implication_Parser",
        r"""
  start [label="Начало", shape=oval];
  p1 [label="expression = self._parse_disjunction()", shape=box];
  d1 [label="self._match(TokenType.IMPLIES)?", shape=diamond];
  p2 [label="operator = self._previous()", shape=box];
  p3 [label="right = self._parse_implication()", shape=box];
  ret_bin [label="Возврат BinaryExpression(\noperator.value, expression, right)", shape=parallelogram];
  ret_expr [label="Возврат expression", shape=parallelogram];
  stop [label="Конец", shape=oval];

  start -> p1 -> d1;
  d1 -> p2 [label="да"];
  p2 -> p3 -> ret_bin -> stop;
  d1 -> ret_expr [label="нет"];
  ret_expr -> stop;
""",
    ),
    "parser_parse_disjunction.puml": activity(
        "parse_disjunction_Parser",
        r"""
  start [label="Начало", shape=oval];
  p1 [label="expression = self._parse_conjunction()", shape=box];
  d1 [label="self._match(TokenType.OR)?", shape=diamond];
  p2 [label="operator = self._previous()", shape=box];
  p3 [label="right = self._parse_conjunction()", shape=box];
  p4 [label="expression = BinaryExpression(\noperator.value, expression, right)", shape=box];
  ret [label="Возврат expression", shape=parallelogram];
  stop [label="Конец", shape=oval];

  start -> p1 -> d1;
  d1 -> p2 [label="да"];
  p2 -> p3 -> p4 -> d1;
  d1 -> ret [label="нет"];
  ret -> stop;
""",
    ),
    "parser_parse_conjunction.puml": activity(
        "parse_conjunction_Parser",
        r"""
  start [label="Начало", shape=oval];
  p1 [label="expression = self._parse_unary()", shape=box];
  d1 [label="self._match(TokenType.AND)?", shape=diamond];
  p2 [label="operator = self._previous()", shape=box];
  p3 [label="right = self._parse_unary()", shape=box];
  p4 [label="expression = BinaryExpression(\noperator.value, expression, right)", shape=box];
  ret [label="Возврат expression", shape=parallelogram];
  stop [label="Конец", shape=oval];

  start -> p1 -> d1;
  d1 -> p2 [label="да"];
  p2 -> p3 -> p4 -> d1;
  d1 -> ret [label="нет"];
  ret -> stop;
""",
    ),
    "parser_parse_unary.puml": activity(
        "parse_unary_Parser",
        r"""
  start [label="Начало", shape=oval];
  d1 [label="self._match(TokenType.NOT)?", shape=diamond];
  p1 [label="operator = self._previous()", shape=box];
  p2 [label="upcoming = self._current()", shape=box];
  d2 [label="upcoming - бинарный оператор,\n')' или EOF?", shape=diamond];
  err [label="Ошибка ParserError:\nнекорректное отрицание", shape=parallelogram];
  ret_unary [label="Возврат UnaryExpression(\noperator.value, self._parse_unary())", shape=parallelogram];
  ret_primary [label="Возврат self._parse_primary()", shape=parallelogram];
  stop [label="Конец", shape=oval];

  start -> d1;
  d1 -> p1 [label="да"];
  p1 -> p2 -> d2;
  d2 -> err [label="да"];
  err -> stop;
  d2 -> ret_unary [label="нет"];
  ret_unary -> stop;
  d1 -> ret_primary [label="нет"];
  ret_primary -> stop;
""",
    ),
    "parser_parse_primary.puml": activity(
        "parse_primary_Parser",
        r"""
  start [label="Начало", shape=oval];
  p0 [label="current = self._current()", shape=box];
  d_id [label="self._match(TokenType.IDENTIFIER)?", shape=diamond];
  ret_id [label="Возврат Identifier(\nself._previous().value)", shape=parallelogram];
  d_const [label="self._match(TokenType.CONSTANT)?", shape=diamond];
  ret_const [label="Возврат BooleanConstant(\nself._previous().value == '1')", shape=parallelogram];
  d_lparen [label="self._match(TokenType.LPAREN)?", shape=diamond];
  p_open [label="opening = self._previous()", shape=box];
  p_expr [label="expression = self._parse_equivalence()", shape=box];
  d_rparen_match [label="self._match(TokenType.RPAREN)?", shape=diamond];
  ret_expr [label="Возврат expression", shape=parallelogram];
  err_missing [label="Ошибка ParserError:\nне найдена закрывающая скобка", shape=parallelogram];
  d_rparen [label="current.token_type == RPAREN?", shape=diamond];
  err_extra [label="Ошибка ParserError:\nлишняя закрывающая скобка", shape=parallelogram];
  d_bin [label="current.token_type\nв _BINARY_TOKENS?", shape=diamond];
  err_operand [label="Ошибка ParserError:\nожидался операнд", shape=parallelogram];
  d_eof [label="current.token_type == EOF?", shape=diamond];
  err_eof [label="Ошибка ParserError:\nвыражение закончилось", shape=parallelogram];
  err_garbage [label="Ошибка ParserError:\nмусорный ввод", shape=parallelogram];
  stop [label="Конец", shape=oval];

  start -> p0 -> d_id;
  d_id -> ret_id [label="да"];
  ret_id -> stop;
  d_id -> d_const [label="нет"];
  d_const -> ret_const [label="да"];
  ret_const -> stop;
  d_const -> d_lparen [label="нет"];
  d_lparen -> p_open [label="да"];
  p_open -> p_expr -> d_rparen_match;
  d_rparen_match -> ret_expr [label="да"];
  ret_expr -> stop;
  d_rparen_match -> err_missing [label="нет"];
  err_missing -> stop;
  d_lparen -> d_rparen [label="нет"];
  d_rparen -> err_extra [label="да"];
  err_extra -> stop;
  d_rparen -> d_bin [label="нет"];
  d_bin -> err_operand [label="да"];
  err_operand -> stop;
  d_bin -> d_eof [label="нет"];
  d_eof -> err_eof [label="да"];
  err_eof -> stop;
  d_eof -> err_garbage [label="нет"];
  err_garbage -> stop;
""",
    ),
    "_parser_unexpected_after_expression.puml": activity(
        "_unexpected_after_expression_Parser",
        r"""
  start [label="Начало", shape=oval];
  d1 [label="token.token_type в\n{IDENTIFIER, CONSTANT,\nLPAREN, NOT}?", shape=diamond];
  ret_missing [label="Возврат ParserError:\nпропущен оператор", shape=parallelogram];
  d2 [label="token.token_type == RPAREN?", shape=diamond];
  ret_rparen [label="Возврат ParserError:\nлишняя закрывающая скобка", shape=parallelogram];
  ret_tail [label="Возврат ParserError:\nнекорректный хвост", shape=parallelogram];
  stop [label="Конец", shape=oval];

  start -> d1;
  d1 -> ret_missing [label="да"];
  ret_missing -> stop;
  d1 -> d2 [label="нет"];
  d2 -> ret_rparen [label="да"];
  ret_rparen -> stop;
  d2 -> ret_tail [label="нет"];
  ret_tail -> stop;
""",
    ),
    "_parse_formula.puml": activity(
        "_parse_formula_parser",
        """
  start [label="Начало", shape=oval];
  ret [label="Возврат Parser(text).parse()", shape=parallelogram];
  stop [label="Конец", shape=oval];

  start -> ret -> stop;
""",
    ),
    "_run_main.puml": activity(
        "_run_main",
        r"""
  start [label="Начало", shape=oval];
  p0 [label="Вывести заголовок программы", shape=parallelogram];
  p_menu [label="Вывести меню", shape=parallelogram];
  p_choice [label="choice = input(...).strip().lower()", shape=parallelogram];
  d_exit [label="choice в {'0', 'exit', ''}?", shape=diamond];
  out_exit [label="Вывести 'Завершение работы.'", shape=parallelogram];
  d_manual [label="choice == '1'?", shape=diamond];
  in_formula [label="raw_formula = input(...).strip()", shape=parallelogram];
  d_empty_formula [label="raw_formula пустая?", shape=diamond];
  err_empty_formula [label="Вывести ошибку:\nформула не введена", shape=parallelogram];
  call_manual [label="print_sknf_result(raw_formula)", shape=box];
  d_file [label="choice == '2'?", shape=diamond];
  in_path [label="file_path = input(...).strip()", shape=parallelogram];
  d_empty_path [label="file_path пустой?", shape=diamond];
  err_empty_path [label="Вывести ошибку:\nпуть не введен", shape=parallelogram];
  p_load [label="raw_formula = load_formula_from_file(file_path)", shape=box];
  d_read_error [label="ошибка чтения\nили пустой файл?", shape=diamond];
  err_read [label="Вывести ошибку", shape=parallelogram];
  out_formula [label="Вывести формулу", shape=parallelogram];
  call_file [label="print_sknf_result(raw_formula)", shape=box];
  err_choice [label="Вывести ошибку:\nвыберите 1, 2 или 0", shape=parallelogram];
  stop [label="Конец", shape=oval];

  start -> p0 -> p_menu -> p_choice -> d_exit;
  d_exit -> out_exit [label="да"];
  out_exit -> stop;
  d_exit -> d_manual [label="нет"];
  d_manual -> in_formula [label="да"];
  in_formula -> d_empty_formula;
  d_empty_formula -> err_empty_formula [label="да"];
  err_empty_formula -> p_menu;
  d_empty_formula -> call_manual [label="нет"];
  call_manual -> p_menu;
  d_manual -> d_file [label="нет"];
  d_file -> in_path [label="да"];
  in_path -> d_empty_path;
  d_empty_path -> err_empty_path [label="да"];
  err_empty_path -> p_menu;
  d_empty_path -> p_load [label="нет"];
  p_load -> d_read_error;
  d_read_error -> err_read [label="да"];
  err_read -> p_menu;
  d_read_error -> out_formula [label="нет"];
  out_formula -> call_file -> p_menu;
  d_file -> err_choice [label="нет"];
  err_choice -> p_menu;
""",
    ),
    "sknf_collect_conjunction_terms.puml": activity(
        "collect_conjunction_terms_sknf",
        r"""
  start [label="Начало", shape=oval];
  d1 [label="node - BinaryExpression\nи operator == '/\\'?", shape=diamond];
  ret_rec [label="Возврат collect(left)\n+ collect(right)", shape=parallelogram];
  ret_node [label="Возврат [node]", shape=parallelogram];
  stop [label="Конец", shape=oval];

  start -> d1;
  d1 -> ret_rec [label="да"];
  ret_rec -> stop;
  d1 -> ret_node [label="нет"];
  ret_node -> stop;
""",
    ),
    "sknf_collect_disjunction_terms.puml": activity(
        "collect_disjunction_terms_sknf",
        r"""
  start [label="Начало", shape=oval];
  d1 [label="node - BinaryExpression\nи operator == '\\/'?", shape=diamond];
  ret_rec [label="Возврат collect(left)\n+ collect(right)", shape=parallelogram];
  ret_node [label="Возврат [node]", shape=parallelogram];
  stop [label="Конец", shape=oval];

  start -> d1;
  d1 -> ret_rec [label="да"];
  ret_rec -> stop;
  d1 -> ret_node [label="нет"];
  ret_node -> stop;
""",
    ),
    "sknf_extract_clause_variables.puml": activity(
        "extract_clause_variables_sknf",
        r"""
  start [label="Начало", shape=oval];
  p1 [label="literals = _collect_disjunction_terms(node)", shape=box];
  p2 [label="variables = set()", shape=box];
  d_loop [label="есть следующий literal?", shape=diamond];
  p3 [label="variable_name = _literal_variable_name(literal)", shape=box];
  d_bad [label="variable_name is None\nили уже есть в variables?", shape=diamond];
  ret_none [label="Возврат None", shape=parallelogram];
  p_add [label="variables.add(variable_name)", shape=box];
  ret_vars [label="Возврат variables", shape=parallelogram];
  stop [label="Конец", shape=oval];

  start -> p1 -> p2 -> d_loop;
  d_loop -> p3 [label="да"];
  p3 -> d_bad;
  d_bad -> ret_none [label="да"];
  ret_none -> stop;
  d_bad -> p_add [label="нет"];
  p_add -> d_loop;
  d_loop -> ret_vars [label="нет"];
  ret_vars -> stop;
""",
    ),
    "sknf_is_sknf.puml": activity(
        "is_sknf_sknf",
        r"""
  start [label="Начало", shape=oval];
  p1 [label="clauses = _collect_conjunction_terms(node)", shape=box];
  d_empty [label="not clauses?", shape=diamond];
  ret_false_1 [label="Возврат False", shape=parallelogram];
  p_sets [label="clause_variable_sets = []", shape=box];
  d_loop [label="есть следующий clause?", shape=diamond];
  p_vars [label="variables = _extract_clause_variables(clause)", shape=box];
  d_bad [label="variables is None?", shape=diamond];
  ret_false_2 [label="Возврат False", shape=parallelogram];
  p_add [label="Добавить frozenset(variables)\nв clause_variable_sets", shape=box];
  p_ref [label="reference_variables =\nclause_variable_sets[0]", shape=box];
  ret_all [label="Возврат all(variables ==\nreference_variables)", shape=parallelogram];
  stop [label="Конец", shape=oval];

  start -> p1 -> d_empty;
  d_empty -> ret_false_1 [label="да"];
  ret_false_1 -> stop;
  d_empty -> p_sets [label="нет"];
  p_sets -> d_loop;
  d_loop -> p_vars [label="да"];
  p_vars -> d_bad;
  d_bad -> ret_false_2 [label="да"];
  ret_false_2 -> stop;
  d_bad -> p_add [label="нет"];
  p_add -> d_loop;
  d_loop -> p_ref [label="нет"];
  p_ref -> ret_all -> stop;
""",
    ),
    "sknf_literal_variable_name.puml": activity(
        "literal_variable_name_sknf",
        r"""
  start [label="Начало", shape=oval];
  d_id [label="node - Identifier?", shape=diamond];
  ret_name [label="Возврат node.name", shape=parallelogram];
  d_unary [label="node - UnaryExpression\nи operator == '!'?", shape=diamond];
  d_operand [label="node.operand - Identifier?", shape=diamond];
  ret_operand [label="Возврат node.operand.name", shape=parallelogram];
  ret_none_1 [label="Возврат None", shape=parallelogram];
  ret_none_2 [label="Возврат None", shape=parallelogram];
  stop [label="Конец", shape=oval];

  start -> d_id;
  d_id -> ret_name [label="да"];
  ret_name -> stop;
  d_id -> d_unary [label="нет"];
  d_unary -> d_operand [label="да"];
  d_operand -> ret_operand [label="да"];
  ret_operand -> stop;
  d_operand -> ret_none_1 [label="нет"];
  ret_none_1 -> stop;
  d_unary -> ret_none_2 [label="нет"];
  ret_none_2 -> stop;
""",
    ),
    "_class_diagram.puml": """@startuml _class_diagram
skinparam monochrome true
skinparam shadowing false
skinparam classAttributeIconSize 0
hide circle

class FormulaError
class LexerError
class ParserError

class TokenType {
  IDENTIFIER
  CONSTANT
  NOT
  AND
  OR
  IMPLIES
  EQUIV
  LPAREN
  RPAREN
  EOF
}

class Token {
  +token_type: TokenType
  +value: str
  +position: int
}

class Lexer {
  -_text: str
  -_length: int
  -_position: int
  +tokenize(): list[Token]
  -_read_operator(): Token | None
  -_read_identifier(): Token
}

abstract class Expression
class Identifier {
  +name: str
}
class BooleanConstant {
  +value: bool
}
class UnaryExpression {
  +operator: str
  +operand: Expression
}
class BinaryExpression {
  +operator: str
  +left: Expression
  +right: Expression
}

class Parser {
  -_tokens: list[Token]
  -_index: int
  +parse(): Expression
  -_parse_equivalence(): Expression
  -_parse_implication(): Expression
  -_parse_disjunction(): Expression
  -_parse_conjunction(): Expression
  -_parse_unary(): Expression
  -_parse_primary(): Expression
  -_unexpected_after_expression(token: Token): ParserError
  -_match(token_type: TokenType): bool
  -_current(): Token
  -_previous(): Token
  -_is_wrapped_by_outer_parentheses(): bool
}

FormulaError --|> ValueError
LexerError --|> FormulaError
ParserError --|> FormulaError

Identifier --|> Expression
BooleanConstant --|> Expression
UnaryExpression --|> Expression
BinaryExpression --|> Expression

Token --> TokenType
Lexer --> Token : создает
Lexer ..> LexerError : выбрасывает

Parser --> Lexer : использует
Parser --> Token : использует
Parser --> TokenType : использует
Parser ..> ParserError : выбрасывает
Parser ..> Identifier : создает
Parser ..> BooleanConstant : создает
Parser ..> UnaryExpression : создает
Parser ..> BinaryExpression : создает

UnaryExpression --> Expression
BinaryExpression --> Expression

@enduml
""",
}


FIGURES: list[tuple[str, str]] = [
    ("tokenize_Lexer.png", "Рис. 1. Метод tokenize класса Lexer"),
    ("read_operator_Lexer.png", "Рис. 2. Метод _read_operator класса Lexer"),
    ("read_identifier_Lexer.png", "Рис. 3. Метод _read_identifier класса Lexer"),
    ("parse_Parser.png", "Рис. 4. Метод parse класса Parser"),
    ("parse_equivalence_Parser.png", "Рис. 5. Метод _parse_equivalence класса Parser"),
    ("parse_implication_Parser.png", "Рис. 6. Метод _parse_implication класса Parser"),
    ("parse_disjunction_Parser.png", "Рис. 7. Метод _parse_disjunction класса Parser"),
    ("parse_conjunction_Parser.png", "Рис. 8. Метод _parse_conjunction класса Parser"),
    ("parse_unary_Parser.png", "Рис. 9. Метод _parse_unary класса Parser"),
    ("parse_primary_Parser.png", "Рис. 10. Метод _parse_primary класса Parser"),
    ("is_sknf_sknf.png", "Рис. 11. Функция is_sknf"),
    ("collect_conjunction_terms_sknf.png", "Рис. 12. Функция _collect_conjunction_terms"),
    ("collect_disjunction_terms_sknf.png", "Рис. 13. Функция _collect_disjunction_terms"),
    ("extract_clause_variables_sknf.png", "Рис. 14. Функция _extract_clause_variables"),
    ("literal_variable_name_sknf.png", "Рис. 15. Функция _literal_variable_name"),
]

NON_CORE_ITEMS: list[str] = [
    "_class_diagram.puml / _class_diagram.png - диаграмма структуры классов, не алгоритм функции",
    "_lexer_init.puml / _lexer_init.png - конструктор Lexer, только инициализирует поля объекта",
    "_parser_init.puml / _parser_init.png - конструктор Parser, только создает список токенов и индекс",
    "_parser_unexpected_after_expression.puml / _unexpected_after_expression_Parser.png - формирует текст ошибки",
    "_parser_match.puml / _match_Parser.png - служебное перемещение по токенам",
    "_parser_current.puml / _current_Parser.png - служебный доступ к текущему токену",
    "_parser_previous.puml / _previous_Parser.png - служебный доступ к предыдущему токену",
    "_parse_formula.puml / _parse_formula_parser.png - функция-обертка над Parser(text).parse()",
    "_run_main.puml / _run_main.png - пользовательский интерфейс и вызов других функций",
]

LEGACY_NON_CORE_FILES: list[tuple[Path, str, str]] = [
    (DIAGRAM_DIR, "class_diagram.puml", "_class_diagram.puml"),
    (DIAGRAM_DIR, "lexer_init.puml", "_lexer_init.puml"),
    (DIAGRAM_DIR, "parser_init.puml", "_parser_init.puml"),
    (DIAGRAM_DIR, "parser_unexpected_after_expression.puml", "_parser_unexpected_after_expression.puml"),
    (DIAGRAM_DIR, "parser_match.puml", "_parser_match.puml"),
    (DIAGRAM_DIR, "parser_current.puml", "_parser_current.puml"),
    (DIAGRAM_DIR, "parser_previous.puml", "_parser_previous.puml"),
    (DIAGRAM_DIR, "parse_formula.puml", "_parse_formula.puml"),
    (DIAGRAM_DIR, "run_main.puml", "_run_main.puml"),
    (PNG_DIR, "class_diagram.png", "_class_diagram.png"),
    (PNG_DIR, "lexer_init.png", "_lexer_init.png"),
    (PNG_DIR, "parser_init.png", "_parser_init.png"),
    (PNG_DIR, "unexpected_after_expression_Parser.png", "_unexpected_after_expression_Parser.png"),
    (PNG_DIR, "match_Parser.png", "_match_Parser.png"),
    (PNG_DIR, "current_Parser.png", "_current_Parser.png"),
    (PNG_DIR, "previous_Parser.png", "_previous_Parser.png"),
    (PNG_DIR, "parse_formula_parser.png", "_parse_formula_parser.png"),
    (PNG_DIR, "run_main.png", "_run_main.png"),
]


def write_sources() -> None:
    for directory, legacy_name, marked_name in LEGACY_NON_CORE_FILES:
        legacy_path = directory / legacy_name
        marked_path = directory / marked_name
        if legacy_path.exists() and not marked_path.exists():
            legacy_path.rename(marked_path)
        elif legacy_path.exists():
            legacy_path.unlink()

    for name, content in PUML.items():
        (DIAGRAM_DIR / name).write_text(content, encoding="utf-8")


def write_html() -> None:
    figures_html = []
    for image_name, caption in FIGURES:
        figures_html.append(
            f"""<figure>
  <img src="png/{image_name}" alt="{caption}">
  <figcaption>{caption}</figcaption>
</figure>"""
        )
    non_core_html = "".join(f"<li>{escape(item)}</li>" for item in NON_CORE_ITEMS)

    html = f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <title>Основные схемы функций программы</title>
  <style>
    @page {{ size: A4; margin: 2cm 1.5cm 2cm 2cm; }}
    body {{ font-family: "Times New Roman", serif; font-size: 14pt; line-height: 1.2; }}
    h1, h2 {{ text-align: center; font-size: 16pt; margin: 0 0 18pt; }}
    figure {{ text-align: center; margin: 0 0 18pt; page-break-inside: avoid; }}
    img {{ max-width: 17cm; max-height: 23cm; width: auto; height: auto; }}
    figcaption {{ font-size: 12pt; margin-top: 6pt; }}
    li {{ margin-bottom: 6pt; }}
  </style>
</head>
<body>
  <h1>Основные схемы функций программы</h1>
  {''.join(figures_html)}
  <h2>Неосновные функции и элементы</h2>
  <ul>{non_core_html}</ul>
</body>
</html>
"""
    (DIAGRAM_DIR / "gost_block_schemes.html").write_text(html, encoding="utf-8")


def paragraph(text: str, *, align: str = "both", bold: bool = False, size: int = 28) -> str:
    jc = f'<w:jc w:val="{align}"/>' if align else ""
    bold_tag = "<w:b/>" if bold else ""
    return f"""<w:p>
  <w:pPr>{jc}</w:pPr>
  <w:r>
    <w:rPr>
      <w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:cs="Times New Roman"/>
      {bold_tag}
      <w:sz w:val="{size}"/><w:szCs w:val="{size}"/>
    </w:rPr>
    <w:t>{escape(text)}</w:t>
  </w:r>
</w:p>"""


def image_paragraph(rel_id: str, doc_pr_id: int, filename: str) -> str:
    max_width_in = 6.4
    max_height_in = 9.0
    min_width_in = 3.5
    emu_per_inch = 914_400

    with Image.open(PNG_DIR / filename) as image:
        width_px, height_px = image.size

    width_in = max(min_width_in, width_px / 170)
    height_in = width_in * height_px / width_px
    if width_in > max_width_in:
        width_in = max_width_in
        height_in = width_in * height_px / width_px
    if height_in > max_height_in:
        height_in = max_height_in
        width_in = height_in * width_px / height_px

    cx = int(width_in * emu_per_inch)
    cy = int(height_in * emu_per_inch)

    return f"""<w:p>
  <w:pPr><w:jc w:val="center"/></w:pPr>
  <w:r>
    <w:drawing>
      <wp:inline distT="0" distB="0" distL="0" distR="0">
        <wp:extent cx="{cx}" cy="{cy}"/>
        <wp:docPr id="{doc_pr_id}" name="{escape(filename)}"/>
        <wp:cNvGraphicFramePr>
          <a:graphicFrameLocks noChangeAspect="1"/>
        </wp:cNvGraphicFramePr>
        <a:graphic>
          <a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">
            <pic:pic>
              <pic:nvPicPr>
                <pic:cNvPr id="{doc_pr_id}" name="{escape(filename)}"/>
                <pic:cNvPicPr/>
              </pic:nvPicPr>
              <pic:blipFill>
                <a:blip r:embed="{rel_id}"/>
                <a:stretch><a:fillRect/></a:stretch>
              </pic:blipFill>
              <pic:spPr>
                <a:xfrm>
                  <a:off x="0" y="0"/>
                  <a:ext cx="{cx}" cy="{cy}"/>
                </a:xfrm>
                <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
              </pic:spPr>
            </pic:pic>
          </a:graphicData>
        </a:graphic>
      </wp:inline>
    </w:drawing>
  </w:r>
</w:p>"""


def write_docx() -> None:
    document_parts = [
        paragraph("Основные схемы функций программы", align="center", bold=True, size=32)
    ]
    rel_items = []
    content_type_overrides = []
    media_files: list[tuple[Path, str]] = []

    for index, (image_name, caption) in enumerate(FIGURES, start=1):
        rel_id = f"rId{index}"
        target = f"media/image{index}.png"
        rel_items.append(
            f'<Relationship Id="{rel_id}" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" '
            f'Target="{target}"/>'
        )
        media_files.append((PNG_DIR / image_name, f"word/{target}"))
        document_parts.append(image_paragraph(rel_id, index, image_name))
        document_parts.append(paragraph(caption, align="center", size=24))
        if index != len(FIGURES):
            document_parts.append("<w:p/>")
    document_parts.append(paragraph("Неосновные функции и элементы", align="center", bold=True, size=32))
    for item in NON_CORE_ITEMS:
        document_parts.append(paragraph(item, align="both", size=28))

    document_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document
  xmlns:wpc="http://schemas.microsoft.com/office/word/2010/wordprocessingCanvas"
  xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006"
  xmlns:o="urn:schemas-microsoft-com:office:office"
  xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
  xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math"
  xmlns:v="urn:schemas-microsoft-com:vml"
  xmlns:wp14="http://schemas.microsoft.com/office/word/2010/wordprocessingDrawing"
  xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
  xmlns:w10="urn:schemas-microsoft-com:office:word"
  xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
  xmlns:w14="http://schemas.microsoft.com/office/word/2010/wordml"
  xmlns:wpg="http://schemas.microsoft.com/office/word/2010/wordprocessingGroup"
  xmlns:wpi="http://schemas.microsoft.com/office/word/2010/wordprocessingInk"
  xmlns:wne="http://schemas.microsoft.com/office/word/2006/wordml"
  xmlns:wps="http://schemas.microsoft.com/office/word/2010/wordprocessingShape"
  xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
  xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"
  mc:Ignorable="w14 wp14">
  <w:body>
    {''.join(document_parts)}
    <w:sectPr>
      <w:pgSz w:w="11906" w:h="16838"/>
      <w:pgMar w:top="1134" w:right="850" w:bottom="1134" w:left="1134" w:header="708" w:footer="708" w:gutter="0"/>
      <w:cols w:space="708"/>
      <w:docGrid w:linePitch="360"/>
    </w:sectPr>
  </w:body>
</w:document>"""

    content_types = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Default Extension="png" ContentType="image/png"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
  {''.join(content_type_overrides)}
</Types>"""

    root_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>"""

    document_rels = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  {''.join(rel_items)}
</Relationships>"""

    now = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    core = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
  xmlns:dc="http://purl.org/dc/elements/1.1/"
  xmlns:dcterms="http://purl.org/dc/terms/"
  xmlns:dcmitype="http://purl.org/dc/dcmitype/"
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:title>Основные схемы функций программы</dc:title>
  <dc:creator>Codex</dc:creator>
  <cp:lastModifiedBy>Codex</cp:lastModifiedBy>
  <dcterms:created xsi:type="dcterms:W3CDTF">{now}</dcterms:created>
  <dcterms:modified xsi:type="dcterms:W3CDTF">{now}</dcterms:modified>
</cp:coreProperties>"""

    app = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"
  xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
  <Application>Codex</Application>
</Properties>"""

    docx_path = DIAGRAM_DIR / "gost_block_schemes.docx"
    with ZipFile(docx_path, "w", compression=ZIP_DEFLATED) as docx:
        docx.writestr("[Content_Types].xml", content_types)
        docx.writestr("_rels/.rels", root_rels)
        docx.writestr("word/document.xml", document_xml)
        docx.writestr("word/_rels/document.xml.rels", document_rels)
        docx.writestr("docProps/core.xml", core)
        docx.writestr("docProps/app.xml", app)
        for source, target in media_files:
            docx.write(source, target)


if __name__ == "__main__":
    write_sources()
    write_html()
    if all((PNG_DIR / image_name).exists() for image_name, _ in FIGURES):
        write_docx()

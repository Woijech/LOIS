from __future__ import annotations

from pathlib import Path

from logic_parser import FormulaError, is_sknf, parse_formula


def load_formula_from_file(file_path: str) -> str:
    """Считывает формулу из текстового файла."""

    formula = Path(file_path).read_text(encoding="utf-8").strip()
    if not formula:
        raise ValueError("Файл с формулой пуст.")
    return formula


def print_sknf_result(raw_formula: str) -> None:
    """Разбирает формулу и выводит результат проверки СКНФ."""

    try:
        tree = parse_formula(raw_formula)
    except FormulaError as error:
        print(f"Ошибка: {error}")
        return

    print(f"СКНФ: {'да' if is_sknf(tree) else 'нет'}")


def main() -> None:
    print("Парсер логических формул.")

    while True:
        print("\n1. Ввести формулу вручную")
        print("2. Загрузить формулу из файла")
        print("0. Выход")

        choice = input("Выберите пункт: ").strip().lower()
        if choice in {"0", "exit", ""}:
            print("Завершение работы.")
            break

        if choice == "1":
            raw_formula = input("Введите формулу: ").strip()
            if not raw_formula:
                print("Ошибка: формула не введена.")
                continue
            print_sknf_result(raw_formula)
            continue

        if choice == "2":
            file_path = input("Введите путь к файлу: ").strip()
            if not file_path:
                print("Ошибка: путь к файлу не введён.")
                continue

            try:
                raw_formula = load_formula_from_file(file_path)
            except OSError as error:
                print(f"Ошибка чтения файла: {error}")
                continue
            except ValueError as error:
                print(f"Ошибка: {error}")
                continue

            print(f"Формула: {raw_formula}")
            print_sknf_result(raw_formula)
            continue

        print("Ошибка: выберите пункт 1, 2 или 0.")


if __name__ == "__main__":
    main()

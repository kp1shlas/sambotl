"""Generate a sample participants spreadsheet for testing the importer.

Run:  python scripts/make_sample_excel.py
Output: data/samples/participants_sample.xlsx
"""
from pathlib import Path

from openpyxl import Workbook

HEADERS = [
    "Фамилия",
    "Имя",
    "Отчество",
    "Пол",
    "Дата рождения",
    "Клуб",
    "Регион",
    "Тренер",
    "Категория",
    "Заявленный вес",
    "Текущий вес",
]

ROWS = [
    ["Иванов", "Пётр", "Сергеевич", "М", "12.05.1998", "Самбо-70", "Москва", "Кузнецов А.А.", "до 71", 70.5, 70.8],
    ["Петров", "Алексей", "Иванович", "М", "03.11.1996", "Динамо", "Москва", "Смирнов В.В.", "до 79", 78.0, 79.0],
    ["Сидоров", "Николай", "Петрович", "М", "21.02.2000", "Самбо-70", "Москва", "Кузнецов А.А.", "", 88.4, 88.4],
    ["Кузнецова", "Анна", "Дмитриевна", "Ж", "17.07.1999", "Юность", "Тула", "Орлов Д.Д.", "до 59", 58.0, 58.2],
    ["Морозов", "Дмитрий", "Андреевич", "М", "09.09.1994", "Родина", "Пермь", "Белов И.И.", "до 98", 96.0, 99.1],
    ["Волкова", "Мария", "Сергеевна", "Ж", "30.01.2001", "Юность", "Тула", "Орлов Д.Д.", "", 71.0, 71.0],
]


def main() -> None:
    target_dir = Path(__file__).resolve().parent.parent / "data" / "samples"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / "participants_sample.xlsx"

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Участники"
    sheet.append(HEADERS)
    for row in ROWS:
        sheet.append(row)
    workbook.save(target)
    print(f"Создан пример: {target}")


if __name__ == "__main__":
    main()

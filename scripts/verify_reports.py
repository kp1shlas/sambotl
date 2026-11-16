"""Verify generated report files are valid and contain expected data."""
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

from docx import Document  # noqa: E402
from openpyxl import load_workbook  # noqa: E402

target = BASE_DIR / "data" / "reports"

# Excel — weigh-in protocol
wb = load_workbook(target / "weighing.xlsx")
ws = wb.active
print("weighing.xlsx:")
print("  заголовки:", [c.value for c in ws[1]])
print("  строк данных:", ws.max_row - 1)

# Excel — bracket
wb2 = load_workbook(target / "bracket.xlsx")
ws2 = wb2.active
print("bracket.xlsx:")
print("  заголовки:", [c.value for c in ws2[1]])

# Word — results
doc = Document(target / "results.docx")
headings = [p.text for p in doc.paragraphs if p.style.name.startswith("Heading") or p.style.name == "Title"]
print("results.docx:")
print("  заголовки:", headings[:5])
print("  абзацев:", len(doc.paragraphs))

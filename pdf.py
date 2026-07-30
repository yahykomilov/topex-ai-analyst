"""Генерация PDF с полным текстом разговора и ТЗ для сотрудника."""

import re
from pathlib import Path

from fpdf import FPDF
from fpdf.enums import XPos, YPos

FONT = "C:/Windows/Fonts/arial.ttf"
FONT_BOLD = "C:/Windows/Fonts/arialbd.ttf"

_CELL_KW = {"new_x": XPos.LMARGIN, "new_y": YPos.NEXT}


def _clean(text: str) -> str:
    """Убираем эмодзи и символы, которых нет в шрифте."""
    text = re.sub(r"[\U00010000-\U0010FFFF]", "", text)  # эмодзи и прочее вне BMP
    text = re.sub(r"[\u2600-\u27BF\uFE0F\u200D]", "", text)  # значки, селекторы
    return text


def make_call_pdf(dest: Path, title: str, meta_lines: list[str], body: str) -> Path:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.add_font("ArialU", "", FONT)
    pdf.add_font("ArialU", "B", FONT_BOLD)

    pdf.set_font("ArialU", "B", 14)
    pdf.multi_cell(0, 8, _clean(title), **_CELL_KW)
    pdf.ln(1)

    pdf.set_font("ArialU", "", 10)
    pdf.set_text_color(90, 90, 90)
    for line in meta_lines:
        pdf.multi_cell(0, 5.5, _clean(line), **_CELL_KW)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(4)

    pdf.set_font("ArialU", "", 11)
    for paragraph in _clean(body).split("\n"):
        if not paragraph.strip():
            pdf.ln(3)
            continue
        # заголовки секций — жирным
        if paragraph.strip().rstrip(":").isupper() and len(paragraph) < 60:
            pdf.set_font("ArialU", "B", 11)
            pdf.multi_cell(0, 6, paragraph.strip(), **_CELL_KW)
            pdf.set_font("ArialU", "", 11)
        else:
            pdf.multi_cell(0, 6, paragraph, **_CELL_KW)
    pdf.output(str(dest))
    return dest

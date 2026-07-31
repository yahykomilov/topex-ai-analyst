"""Генерация PDF с полным текстом разговора и ТЗ для сотрудника."""

import re
from pathlib import Path

from fpdf import FPDF
from fpdf.enums import XPos, YPos

# Шрифт с поддержкой кириллицы И узбекской латиницы (ʻ, ʼ и т.п.).
# Ищем по кандидатам: Windows (локально) → Linux DejaVu/Liberation (сервер) → macOS.
# Так PDF работает и на ПК при разработке, и на VPS после деплоя — без правок кода.
_FONT_CANDIDATES = [
    ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"),
    (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ),
    (
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ),
    ("/Library/Fonts/Arial.ttf", "/Library/Fonts/Arial Bold.ttf"),
    ("/System/Library/Fonts/Supplemental/Arial.ttf", "/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
]


def _resolve_fonts() -> tuple[str, str]:
    """Возвращает (обычный, жирный) первый найденный шрифт.

    Если жирного нет — используем обычный и для жирного. Если не найдено ничего —
    понятная ошибка (на сервере ставится: apt install fonts-dejavu-core).
    """
    for regular, bold in _FONT_CANDIDATES:
        if Path(regular).exists():
            return regular, (bold if Path(bold).exists() else regular)
    raise RuntimeError(
        "Не найден TTF-шрифт с поддержкой кириллицы/узбекского. "
        "На сервере установите: apt-get install -y fonts-dejavu-core"
    )


_CELL_KW = {"new_x": XPos.LMARGIN, "new_y": YPos.NEXT}


def _clean(text: str) -> str:
    """Убираем эмодзи и символы, которых нет в шрифте."""
    text = re.sub(r"[\U00010000-\U0010FFFF]", "", text)  # эмодзи и прочее вне BMP
    text = re.sub(r"[\u2190-\u21FF\u2300-\u23FF\u2600-\u27BF\u2B00-\u2BFF\uFE0F\u200D\u20E3]", "", text)  # значки/стрелки/технические + селекторы
    return text


def make_call_pdf(dest: Path, title: str, meta_lines: list[str], body: str) -> Path:
    font_regular, font_bold = _resolve_fonts()
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.add_font("ArialU", "", font_regular)
    pdf.add_font("ArialU", "B", font_bold)

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

"""Генерация PDF с полным текстом разговора и ТЗ для сотрудника."""

import platform
from functools import lru_cache
from pathlib import Path

from fontTools.ttLib import TTFont
from fpdf import FPDF
from fpdf.enums import XPos, YPos

# Шрифт нужен с кириллицей и узбекской латиницей (ў, ғ, ҳ / oʻ, gʻ).
# DejaVu лежит в репозитории — одинаковый результат на Windows, macOS и Ubuntu VPS.
_BUNDLED_FONTS = Path(__file__).parent / "assets" / "fonts"

_SYSTEM_FONTS = {
    "Windows": ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"),
    "Darwin": (
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    ),
    "Linux": (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ),
}

_CELL_KW = {"new_x": XPos.LMARGIN, "new_y": YPos.NEXT}


def font_paths() -> tuple[str, str]:
    """Пути к обычному и жирному начертанию: сначала свой шрифт, потом системный."""
    candidates = [
        (_BUNDLED_FONTS / "DejaVuSans.ttf", _BUNDLED_FONTS / "DejaVuSans-Bold.ttf")
    ]
    system = _SYSTEM_FONTS.get(platform.system())
    if system:
        candidates.append(system)

    for regular, bold in candidates:
        if Path(regular).is_file() and Path(bold).is_file():
            return str(regular), str(bold)

    raise FileNotFoundError(
        f"Шрифт для PDF не найден. Положите DejaVuSans.ttf и DejaVuSans-Bold.ttf "
        f"в {_BUNDLED_FONTS}"
    )


@lru_cache(maxsize=8)
def _glyphs(*font_files: str) -> frozenset[int]:
    """Коды символов, которые есть сразу во всех начертаниях шрифта."""
    sets = []
    for path in font_files:
        font = TTFont(path, fontNumber=0, lazy=True)
        sets.append(set(font.getBestCmap()))
        font.close()
    return frozenset(set.intersection(*sets))


def _clean(text: str, glyphs: frozenset[int]) -> str:
    """Выкидываем эмодзи и всё, чего нет в шрифте — иначе в PDF пустые квадраты."""
    return "".join(ch for ch in text if ch == "\n" or ord(ch) in glyphs)


def make_call_pdf(dest: Path, title: str, meta_lines: list[str], body: str) -> Path:
    regular, bold = font_paths()
    glyphs = _glyphs(regular, bold)

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.add_font("ArialU", "", regular)
    pdf.add_font("ArialU", "B", bold)

    pdf.set_font("ArialU", "B", 14)
    pdf.multi_cell(0, 8, _clean(title, glyphs), **_CELL_KW)
    pdf.ln(1)

    pdf.set_font("ArialU", "", 10)
    pdf.set_text_color(90, 90, 90)
    for line in meta_lines:
        pdf.multi_cell(0, 5.5, _clean(line, glyphs), **_CELL_KW)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(4)

    pdf.set_font("ArialU", "", 11)
    for paragraph in _clean(body, glyphs).split("\n"):
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

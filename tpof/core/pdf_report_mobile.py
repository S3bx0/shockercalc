"""Lekki generator PDF dla wersji mobilnej (Android), oparty na fpdf2.

`reportlab` nie kompiluje się pod python-for-android (rozszerzenia C),
dlatego na telefonie budujemy PDF czysto-pythonowym `fpdf2`.
Zwraca bajty PDF, tak jak desktopowy `pdf_report.build_pdf`.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from .formatters import format_results_text
from .models import FreezingResults


def build_pdf_simple(
    results: FreezingResults, font_path: Path | None = None
) -> bytes:
    """Buduje prosty raport PDF z wynikami i zwraca jego bajty."""
    from fpdf import FPDF

    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    font_name = "Helvetica"
    unicode_font = False
    if font_path is not None and Path(font_path).exists():
        try:
            pdf.add_font("DejaVu", "", str(font_path))
            font_name = "DejaVu"
            unicode_font = True
        except Exception:
            font_name = "Helvetica"

    def _txt(value: str) -> str:
        # Czcionki rdzeniowe (Helvetica) obsługują tylko latin-1.
        if unicode_font:
            return value
        return value.encode("latin-1", "replace").decode("latin-1")

    pdf.set_font(font_name, size=16)
    pdf.multi_cell(0, 10, _txt("Refrigeration Calc"), align="C",
                   new_x="LMARGIN", new_y="NEXT")

    pdf.set_font(font_name, size=9)
    pdf.multi_cell(0, 6, _txt(datetime.now().strftime("%Y-%m-%d %H:%M")),
                   align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    pdf.set_font(font_name, size=11)
    body = format_results_text(results, include_product_properties=False)
    for line in body.splitlines():
        pdf.multi_cell(0, 7, _txt(line), new_x="LMARGIN", new_y="NEXT")

    return bytes(pdf.output())

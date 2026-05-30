"""Generator PDF — niezależny od warstwy UI.

Zwraca bajty PDF zamiast pisać do pliku — desktop zapisuje je przez `filedialog`,
warstwa mobilna (Kivy/Android) przez Storage Access Framework.
"""

from __future__ import annotations

import logging
import tempfile
from io import BytesIO
from pathlib import Path
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.colors import black, grey, lightgrey
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm, inch
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.platypus import (
    Image as RImage,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

try:
    from pypdf import PdfReader, PdfWriter
except ImportError:  # fallback dla starszych instalacji
    from PyPDF2 import PdfReader, PdfWriter  # type: ignore

from .formatters import format_results_text
from .models import FreezingResults

log = logging.getLogger(__name__)

DEFAULT_FONT_NAME = "DejaVuSans"
_FONT_REGISTERED = False


def register_font(font_path: Path, font_name: str = DEFAULT_FONT_NAME) -> str:
    """Rejestruje czcionkę TTF (idempotentnie). Zwraca nazwę czcionki."""
    global _FONT_REGISTERED
    if not _FONT_REGISTERED:
        pdfmetrics.registerFont(TTFont(font_name, str(font_path)))
        _FONT_REGISTERED = True
    return font_name


def _build_base_pdf(
    results: FreezingResults,
    font_name: str,
    product_image_path: Optional[Path],
    author_text: str,
) -> bytes:
    """Buduje główny PDF (bez watermark/hasła) i zwraca jego bajty."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=0.5 * inch,
        rightMargin=0.5 * inch,
        topMargin=0.5 * inch,
        bottomMargin=0.5 * inch,
    )

    title_style = ParagraphStyle(
        name="TitleStyle", fontName=font_name, fontSize=16, alignment=TA_CENTER
    )
    author_style = ParagraphStyle(
        name="AuthorStyle",
        fontName=font_name,
        fontSize=10,
        leading=12,
        alignment=TA_CENTER,
        textColor=black,
        spaceAfter=12,
    )

    story = [
        Paragraph("Wyniki obliczeń zamrażania", title_style),
        Spacer(1, 36),
    ]

    # Tabela wyników na podstawie sformatowanego tekstu (jeden source of truth).
    text = format_results_text(results)
    data_rows = []
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        parts = line.split(": ", 1)
        if len(parts) == 2:
            data_rows.append(parts)
        else:
            data_rows.append([line, ""])

    table = Table(data_rows, colWidths=[7 * cm, 9 * cm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), lightgrey),
                ("TEXTCOLOR", (0, 0), (-1, 0), black),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("FONTNAME", (0, 0), (-1, -1), font_name),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("GRID", (0, 0), (-1, -1), 0.5, grey),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 18))

    if product_image_path and product_image_path.exists():
        try:
            story.append(RImage(str(product_image_path), width=2.5 * inch, height=2.5 * inch))
            story.append(Spacer(1, 6))
        except Exception as e:  # noqa: BLE001
            log.warning("Nie udało się dołączyć zdjęcia produktu: %s", e)

    story.append(Paragraph(author_text.replace("\n", "<br/>"), author_style))

    doc.build(story)
    return buffer.getvalue()


def _apply_watermark(pdf_bytes: bytes, watermark_image: Path) -> bytes:
    """Nakłada obraz znaku wodnego na każdą stronę PDF."""
    if not watermark_image.exists():
        log.warning("Brak pliku znaku wodnego: %s — pomijam.", watermark_image)
        return pdf_bytes

    # Generujemy stronę watermark
    wm_buffer = BytesIO()
    c = rl_canvas.Canvas(wm_buffer, pagesize=A4)
    try:
        watermark_img = ImageReader(str(watermark_image))
        page_w, page_h = A4
        img_w, img_h = watermark_img.getSize()
        scale = min(page_w / img_w, page_h / img_h, 1.0)
        img_w *= scale
        img_h *= scale
        x = (page_w - img_w) / 2
        y = (page_h - img_h) / 2
        c.saveState()
        try:
            c.setFillAlpha(0.18)
        except Exception:  # noqa: BLE001
            pass  # starsze wersje reportlab
        c.drawImage(watermark_img, x, y, width=img_w, height=img_h, mask="auto")
        c.restoreState()
    except Exception as e:  # noqa: BLE001
        log.warning("Błąd generowania watermark: %s", e)
        return pdf_bytes
    c.save()
    wm_buffer.seek(0)

    reader = PdfReader(BytesIO(pdf_bytes))
    watermark_reader = PdfReader(wm_buffer)
    writer = PdfWriter()
    for page in reader.pages:
        page.merge_page(watermark_reader.pages[0])
        writer.add_page(page)

    out = BytesIO()
    writer.write(out)
    return out.getvalue()


def _encrypt(pdf_bytes: bytes, owner_password: str) -> bytes:
    """Szyfruje PDF — puste user_password = otwiera się bez hasła,
    owner_password chroni przed edycją (działa tylko gdy reader respektuje uprawnienia)."""
    if not owner_password:
        return pdf_bytes
    reader = PdfReader(BytesIO(pdf_bytes))
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    try:
        writer.encrypt(
            user_password="",
            owner_password=owner_password,
            use_128bit=True,
        )
    except TypeError:
        # pypdf nowe API
        writer.encrypt(owner_password, user_password="")
    out = BytesIO()
    writer.write(out)
    return out.getvalue()


def build_pdf(
    results: FreezingResults,
    font_path: Path,
    product_image_path: Optional[Path] = None,
    watermark_image_path: Optional[Path] = None,
    author_text: str = "Autor:\nSebastian Milczarek\nMD-Puch Sp. z o.o.",
    owner_password: Optional[str] = None,
) -> bytes:
    """Generuje gotowe bajty PDF.

    Wywołanie jest synchroniczne i nie dotyka systemu plików (poza czytaniem
    grafik i czcionek). Dzięki temu może być uruchomione również na Androidzie.
    """
    font_name = register_font(font_path)
    pdf = _build_base_pdf(results, font_name, product_image_path, author_text)
    if watermark_image_path:
        pdf = _apply_watermark(pdf, watermark_image_path)
    if owner_password:
        pdf = _encrypt(pdf, owner_password)
    return pdf


def save_pdf(pdf_bytes: bytes, output_path: Path) -> None:
    """Zapisuje bajty PDF do pliku (atomowo przez plik tymczasowy)."""
    output_path = Path(output_path)
    with tempfile.NamedTemporaryFile(
        delete=False, suffix=".pdf", dir=str(output_path.parent)
    ) as tmp:
        tmp.write(pdf_bytes)
        tmp_path = Path(tmp.name)
    tmp_path.replace(output_path)

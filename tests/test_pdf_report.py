from io import BytesIO
from pathlib import Path

import pytest
from pypdf import PdfReader

from tpof.core import pdf_report
from tpof.core.calculations import calculate_freezing
from tpof.core.models import FreezingInputs, Product


def test_legacy_pdf_encryption_uses_user_password_before_owner(monkeypatch):
    writers = []

    class LegacyReader:
        def __init__(self, _stream: BytesIO):
            self.pages = [object()]

    class LegacyWriter:
        def __init__(self):
            self.passwords = None
            writers.append(self)

        def add_page(self, _page):
            return None

        def encrypt(self, *args, **kwargs):
            if kwargs:
                raise TypeError("legacy positional API")
            self.passwords = args

        def write(self, stream: BytesIO):
            stream.write(b"encrypted-pdf")

    monkeypatch.setattr(pdf_report, "PdfReader", LegacyReader)
    monkeypatch.setattr(pdf_report, "PdfWriter", LegacyWriter)

    result = pdf_report._encrypt(b"source-pdf", "owner-secret")

    assert result == b"encrypted-pdf"
    assert writers[0].passwords == ("", "owner-secret")


def test_legacy_named_pdf_encryption_uses_old_keyword_names(monkeypatch):
    writers = []

    class LegacyReader:
        def __init__(self, _stream: BytesIO):
            self.pages = [object()]

    class LegacyNamedWriter:
        def __init__(self):
            self.passwords = None
            writers.append(self)

        def add_page(self, _page):
            return None

        def encrypt(self, user_pwd, owner_pwd=None, use_128bit=True):
            self.passwords = (user_pwd, owner_pwd, use_128bit)

        def write(self, stream: BytesIO):
            stream.write(b"encrypted-pdf")

    monkeypatch.setattr(pdf_report, "PdfReader", LegacyReader)
    monkeypatch.setattr(pdf_report, "PdfWriter", LegacyNamedWriter)

    result = pdf_report._encrypt(b"source-pdf", "owner-secret")

    assert result == b"encrypted-pdf"
    assert writers[0].passwords == ("", "owner-secret", True)


def test_modern_pdf_encryption_does_not_mask_internal_type_error(monkeypatch):
    class ModernReader:
        def __init__(self, _stream: BytesIO):
            self.pages = [object()]

    class BrokenModernWriter:
        def add_page(self, _page):
            return None

        def encrypt(self, user_password, owner_password=None, use_128bit=True):
            raise TypeError("internal encryption failure")

    monkeypatch.setattr(pdf_report, "PdfReader", ModernReader)
    monkeypatch.setattr(pdf_report, "PdfWriter", BrokenModernWriter)

    import pytest

    with pytest.raises(TypeError, match="internal encryption failure"):
        pdf_report._encrypt(b"source-pdf", "owner-secret")


@pytest.mark.parametrize("with_watermark", [False, True])
@pytest.mark.parametrize("owner_password", [None, "test-owner-password"])
def test_real_pdf_generation_watermark_and_owner_password(with_watermark, owner_password):
    """Compatibility control with real ReportLab/pypdf, not a mocked writer."""
    root = Path(__file__).resolve().parents[1]
    results = calculate_freezing(
        FreezingInputs(masa_kg=100, T_pocz_C=5, T_konc_C=-18, czas_h=24),
        Product(nazwa="Wiśnie", c1=3.4, c2=2.2, T_zam=-2, L1=223),
    )
    data = pdf_report.build_pdf(
        results,
        root / "assets/fonts/DejaVuSans.ttf",
        product_image_path=root / "assets/icon.png",
        watermark_image_path=root / "assets/watermark.png" if with_watermark else None,
        owner_password=owner_password,
    )
    assert data.startswith(b"%PDF-")
    reader = PdfReader(BytesIO(data))
    assert reader.is_encrypted is bool(owner_password)
    if owner_password:
        assert reader.decrypt("") == 1  # User still opens the report without a password.
        assert PdfReader(BytesIO(data)).decrypt(owner_password) == 2
    assert len(reader.pages) >= 1
    assert "Wiśnie" in "\n".join(page.extract_text() for page in reader.pages)
    # The product icon alone must not make a broken/no-op watermark pass.
    assert len(reader.pages[0].images) == (2 if with_watermark else 1)

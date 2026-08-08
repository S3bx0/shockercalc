from io import BytesIO

from tpof.core import pdf_report


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

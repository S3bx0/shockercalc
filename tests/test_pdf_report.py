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

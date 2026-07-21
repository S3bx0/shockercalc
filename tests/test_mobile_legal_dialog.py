from pathlib import Path

import pytest

from tpof.mobile.dialogs.legal import LegalDialogController, split_legal_text

ROOT = Path(__file__).resolve().parents[1]


def _controller(root: Path) -> LegalDialogController:
    return LegalDialogController(
        translate=lambda key, **_kwargs: key,
        project_root=root,
    )


def test_legal_controller_exposes_and_reads_packaged_documents(tmp_path):
    (tmp_path / "legal").mkdir()
    expected = {
        "EULA": "eula",
        "LICENSE": "source",
        "AI_USAGE_POLICY": "ai",
        "THIRD_PARTY_NOTICES": "third party",
        "legal/LGPL-3.0-only": "lgpl",
        "legal/GPL-3.0-only": "gpl",
    }
    for relative_path, content in expected.items():
        path = tmp_path / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    controller = _controller(tmp_path)

    assert [document.identifier for document in controller.documents] == [
        "eula",
        "source",
        "ai",
        "third_party",
        "lgpl",
        "gpl",
    ]
    assert controller.read_document("third_party") == "third party"
    assert controller.read_document("lgpl") == "lgpl"
    with pytest.raises(KeyError):
        controller.read_document("missing")


def test_split_legal_text_keeps_chunks_small_and_complete():
    text = "A" * 350 + "\n\n" + "B" * 350 + "\n\nshort"

    chunks = split_legal_text(text, max_chars=400)

    assert chunks == ["A" * 350, "B" * 350 + "\n\nshort"]
    assert all(len(chunk) <= 400 for chunk in chunks)


def test_split_legal_text_rejects_unusable_chunk_size():
    with pytest.raises(ValueError):
        split_legal_text("text", max_chars=100)


def test_repository_contains_every_document_exposed_in_mobile_settings():
    controller = _controller(ROOT)

    for document in controller.documents:
        text = controller.read_document(document.identifier)
        assert len(text) > 100, document.relative_path

    assert "TDM-Reservation: 1" in controller.read_document("ai")
    assert "fpdf2 2.8.7" in controller.read_document("third_party")

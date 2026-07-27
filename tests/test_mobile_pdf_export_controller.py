from __future__ import annotations

from datetime import datetime
from pathlib import Path

from tpof.mobile.pdf_export import PdfExportController

ROOT = Path(__file__).resolve().parents[1]


class _Product:
    def __init__(self, name: str) -> None:
        self.nazwa = name


class _Results:
    def __init__(self, product_name: str = "Mrożone jagody") -> None:
        self.produkt = _Product(product_name)


def _controller(
    tmp_path: Path,
    *,
    results=None,
    pdf_bytes: bytes | None = b"%PDF-test",
    share_result: bool = True,
    pdf_builder=None,
):
    messages: list[str] = []
    shares: list[tuple[str, str, str, str]] = []
    events: list[tuple[object, ...]] = []
    exceptions: list[tuple[BaseException, str]] = []
    builder_calls: list[object] = []

    def translate(key: str, **values: object) -> str:
        if key == "saved":
            return f"saved:{values['path']}"
        if key == "pdf_error":
            return f"pdf_error:{values['error']}"
        return key

    def build_pdf(current_results):
        builder_calls.append(current_results)
        return pdf_bytes

    def share_file(
        path: str,
        mime_type: str,
        subject: str,
        text: str,
    ) -> bool:
        shares.append((path, mime_type, subject, text))
        return share_result

    controller = PdfExportController(
        get_results=lambda: results,
        translate=translate,
        show_message=messages.append,
        share_file=share_file,
        log_event=lambda *args: events.append(args),
        record_exception=lambda exc, context: exceptions.append((exc, context)),
        output_dir=lambda: tmp_path,
        now=lambda: datetime(2026, 7, 27, 12, 34, 56),
        pdf_builder=pdf_builder or build_pdf,
    )
    return {
        "controller": controller,
        "messages": messages,
        "shares": shares,
        "events": events,
        "exceptions": exceptions,
        "builder_calls": builder_calls,
    }


def test_export_requires_calculation_results(tmp_path):
    state = _controller(tmp_path, results=None)

    assert state["controller"].export() is None

    assert state["messages"] == ["pdf_first"]
    assert state["builder_calls"] == []
    assert state["shares"] == []
    assert list(tmp_path.iterdir()) == []


def test_export_writes_and_shares_pdf(tmp_path):
    results = _Results()
    state = _controller(tmp_path, results=results)

    exported = state["controller"].export()

    assert exported == (
        tmp_path / "RefrigerationCalc_Mrożone_jagody_20260727_123456.pdf"
    )
    assert exported.read_bytes() == b"%PDF-test"
    assert state["builder_calls"] == [results]
    assert state["shares"] == [
        (
            str(exported),
            "application/pdf",
            "pdf_share_subject",
            "pdf_share_text",
        )
    ]
    assert state["events"] == [
        ("pdf_generated", {"calculator": "freezing"}),
        ("report_shared", {"calculator": "freezing"}),
    ]
    assert state["messages"] == []
    assert state["exceptions"] == []


def test_export_reports_saved_path_when_native_share_is_unavailable(tmp_path):
    state = _controller(
        tmp_path,
        results=_Results("Jabłko"),
        share_result=False,
    )

    exported = state["controller"].export()

    assert exported is not None
    assert state["events"] == [
        ("pdf_generated", {"calculator": "freezing"}),
    ]
    assert state["messages"] == [f"saved:{exported}"]


def test_export_reports_unavailable_pdf_builder(tmp_path):
    state = _controller(
        tmp_path,
        results=_Results(),
        pdf_bytes=None,
    )

    assert state["controller"].export() is None

    assert state["messages"] == ["pdf_unavailable"]
    assert state["shares"] == []
    assert list(tmp_path.iterdir()) == []


def test_export_contains_failures_and_reports_telemetry(tmp_path):
    def fail(_results):
        raise RuntimeError("builder failed")

    state = _controller(
        tmp_path,
        results=_Results(),
        pdf_builder=fail,
    )

    assert state["controller"].export() is None

    assert len(state["exceptions"]) == 1
    error, context = state["exceptions"][0]
    assert isinstance(error, RuntimeError)
    assert context == "export_pdf"
    assert state["messages"] == ["pdf_error:builder failed"]
    assert state["shares"] == []


def test_main_delegates_pdf_export_to_controller():
    main_source = (ROOT / "tpof" / "mobile" / "main.py").read_text(encoding="utf-8")

    assert "self._pdf_export = PdfExportController(" in main_source
    assert "share_file=self._android.share_file" in main_source
    assert "on_export_pdf=self._pdf_export.export" in main_source
    assert "def _build_pdf_bytes" not in main_source
    assert "def _export_pdf" not in main_source

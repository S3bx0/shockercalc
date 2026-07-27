"""Mobile PDF export helpers."""
from __future__ import annotations

import logging
import os
from collections.abc import Callable, Mapping
from datetime import datetime
from pathlib import Path

from tpof.core.models import FreezingResults
from tpof.mobile.android_bridge import (
    _purge_host_arch_fonttools_so,
    _runtime_font_path,
)
from tpof.mobile.catalog import _safe_image_path

log = logging.getLogger(__name__)


def _pdf_output_dir() -> Path:
    """Zwraca prywatny katalog PDF bez żądania szerokich uprawnień storage."""
    if "ANDROID_ARGUMENT" in os.environ:
        private_root = Path(os.environ.get("ANDROID_PRIVATE", os.getcwd()))
        pdf_dir = private_root / "pdf"
        try:
            pdf_dir.mkdir(parents=True, exist_ok=True)
            return pdf_dir
        except OSError:
            return private_root
    return Path.cwd()


class PdfExportController:
    """Build, save and share freezing reports without depending on Kivy."""

    def __init__(
        self,
        *,
        get_results: Callable[[], FreezingResults | None],
        translate: Callable[..., str],
        show_message: Callable[[str], None],
        share_file: Callable[[str, str, str, str], bool],
        log_event: Callable[[str, Mapping[str, object] | None], None],
        record_exception: Callable[[BaseException, str], None],
        output_dir: Callable[[], Path] = _pdf_output_dir,
        now: Callable[[], datetime] = datetime.now,
        pdf_builder: Callable[[FreezingResults], bytes | None] | None = None,
    ) -> None:
        self._get_results = get_results
        self._translate = translate
        self._show_message = show_message
        self._share_file = share_file
        self._log_event = log_event
        self._record_exception = record_exception
        self._output_dir = output_dir
        self._now = now
        self._pdf_builder = pdf_builder or self.build_pdf_bytes

    @staticmethod
    def build_pdf_bytes(results: FreezingResults) -> bytes | None:
        """Build a PDF without exposing source product properties."""
        runtime_font = _runtime_font_path()
        if runtime_font is not None:
            try:
                from tpof.core.pdf_report import build_pdf

                img_path = _safe_image_path(results.produkt.nazwa)
                return build_pdf(
                    results,
                    font_path=runtime_font,
                    product_image_path=Path(img_path) if img_path else None,
                    watermark_image_path=None,
                )
            except ImportError:
                pass
        try:
            _purge_host_arch_fonttools_so()
            from tpof.core.pdf_report_mobile import build_pdf_simple
        except ImportError:
            return None
        return build_pdf_simple(results, font_path=runtime_font)

    def export(self) -> Path | None:
        """Export the latest freezing result and return its saved path."""
        results = self._get_results()
        if results is None:
            self._show_message(self._translate("pdf_first"))
            return None
        try:
            pdf_bytes = self._pdf_builder(results)
            if pdf_bytes is None:
                self._show_message(self._translate("pdf_unavailable"))
                return None
            out_dir = self._output_dir()
            out_dir.mkdir(parents=True, exist_ok=True)
            timestamp = self._now().strftime("%Y%m%d_%H%M%S")
            product_name = results.produkt.nazwa.replace(" ", "_")
            out_path = out_dir / f"RefrigerationCalc_{product_name}_{timestamp}.pdf"
            out_path.write_bytes(pdf_bytes)
            self._log_event("pdf_generated", {"calculator": "freezing"})
            if self._share_file(
                str(out_path),
                "application/pdf",
                self._translate("pdf_share_subject"),
                self._translate("pdf_share_text"),
            ):
                self._log_event("report_shared", {"calculator": "freezing"})
            else:
                self._show_message(self._translate("saved", path=out_path))
            return out_path
        except Exception as exc:  # pragma: no cover - UI feedback
            self._record_exception(exc, "export_pdf")
            log.exception("Eksport PDF")
            self._show_message(self._translate("pdf_error", error=exc))
            return None

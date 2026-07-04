"""Mobile PDF export helpers."""
from __future__ import annotations

import os
from pathlib import Path


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

"""Ścieżki do zasobów w wersji mobilnej.

Na Androidzie pliki z `assets/` są pakowane do APK (sekcja `source.include_patterns`
w `buildozer.spec`) i dostępne względem katalogu uruchomieniowego aplikacji.
Na desktopie (testy lokalne KivyMD) korzystamy z normalnej lokalizacji projektu.
"""
from __future__ import annotations

import os
from pathlib import Path


def _app_root() -> Path:
    """Katalog z którego startuje aplikacja (na Androidzie = unpack APK)."""
    # Na Androidzie p4a ustawia ANDROID_ARGUMENT / ANDROID_APP_PATH
    if "ANDROID_ARGUMENT" in os.environ:
        return Path(os.environ.get("ANDROID_APP_PATH", os.getcwd()))
    # Desktop: dwa poziomy w górę od tpof/mobile/paths.py = root projektu
    return Path(__file__).resolve().parents[2]


PROJECT_ROOT: Path = _app_root()
ASSETS_DIR: Path = PROJECT_ROOT / "assets"
DATA_PATH: Path = ASSETS_DIR / "Table3.json"
FONT_PATH: Path = ASSETS_DIR / "fonts" / "DejaVuSans.ttf"
IMAGES_DIR: Path = ASSETS_DIR / "images"
WATERMARK_PATH: Path = ASSETS_DIR / "watermark.png"

"""Stałe ścieżek do zasobów aplikacji.

Etap 2: pliki nadal leżą w korzeniu projektu (Table3.json, Zdjęcia/, fonty).
Etap 3 przeniesie je do `assets/` i zmieni tylko ten plik.
"""

from __future__ import annotations

from pathlib import Path

# Ścieżka do katalogu projektu (TPOF/)
PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]

# Aktywne lokalizacje (Etap 2 — bez przenoszenia plików)
DATA_PATH: Path = PROJECT_ROOT / "Table3.json"
IMAGES_DIR: Path = PROJECT_ROOT / "Zdjęcia"
FONT_PATH: Path = PROJECT_ROOT / "dejavu-fonts-ttf-2.37" / "ttf" / "DejaVuSans.ttf"
FALLBACK_IMAGE: Path = PROJECT_ROOT / "bloodghast.jpg"

# Watermark — Etap 3 skopiuje go lokalnie do assets/watermark.png
WATERMARK_PATH: Path = PROJECT_ROOT.parent.parent / "_Logo" / "PUCH (300ppi) - TIFF.TIF"

# Po Etapie 3 (przygotowane wcześniej, używane jeśli plik istnieje):
ASSETS_DIR: Path = PROJECT_ROOT / "assets"
_LOCAL_WATERMARK: Path = ASSETS_DIR / "watermark.png"
if _LOCAL_WATERMARK.exists():
    WATERMARK_PATH = _LOCAL_WATERMARK
_LOCAL_FONT: Path = ASSETS_DIR / "fonts" / "DejaVuSans.ttf"
if _LOCAL_FONT.exists():
    FONT_PATH = _LOCAL_FONT
_LOCAL_DATA: Path = ASSETS_DIR / "Table3.json"
if _LOCAL_DATA.exists():
    DATA_PATH = _LOCAL_DATA
_LOCAL_IMAGES: Path = ASSETS_DIR / "images"
if _LOCAL_IMAGES.exists():
    IMAGES_DIR = _LOCAL_IMAGES

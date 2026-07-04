"""Android runtime helpers for the mobile application.

The current implementation lives in ``tpof.mobile.main``. Keep this module
framework-light while migrating methods so desktop/core tests can import it.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import List, Optional

from tpof.mobile.constants import IS_ANDROID
from tpof.mobile.paths import FONT_PATH

log = logging.getLogger(__name__)

_FONTTOOLS_SO_PURGED = False


def _runtime_font_path() -> Optional[Path]:
    """Używa fontu aplikacji albo kopii DejaVu dostarczanej przez Kivy."""
    if FONT_PATH.exists():
        return FONT_PATH
    try:
        from kivy.resources import resource_find

        found = resource_find("data/fonts/DejaVuSans.ttf")
        return Path(found) if found else None
    except ImportError:
        return None


def _purge_host_arch_fonttools_so() -> None:
    """Usuwa host-arch (.so) rozszerzenia fonttools z rozpakowanego bundla.

    Na Androidzie p4a instaluje fonttools hostowym pipem, więc skompilowane
    rozszerzenia Cython (np. ``fontTools/misc/bezierTools.so``) są dla x86_64,
    a nie arm64 -> ``dlopen`` pada przy generowaniu PDF. Katalog
    ``_python_bundle`` jest rozpakowany do zapisywalnego ``files/app/...``,
    więc kasujemy te ``.so`` w runtime - fonttools wraca do czystego Pythona.
    """
    global _FONTTOOLS_SO_PURGED
    if _FONTTOOLS_SO_PURGED or not IS_ANDROID:
        return
    _FONTTOOLS_SO_PURGED = True

    import sys

    roots: List[str] = []
    try:
        import fontTools  # noqa: WPS433 - pakiet __init__ jest czysto-pythonowy

        roots.extend(getattr(fontTools, "__path__", []) or [])
    except Exception:  # pragma: no cover - Android only
        pass
    for entry in sys.path:
        candidate = os.path.join(entry, "fontTools")
        if os.path.isdir(candidate):
            roots.append(candidate)

    seen = set()
    for root in roots:
        root = os.path.abspath(root)
        if root in seen or not os.path.isdir(root):
            continue
        seen.add(root)
        for dirpath, _dirnames, filenames in os.walk(root):
            for name in filenames:
                if name.endswith(".so"):
                    try:
                        os.remove(os.path.join(dirpath, name))
                        log.warning("Usunieto host-arch fonttools .so: %s", name)
                    except OSError as exc:  # pragma: no cover - Android only
                        log.warning("Nie usunieto %s: %s", name, exc)

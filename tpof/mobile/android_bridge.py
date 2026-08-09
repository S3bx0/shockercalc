"""Android runtime facade and helpers for the mobile application."""
from __future__ import annotations

import logging
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

from tpof.mobile.constants import IS_ANDROID
from tpof.mobile.paths import FONT_PATH

log = logging.getLogger(__name__)

_FONTTOOLS_SO_PURGED = False


class AndroidActivityBridge:
    """Expose the small native Activity contract used by Python controllers."""

    def __init__(
        self,
        *,
        is_android: bool = IS_ANDROID,
        activity_loader: Callable[[], Any] | None = None,
    ) -> None:
        self._is_android = is_android
        self._activity_loader = activity_loader or self._load_activity

    @staticmethod
    def _load_activity() -> Any:
        from jnius import autoclass, cast

        activity = autoclass("org.kivy.android.PythonActivity").mActivity
        try:
            return cast(
                "pl.smilczarek.refrigerationcalc.RefrigerationCalcActivity",
                activity,
            )
        except Exception:  # pragma: no cover - Android only
            return activity

    def activity(self) -> Any:
        """Return the cast native Activity for Android-only service calls."""
        if not self._is_android:
            raise RuntimeError("Android Activity is unavailable outside Android")
        return self._activity_loader()

    def set_active_ad_tab(self, tab: str) -> bool:
        if not self._is_android:
            return False
        try:
            self.activity().setActiveAdTab(tab)
            return True
        except Exception:  # pragma: no cover - Android only
            log.debug("setActiveAdTab nie powiodło się", exc_info=True)
            return False

    def consume_shortcut_tab(self) -> str | None:
        """Return and clear the pending launcher-shortcut destination."""

        if not self._is_android:
            return None
        try:
            target = self.activity().consumePendingShortcutTab()
            normalized = str(target or "").strip()
            return normalized or None
        except Exception:  # pragma: no cover - Android only
            log.debug("Odczyt skrótu aplikacji nie powiódł się", exc_info=True)
            return None

    def configure_accessibility(self, description: str) -> bool:
        """Expose the current Kivy-screen summary to Android TalkBack."""

        if not self._is_android:
            return False
        try:
            self.activity().configureAccessibility(str(description))
            return True
        except Exception:  # pragma: no cover - Android only
            log.debug("Konfiguracja TalkBack nie powiodła się", exc_info=True)
            return False

    def announce_for_accessibility(self, message: str) -> bool:
        """Politely announce an important UI message through TalkBack."""

        if not self._is_android or not str(message).strip():
            return False
        try:
            self.activity().announceForAccessibility(str(message).strip())
            return True
        except Exception:  # pragma: no cover - Android only
            log.debug("Komunikat TalkBack nie powiódł się", exc_info=True)
            return False

    def banner_height_dp(self) -> int:
        if not self._is_android:
            return 0
        try:
            return int(self.activity().getBannerHeightDp())
        except Exception:  # pragma: no cover - Android only
            log.debug("Nie udało się odczytać wysokości banera", exc_info=True)
            return 0

    def resolved_banner_height(self, pro_active: bool, current_height: int) -> int:
        """Return a usable changed height, or preserve the current UI value."""
        if pro_active:
            return current_height
        height = self.banner_height_dp()
        return height if height > 0 else current_height

    def privacy_options_required(self) -> bool:
        if not self._is_android:
            return False
        return bool(self.activity().isPrivacyOptionsRequired())

    def show_privacy_options_form(self) -> None:
        if not self._is_android:
            return
        self.activity().showPrivacyOptionsForm()

    def share_file(
        self,
        path: str,
        mime_type: str,
        subject: str,
        text: str,
    ) -> bool:
        if not self._is_android:
            return False
        try:
            self.activity().shareFile(path, mime_type, subject, text)
            return True
        except Exception:  # pragma: no cover - Android only
            log.exception("Udostępnianie pliku Android")
            return False

    def open_feedback_email(
        self,
        recipient: str,
        subject: str,
        body: str,
    ) -> bool:
        """Open an editable feedback draft in a native Android email app."""
        if not self._is_android:
            return False
        try:
            self.activity().openFeedbackEmail(recipient, subject, body)
            return True
        except Exception:  # pragma: no cover - Android only
            log.exception("Otwarcie wiadomości z opinią Android")
            return False

    def open_google_play_listing(self, package_name: str) -> bool:
        """Open the app's Google Play page for voluntary tester feedback."""
        if not self._is_android:
            return False
        try:
            self.activity().openGooglePlayListing(package_name)
            return True
        except Exception:  # pragma: no cover - Android only
            log.exception("Otwarcie Google Play dla opinii testowej")
            return False


def _runtime_font_path() -> Path | None:
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

    roots: list[str] = []
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

"""Uprawnienia: 7-dniowy pełny trial, potem freemium (1 produkt z każdej listy).

Logika świadomie oddzielona od UI, żeby dało się ją łatwo testować bez Kivy.

Reguły:
  • Pierwsze uruchomienie zapisuje znacznik czasu (``first_launch_ts``).
  • Przez ``TRIAL_DAYS`` dni użytkownik ma pełny dostęp do wszystkich produktów.
  • Po wygaśnięciu triala (bez PRO) dostępny jest tylko pierwszy produkt
    z każdej kategorii (``FREE_PRODUCTS_PER_CATEGORY``).
  • Zakup PRO (``pro_no_ads``) odblokowuje wszystko bezterminowo.

Stan trwały trzymany jest w pliku JSON w prywatnym katalogu aplikacji
(Android: ``ANDROID_PRIVATE``; desktop: ``%APPDATA%``/``~/.config``).
"""
from __future__ import annotations

import json
import math
import os
import time
from pathlib import Path
from typing import Callable, Optional

TRIAL_DAYS = 7
_TRIAL_SECONDS = TRIAL_DAYS * 24 * 60 * 60
FREE_PRODUCTS_PER_CATEGORY = 1
STATE_FILE = "entitlement.json"


def _state_dir() -> Path:
    """Katalog na trwały stan uprawnień (zapisywalny na danej platformie)."""
    if "ANDROID_ARGUMENT" in os.environ:
        base = (
            os.environ.get("ANDROID_PRIVATE")
            or os.environ.get("ANDROID_APP_PATH")
            or os.getcwd()
        )
        return Path(base)
    base = (
        os.environ.get("APPDATA")
        or os.environ.get("XDG_CONFIG_HOME")
        or str(Path.home())
    )
    return Path(base) / "RefrigerationCalc"


class Entitlements:
    """Stan uprawnień użytkownika (trial + freemium)."""

    def __init__(
        self,
        state_path: Optional[Path] = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._clock = clock
        self._path = Path(state_path) if state_path else (_state_dir() / STATE_FILE)
        self._first_launch_ts: Optional[float] = None
        self._load()

    # --- trwały stan -----------------------------------------------------
    def _load(self) -> None:
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except (FileNotFoundError, ValueError, OSError):
            return
        ts = data.get("first_launch_ts")
        if isinstance(ts, (int, float)) and ts > 0:
            self._first_launch_ts = float(ts)

    def _save(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(
                json.dumps({"first_launch_ts": self._first_launch_ts}),
                encoding="utf-8",
            )
        except OSError:
            # Brak możliwości zapisu nie powinien wywracać aplikacji.
            pass

    def ensure_started(self) -> None:
        """Zapisuje datę pierwszego uruchomienia, jeśli jeszcze jej nie ma."""
        if self._first_launch_ts is None:
            self._first_launch_ts = float(self._clock())
            self._save()

    # --- trial -----------------------------------------------------------
    def trial_start_ts(self) -> Optional[float]:
        return self._first_launch_ts

    def trial_seconds_left(self) -> float:
        if self._first_launch_ts is None:
            return float(_TRIAL_SECONDS)
        elapsed = self._clock() - self._first_launch_ts
        return max(0.0, _TRIAL_SECONDS - elapsed)

    def trial_days_left(self) -> int:
        """Liczba pełnych dni triala (zaokrąglona w górę), min. 0."""
        return int(math.ceil(self.trial_seconds_left() / 86400.0))

    def is_trial_active(self) -> bool:
        return self.trial_seconds_left() > 0

    # --- dostęp do funkcji ----------------------------------------------
    def is_unlocked(self, pro: bool) -> bool:
        """Pełny dostęp = aktywne PRO lub trwający trial."""
        return bool(pro) or self.is_trial_active()

    def is_product_allowed(self, index: int, pro: bool) -> bool:
        """Czy produkt o indeksie ``index`` (0-based w kategorii) jest dostępny."""
        if self.is_unlocked(pro):
            return True
        return index < FREE_PRODUCTS_PER_CATEGORY

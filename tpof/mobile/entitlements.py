"""Uprawnienia: 7-dniowy pełny trial, freemium produktów oraz moduły funkcyjne.

Logika świadomie oddzielona od UI, żeby dało się ją łatwo testować bez Kivy.

Model uprawnień ma trzy warstwy:

1. **Trial** — pierwsze ``TRIAL_DAYS`` dni od instalacji dają pełny dostęp
   do wszystkiego (wszystkie produkty, wszystkie moduły).

2. **Freemium produktów** — po wygaśnięciu triala (bez PRO) dostępny jest
   tylko pierwszy produkt z każdej kategorii (``FREE_PRODUCTS_PER_CATEGORY``).

3. **Moduły funkcyjne (karty)** — każda karta obliczeniowa to osobny moduł
   o własnym identyfikatorze. Moduł rdzeniowy (``CORE_MODULE``) jest zawsze
   darmowy i pełni rolę „haka". Kolejne karty (np. dobór zaworów
   dekompresyjnych) będą płatnymi modułami jednorazowymi, kupowanymi przez
   Google Play Billing i nadawanymi przez :meth:`Entitlements.grant_module`.

Zakup PRO (``pro_no_ads``) usuwa reklamy oraz odblokowuje pełną listę
produktów. Dostęp do płatnych modułów funkcyjnych jest niezależny od
``pro_no_ads`` — chyba że dany moduł zostanie jawnie nadany lub trwa trial.

Stan trwały trzymany jest w pliku JSON w prywatnym katalogu aplikacji
(Android: ``ANDROID_PRIVATE``; desktop: ``%APPDATA%``/``~/.config``).
"""
from __future__ import annotations

import json
import math
import os
import time
from pathlib import Path
from typing import Callable, Iterable, Optional

TRIAL_DAYS = 7
_TRIAL_SECONDS = TRIAL_DAYS * 24 * 60 * 60
FREE_PRODUCTS_PER_CATEGORY = 1
STATE_FILE = "entitlement.json"

# --- Moduły funkcyjne (karty obliczeniowe) -------------------------------
# Identyfikatory muszą się 1:1 zgadzać z ID produktów w Google Play Billing.
CORE_MODULE = "freezing"            # rdzeń: obliczenia mocy zamrażania (zawsze darmowy)
MODULE_VALVES = "module_valves"     # dobór zaworów dekompresyjnych (płatny)
MODULE_INSULATION = "module_insulation"  # izolacje / obciążenie komory (płatny)

# Moduły dostępne bez opłaty (rdzeń + ewentualne darmowe karty promocyjne).
FREE_MODULES: frozenset = frozenset({CORE_MODULE})



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
    """Stan uprawnień użytkownika (trial + freemium + moduły funkcyjne)."""

    def __init__(
        self,
        state_path: Optional[Path] = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._clock = clock
        self._path = Path(state_path) if state_path else (_state_dir() / STATE_FILE)
        self._first_launch_ts: Optional[float] = None
        self._modules: set = set()
        self._load()

    # --- trwały stan -----------------------------------------------------
    def _load(self) -> None:
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except (FileNotFoundError, ValueError, OSError):
            return
        if not isinstance(data, dict):
            return
        ts = data.get("first_launch_ts")
        if isinstance(ts, (int, float)) and ts > 0:
            self._first_launch_ts = float(ts)
        mods = data.get("modules")
        if isinstance(mods, list):
            self._modules = {str(m) for m in mods if isinstance(m, str)}

    def _save(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(
                json.dumps(
                    {
                        "first_launch_ts": self._first_launch_ts,
                        "modules": sorted(self._modules),
                    }
                ),
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

    # --- moduły funkcyjne (karty) ---------------------------------------
    def owned_modules(self) -> frozenset:
        """Moduły jawnie posiadane przez użytkownika (kupione)."""
        return frozenset(self._modules)

    def grant_module(self, module_id: str) -> None:
        """Nadaje moduł (np. po udanym zakupie w Google Play Billing)."""
        if module_id and module_id not in self._modules:
            self._modules.add(module_id)
            self._save()

    def revoke_module(self, module_id: str) -> None:
        """Cofa moduł (np. po zwrocie/anulowaniu zakupu)."""
        if module_id in self._modules:
            self._modules.discard(module_id)
            self._save()

    def sync_modules(self, module_ids: Iterable[str]) -> None:
        """Ustawia komplet posiadanych modułów wg listy z warstwy Billing."""
        new = {str(m) for m in module_ids if m}
        if new != self._modules:
            self._modules = new
            self._save()

    def has_module(self, module_id: str, pro: bool = False) -> bool:
        """Czy moduł (karta) jest dostępny.

        Dostępny gdy: moduł darmowy, trwa trial, został kupiony, lub PRO.
        """
        if module_id in FREE_MODULES:
            return True
        if self.is_trial_active() or bool(pro):
            return True
        return module_id in self._modules

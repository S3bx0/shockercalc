"""Uprawnienia: 1-dniowy pełny trial, freemium produktów oraz moduły funkcyjne.

Logika świadomie oddzielona od UI, żeby dało się ją łatwo testować bez Kivy.

Model uprawnień ma trzy warstwy:

1. **Trial** — pierwszy dzień od instalacji daje pełny dostęp
   do wszystkiego (wszystkie produkty, wszystkie moduły).

2. **Freemium produktów** — po wygaśnięciu triala (bez PRO) dostępny jest
   tylko pierwszy produkt z każdej kategorii (``FREE_PRODUCTS_PER_CATEGORY``).

3. **Moduły funkcyjne (karty)** — każda karta obliczeniowa to osobny moduł
   o własnym identyfikatorze. Moduł rdzeniowy (``CORE_MODULE``) jest zawsze
   darmowy i pełni rolę „haka". Kolejne karty (np. dobór zaworów
   dekompresyjnych) będą płatnymi modułami jednorazowymi, kupowanymi przez
   Google Play Billing i nadawanymi przez :meth:`Entitlements.grant_module`.

PRO (aktywna subskrypcja ``refrigeration_pro`` albo legacy ``pro_no_ads``)
usuwa reklamy, odblokowuje pełną listę produktów oraz płatne moduły. Moduły
nadal mogą być kupione jednorazowo przez ``grant_module`` jako fallback/legacy.
Trial daje czasowy podgląd wszystkich kart.

4. **Tokeny za reklamy (rewarded)** — darmowy użytkownik bez PRO/triala może
   obejrzeć reklamę rewarded i otrzymać token, który pozwala na **jedno**
   bezpłatne przeliczenie zablokowanego produktu w karcie rdzeniowej.
   Limit ``REWARD_DAILY_AD_CAP`` reklam na dobę chroni przed nadużyciem i
   popycha intensywnych użytkowników do zakupu PRO. Opcjonalny cooldown
   ``REWARD_AD_COOLDOWN_S`` między reklamami (domyślnie 0 — bez przerwy).

Stan trwały trzymany jest w pliku JSON w prywatnym katalogu aplikacji
(Android: ``ANDROID_PRIVATE``; desktop: ``%APPDATA%``/``~/.config``).
"""
from __future__ import annotations

import json
import math
import os
import time
from collections.abc import Callable, Iterable
from pathlib import Path

TRIAL_DAYS = 1
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

# --- Tokeny za reklamy rewarded ------------------------------------------
# Wariant B: 1 reklama = 1 token, bez wymuszonej przerwy między reklamami,
# ale z dziennym sufitem obejrzanych reklam. Cooldown jest parametrem
# (domyślnie 0 s); ustaw na np. 21600 (6h), jeśli chcesz wymusić odstęp.
REWARD_TOKEN_PER_AD = 1     # ile tokenów daje jedna obejrzana reklama
REWARD_DAILY_AD_CAP = 8     # maks. liczba reklam rozliczonych w ciągu doby
REWARD_AD_COOLDOWN_S = 0    # minimalny odstęp między reklamami (0 = brak)
_REWARD_DAY_SECONDS = 24 * 60 * 60



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
        state_path: Path | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._clock = clock
        self._path = Path(state_path) if state_path else (_state_dir() / STATE_FILE)
        self._first_launch_ts: float | None = None
        self._modules: set = set()
        self._reward_tokens: int = 0
        self._ad_timestamps: list = []  # epoch ostatnich obejrzanych reklam
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
        tokens = data.get("reward_tokens")
        if isinstance(tokens, int) and tokens > 0:
            self._reward_tokens = tokens
        stamps = data.get("ad_timestamps")
        if isinstance(stamps, list):
            self._ad_timestamps = [
                float(s) for s in stamps if isinstance(s, (int, float)) and s > 0
            ]

    def _save(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(
                json.dumps(
                    {
                        "first_launch_ts": self._first_launch_ts,
                        "modules": sorted(self._modules),
                        "reward_tokens": self._reward_tokens,
                        "ad_timestamps": self._ad_timestamps,
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
    def trial_start_ts(self) -> float | None:
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

    def try_unlock_product_with_token(self, index: int, pro: bool) -> bool:
        """Próbuje odblokować zablokowany produkt zużywając jeden token.

        Jeśli produkt i tak jest dostępny (PRO/trial/freemium) — nic nie zużywa
        i zwraca ``True``. Jeśli jest zablokowany, zużywa token (gdy dostępny) i
        zwraca ``True``; gdy brak tokenów — ``False``. Wywoływać w momencie
        faktycznego przeliczenia, nie do samego renderowania UI.
        """
        if self.is_product_allowed(index, pro):
            return True
        return self.consume_reward_token()

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

        Moduł jest dostępny gdy:
          • należy do darmowych (``FREE_MODULES``, np. rdzeń zamrażania), lub
          • trwa trial (czasowy podgląd wszystkich kart), lub
          • aktywne jest PRO (subskrypcja/legacy), lub
          • został kupiony (``grant_module``).
        """
        if module_id in FREE_MODULES:
            return True
        if self.is_trial_active():
            return True
        if pro:
            return True
        return module_id in self._modules

    def try_unlock_module_with_token(self, module_id: str, pro: bool = False) -> bool:
        """Próbuje odblokować płatny moduł zużywając jeden token za reklamę.

        Jeśli moduł i tak jest dostępny (darmowy/trial/kupiony) — nic nie zużywa
        i zwraca ``True``. Jeśli jest zablokowany, zużywa token (gdy dostępny) i
        zwraca ``True``; gdy brak tokenów — ``False``. Wywoływać w momencie
        faktycznego użycia karty (np. przeliczenia), nie do renderowania UI.

        Token daje JEDNO użycie — moduł nie jest nadawany na stałe (do tego służy
        zakup przez :meth:`grant_module`).
        """
        if self.has_module(module_id, pro):
            return True
        return self.consume_reward_token()

    # --- tokeny za reklamy rewarded -------------------------------------
    def _prune_ad_window(self) -> None:
        """Usuwa znaczniki reklam starsze niż 24h (przesuwne okno doby)."""
        cutoff = self._clock() - _REWARD_DAY_SECONDS
        kept = [t for t in self._ad_timestamps if t > cutoff]
        if len(kept) != len(self._ad_timestamps):
            self._ad_timestamps = kept

    def reward_tokens(self) -> int:
        """Liczba dostępnych tokenów (1 token = 1 bezpłatne przeliczenie)."""
        return self._reward_tokens

    def ads_watched_today(self) -> int:
        """Liczba reklam rozliczonych w bieżącym oknie 24h."""
        self._prune_ad_window()
        return len(self._ad_timestamps)

    def ads_left_today(self) -> int:
        """Ile jeszcze reklam można dziś rozliczyć (do ``REWARD_DAILY_AD_CAP``)."""
        return max(0, REWARD_DAILY_AD_CAP - self.ads_watched_today())

    def ad_cooldown_left(self) -> float:
        """Sekundy do końca cooldownu między reklamami (0 = można oglądać)."""
        if REWARD_AD_COOLDOWN_S <= 0 or not self._ad_timestamps:
            return 0.0
        last = max(self._ad_timestamps)
        remaining = REWARD_AD_COOLDOWN_S - (self._clock() - last)
        return max(0.0, remaining)

    def can_watch_ad(self) -> bool:
        """Czy można teraz obejrzeć reklamę po token (limit dobowy + cooldown)."""
        return self.ads_left_today() > 0 and self.ad_cooldown_left() <= 0

    def grant_reward_for_ad(self) -> bool:
        """Rozlicza obejrzaną reklamę: dodaje token i zapisuje znacznik czasu.

        Zwraca ``True`` gdy token przyznano, ``False`` gdy wykorzystano limit
        dobowy lub trwa cooldown (wtedy stan się nie zmienia). Wywoływać tylko
        po faktycznym, pełnym obejrzeniu reklamy rewarded (callback AdMob).
        """
        if not self.can_watch_ad():
            return False
        self._ad_timestamps.append(float(self._clock()))
        self._reward_tokens += REWARD_TOKEN_PER_AD
        self._save()
        return True

    def consume_reward_token(self) -> bool:
        """Zużywa jeden token na pojedyncze bezpłatne przeliczenie.

        Zwraca ``True`` gdy token był dostępny i został odjęty, w przeciwnym
        razie ``False`` (brak tokenów).
        """
        if self._reward_tokens <= 0:
            return False
        self._reward_tokens -= 1
        self._save()
        return True

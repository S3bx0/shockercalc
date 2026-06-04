"""Testy logiki uprawnień (trial 7 dni + freemium 1 produkt/kategoria).

Nie wymagają Kivy/KivyMD — czysty Python, sterowanie czasem przez wstrzyknięty zegar.
"""
from __future__ import annotations

from pathlib import Path

from tpof.mobile.entitlements import (
    FREE_PRODUCTS_PER_CATEGORY,
    TRIAL_DAYS,
    CORE_MODULE,
    MODULE_VALVES,
    MODULE_INSULATION,
    Entitlements,
)

_DAY = 24 * 60 * 60


class _Clock:
    """Sterowalny zegar do testów."""

    def __init__(self, now: float = 1_000_000.0) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now

    def advance_days(self, days: float) -> None:
        self.now += days * _DAY


def _make(tmp_path: Path, clock: _Clock) -> Entitlements:
    return Entitlements(state_path=tmp_path / "entitlement.json", clock=clock)


def test_pierwsze_uruchomienie_startuje_trial(tmp_path):
    clock = _Clock()
    ent = _make(tmp_path, clock)
    assert ent.trial_start_ts() is None
    ent.ensure_started()
    assert ent.trial_start_ts() == clock.now
    assert ent.is_trial_active()


def test_trial_aktywny_przez_caly_okres(tmp_path):
    clock = _Clock()
    ent = _make(tmp_path, clock)
    ent.ensure_started()
    clock.advance_days(TRIAL_DAYS - 0.5)
    assert ent.is_trial_active()
    assert ent.is_unlocked(pro=False)


def test_trial_wygasa_po_okresie(tmp_path):
    clock = _Clock()
    ent = _make(tmp_path, clock)
    ent.ensure_started()
    clock.advance_days(TRIAL_DAYS + 0.1)
    assert not ent.is_trial_active()
    assert not ent.is_unlocked(pro=False)


def test_pro_odblokowuje_po_wygasnieciu(tmp_path):
    clock = _Clock()
    ent = _make(tmp_path, clock)
    ent.ensure_started()
    clock.advance_days(TRIAL_DAYS + 5)
    assert not ent.is_unlocked(pro=False)
    assert ent.is_unlocked(pro=True)


def test_freemium_dostepny_tylko_pierwszy_produkt(tmp_path):
    clock = _Clock()
    ent = _make(tmp_path, clock)
    ent.ensure_started()
    clock.advance_days(TRIAL_DAYS + 1)
    # Bez PRO: tylko pierwszy produkt (index 0) dozwolony.
    assert ent.is_product_allowed(0, pro=False)
    assert not ent.is_product_allowed(1, pro=False)
    assert not ent.is_product_allowed(5, pro=False)


def test_freemium_w_trakcie_trialu_wszystko_dostepne(tmp_path):
    clock = _Clock()
    ent = _make(tmp_path, clock)
    ent.ensure_started()
    assert ent.is_product_allowed(0, pro=False)
    assert ent.is_product_allowed(99, pro=False)


def test_pro_odblokowuje_wszystkie_produkty(tmp_path):
    clock = _Clock()
    ent = _make(tmp_path, clock)
    ent.ensure_started()
    clock.advance_days(TRIAL_DAYS + 10)
    assert ent.is_product_allowed(0, pro=True)
    assert ent.is_product_allowed(50, pro=True)


def test_data_pierwszego_uruchomienia_jest_trwala(tmp_path):
    clock = _Clock()
    ent = _make(tmp_path, clock)
    ent.ensure_started()
    started = ent.trial_start_ts()
    # Nowa instancja czyta zapisany stan z pliku.
    ent2 = _make(tmp_path, clock)
    assert ent2.trial_start_ts() == started
    # Ponowne ensure_started nie nadpisuje daty.
    clock.advance_days(2)
    ent2.ensure_started()
    assert ent2.trial_start_ts() == started


def test_dni_trialu_maleja(tmp_path):
    clock = _Clock()
    ent = _make(tmp_path, clock)
    ent.ensure_started()
    assert ent.trial_days_left() == TRIAL_DAYS
    clock.advance_days(1)
    assert ent.trial_days_left() == TRIAL_DAYS - 1
    clock.advance_days(TRIAL_DAYS)
    assert ent.trial_days_left() == 0


def test_uszkodzony_plik_stanu_nie_wywraca(tmp_path):
    path = tmp_path / "entitlement.json"
    path.write_text("{ to nie jest json", encoding="utf-8")
    clock = _Clock()
    ent = Entitlements(state_path=path, clock=clock)
    assert ent.trial_start_ts() is None
    ent.ensure_started()
    assert ent.is_trial_active()


def test_freemium_limit_to_jeden(tmp_path):
    # Strażnik: zakładamy 1 darmowy produkt na liste.
    assert FREE_PRODUCTS_PER_CATEGORY == 1


# --- moduły funkcyjne (karty) -------------------------------------------
def test_modul_rdzeniowy_zawsze_dostepny(tmp_path):
    clock = _Clock()
    ent = _make(tmp_path, clock)
    ent.ensure_started()
    clock.advance_days(TRIAL_DAYS + 30)
    # Rdzeń (zamrażanie) jest darmowy nawet po wygaśnięciu triala bez PRO.
    assert ent.has_module(CORE_MODULE, pro=False)


def test_modul_platny_dostepny_w_trialu(tmp_path):
    clock = _Clock()
    ent = _make(tmp_path, clock)
    ent.ensure_started()
    # W trakcie triala wszystkie moduły są dostępne.
    assert ent.has_module(MODULE_VALVES, pro=False)


def test_modul_platny_zablokowany_po_trialu(tmp_path):
    clock = _Clock()
    ent = _make(tmp_path, clock)
    ent.ensure_started()
    clock.advance_days(TRIAL_DAYS + 1)
    assert not ent.has_module(MODULE_VALVES, pro=False)


def test_grant_module_odblokowuje_po_trialu(tmp_path):
    clock = _Clock()
    ent = _make(tmp_path, clock)
    ent.ensure_started()
    clock.advance_days(TRIAL_DAYS + 1)
    assert not ent.has_module(MODULE_VALVES, pro=False)
    ent.grant_module(MODULE_VALVES)
    assert ent.has_module(MODULE_VALVES, pro=False)
    # Inny moduł nadal zablokowany.
    assert not ent.has_module(MODULE_INSULATION, pro=False)


def test_pro_nie_odblokowuje_platnych_modulow_automatycznie_ale_has_module_tak(tmp_path):
    # Uwaga projektowa: has_module(pro=True) traktuje PRO jako pełny dostęp.
    clock = _Clock()
    ent = _make(tmp_path, clock)
    ent.ensure_started()
    clock.advance_days(TRIAL_DAYS + 1)
    assert ent.has_module(MODULE_VALVES, pro=True)


def test_modul_jest_trwaly(tmp_path):
    clock = _Clock()
    ent = _make(tmp_path, clock)
    ent.ensure_started()
    clock.advance_days(TRIAL_DAYS + 1)
    ent.grant_module(MODULE_VALVES)
    # Nowa instancja czyta moduł z pliku.
    ent2 = _make(tmp_path, clock)
    assert ent2.has_module(MODULE_VALVES, pro=False)
    assert MODULE_VALVES in ent2.owned_modules()


def test_revoke_module(tmp_path):
    clock = _Clock()
    ent = _make(tmp_path, clock)
    ent.ensure_started()
    clock.advance_days(TRIAL_DAYS + 1)
    ent.grant_module(MODULE_VALVES)
    assert ent.has_module(MODULE_VALVES, pro=False)
    ent.revoke_module(MODULE_VALVES)
    assert not ent.has_module(MODULE_VALVES, pro=False)


def test_sync_modules_ustawia_komplet(tmp_path):
    clock = _Clock()
    ent = _make(tmp_path, clock)
    ent.ensure_started()
    clock.advance_days(TRIAL_DAYS + 1)
    ent.sync_modules([MODULE_VALVES, MODULE_INSULATION])
    assert ent.has_module(MODULE_VALVES, pro=False)
    assert ent.has_module(MODULE_INSULATION, pro=False)
    # Synchronizacja z węższą listą usuwa nieobecne.
    ent.sync_modules([MODULE_VALVES])
    assert ent.has_module(MODULE_VALVES, pro=False)
    assert not ent.has_module(MODULE_INSULATION, pro=False)


def test_stary_plik_bez_modulow_dziala(tmp_path):
    # Wsteczna zgodność: plik zapisany przed wprowadzeniem modułów.
    path = tmp_path / "entitlement.json"
    path.write_text('{"first_launch_ts": 1000000.0}', encoding="utf-8")
    clock = _Clock()
    ent = Entitlements(state_path=path, clock=clock)
    assert ent.trial_start_ts() == 1000000.0
    assert ent.owned_modules() == frozenset()
    assert ent.has_module(CORE_MODULE)


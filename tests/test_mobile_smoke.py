"""Smoke testy warstwy mobilnej — nie wymagają zainstalowanego KivyMD.

Sprawdzamy tylko, że:
  • moduł `tpof.mobile.main` importuje się bez błędu (czysty Python),
  • ścieżki do zasobów są poprawnie skonfigurowane,
  • helper `_safe_image_path` zwraca ścieżkę dla istniejących produktów
    i None dla nieistniejących.
"""
from __future__ import annotations

import importlib
from pathlib import Path

import pytest


def test_mobile_main_importuje_sie():
    module = importlib.import_module("tpof.mobile.main")
    assert hasattr(module, "main")
    assert callable(module.main)


def test_mobilny_wynik_nie_ujawnia_wlasciwosci_produktu():
    source = (
        Path(__file__).parents[1] / "tpof" / "mobile" / "main.py"
    ).read_text(encoding="utf-8")

    assert "self.props_grid" not in source
    assert "lbl_props_title" not in source
    assert "watermark_image_path=None" in source


def test_mobilny_font_ma_fallback_do_kivy():
    from tpof.mobile.main import _runtime_font_path

    assert _runtime_font_path() is not None


def test_przelacznik_podpowiedzi_uzywa_obslugiwanego_trybu_kivymd():
    source = (
        Path(__file__).parents[1] / "tpof" / "mobile" / "main.py"
    ).read_text(encoding="utf-8")

    assert 'helper_text_mode = "none"' not in source
    assert 'field.helper_text_mode = "on_focus"' in source


def test_mobilny_naglowek_uzywa_brandowego_gradientu():
    source = (
        Path(__file__).parents[1] / "tpof" / "mobile" / "main.py"
    ).read_text(encoding="utf-8")

    assert "class BrandToolbar" in source
    assert "class FrostChip" in source
    assert 'text="Refrigeration\\nCalc"' in source
    assert "self.toolbar_snowflake = MDIconButton" in source
    assert "md_bg_color=(0.12, 0.55, 0.86, 1)" not in source


def test_mobilne_wyniki_uzywaja_animowanych_ikon_i_tla_marki():
    source = (
        Path(__file__).parents[1] / "tpof" / "mobile" / "main.py"
    ).read_text(encoding="utf-8")

    assert "class StageMotionIcon" in source
    assert "StageMotionIcon(" in source
    assert "self._position_bands()" in source
    assert "assets/images" in source


def test_mobilne_tlo_ma_stabilna_warstwe_i_nawigacja_nie_zapada_zakladek():
    source = (
        Path(__file__).parents[1] / "tpof" / "mobile" / "main.py"
    ).read_text(encoding="utf-8")

    assert "self._root_bg_color = Color(*SURFACE_DARK)" in source
    assert "self._root_bg_rect = Rectangle" in source
    assert "self.tab_frost_background = FrostBackground" in source
    assert "self.bottom_nav.size_hint_y = 1" not in source
    assert '"bottom_nav_h"' in source
    assert 'self.bottom_nav.height = m["bottom_nav_h"]' in source
    assert "reserved_ad_h = max(64 if compact else 70" in source


def test_mobilne_zakladki_maja_wlasne_animowane_ikony():
    source = (
        Path(__file__).parents[1] / "tpof" / "mobile" / "main.py"
    ).read_text(encoding="utf-8")

    assert "class BottomNavMotionIcon" in source
    assert "class BottomNavTab" in source
    assert "self.bottom_freezing_tab" in source
    assert "self.bottom_valves_tab" in source
    assert "def _show_tab" in source
    assert "tab.play()" in source


def test_jasny_motyw_ma_lodowy_dolny_pasek_zakladek():
    source = (
        Path(__file__).parents[1] / "tpof" / "mobile" / "main.py"
    ).read_text(encoding="utf-8")

    assert "BOTTOM_NAV_BG_LIGHT" in source
    assert "def _bottom_nav_bg" in source
    assert "self.bottom_nav.md_bg_color = self._bottom_nav_bg()" in source
    assert "def set_theme_light" in source
    assert "self.bottom_freezing_tab.set_theme_light" in source
    assert "self.bottom_valves_tab.set_theme_light" in source
    assert "self.bottom_nav.md_bg_color = (0.04, 0.05, 0.07, 1)" not in source


def test_nieaktywna_zakladka_nie_blokuje_dotyku():
    source = (
        Path(__file__).parents[1] / "tpof" / "mobile" / "main.py"
    ).read_text(encoding="utf-8")

    assert "def _set_tab_visibility" in source
    assert "widget.size = (0, 0)" in source
    assert "self._raise_tab_widget(self.scroll if freezing_active else self.valve_scroll)" in source
    assert "host.remove_widget(widget)" in source
    assert "host.add_widget(widget)" in source


def test_mobilna_walidacja_temperatur_chroni_przed_skrajnymi_wartosciami():
    source = (
        Path(__file__).parents[1] / "tpof" / "mobile" / "main.py"
    ).read_text(encoding="utf-8")

    assert "ABSOLUTE_ZERO_C = -273.15" in source
    assert "TEMP_HIGH_ERROR_C = 130.0" in source
    assert "def _validate_temperature_input" in source
    assert "temperature_warning_co2" in source


def test_mobilne_ustawienia_i_lokalizacja_sa_przygotowane():
    root = Path(__file__).parents[1]
    source = (root / "tpof" / "mobile" / "main.py").read_text(encoding="utf-8")
    languages = root / "resources" / "strings" / "languages.json"

    assert "def _open_settings_dialog" in source
    assert "self.toolbar_snowflake = MDIconButton" in source
    assert "on_release=lambda *_: self._open_settings_dialog()" in source
    assert "units_imperial_disabled" in source
    assert "for _fallback_lang in (\"es\", \"fr\", \"it\", \"pt\", \"ja\", \"zh\")" in source
    assert languages.exists()


def test_mobilne_komunikaty_walidacji_sa_centralne_i_zanikaja():
    source = (
        Path(__file__).parents[1] / "tpof" / "mobile" / "main.py"
    ).read_text(encoding="utf-8")

    assert "class CenterNotice" in source
    assert "self.center_notice = CenterNotice()" in source
    assert "notice.show(message)" in source
    assert "Animation(opacity=1, d=1.5) + Animation(opacity=0, d=0.5)" in source
    assert '"center_y": 0.54' in source
    assert "def _hide_after_fade" in source
    assert "self.size = (0, 0)" in source


def test_mobilna_lista_ukrywa_wylacznie_techniczne_rekordy_ctp():
    from tpof.core import list_products, load_products
    from tpof.mobile.main import _mobile_product_names
    from tpof.mobile.paths import DATA_PATH

    catalog = load_products(DATA_PATH)
    desktop_names = list_products(catalog, "różne")
    mobile_names = _mobile_product_names(catalog, "różne")

    assert any(name.casefold().endswith("_ctp aldi") for name in desktop_names)
    assert not any(name.casefold().endswith("_ctp aldi") for name in mobile_names)
    assert set(mobile_names).issubset(desktop_names)


def test_mobilny_filtr_nie_ukrywa_ctp_w_innych_kategoriach():
    from tpof.core import Product
    from tpof.mobile.main import _mobile_product_names

    product = Product("Test_CTP ALDI", "warzywa", 1, 1, 1, 1, 1)
    assert _mobile_product_names({"warzywa": [product]}, "warzywa") == [
        product.nazwa
    ]


def test_kolejnosc_kategorii_mobilnych_ma_wyrozniony_poczatek():
    from tpof.mobile.main import _ordered_mobile_categories

    featured, remaining = _ordered_mobile_categories(
        ["ryby", "warzywa", "owoce", "drób", "sery"]
    )

    assert featured == ["owoce", "warzywa"]
    assert remaining == ["drób", "ryby", "sery"]


def test_wyszukiwanie_produktow_ignoruje_polskie_znaki_i_wielkosc_liter():
    from tpof.mobile.main import _search_product_names

    names = ["Śliwki suszone", "Mleko", "Łosoś", "Śliwki świeże"]

    assert _search_product_names(names, "SLIWKI") == [
        "Śliwki suszone",
        "Śliwki świeże",
    ]
    assert _search_product_names(names, "losos") == ["Łosoś"]


def test_wyszukiwanie_produktow_preferuje_poczatek_nazwy():
    from tpof.mobile.main import _search_product_names

    names = ["Brzoskwinie suszone", "Suszone morele", "Morele suszone"]

    assert _search_product_names(names, "morele") == [
        "Morele suszone",
        "Suszone morele",
    ]


def test_paths_wskazuja_na_istniejace_zasoby():
    from tpof.mobile.paths import DATA_PATH, IMAGES_DIR

    assert DATA_PATH.exists(), f"Brak bazy danych: {DATA_PATH}"
    assert IMAGES_DIR.exists(), f"Brak katalogu obrazów: {IMAGES_DIR}"


def test_safe_image_path_dla_istniejacego_produktu():
    from tpof.mobile.main import _safe_image_path

    # W assets/images jest "Banany.webp"
    path = _safe_image_path("Banany")
    assert path is not None
    assert path.endswith(".webp")


def test_safe_image_path_dla_nieistniejacego():
    from tpof.mobile.main import _safe_image_path

    assert _safe_image_path("NieistniejacyProdukt_12345") is None


def test_sync_module_ownership_nadaje_modul(tmp_path):
    from tpof.mobile.entitlements import MODULE_VALVES, Entitlements
    from tpof.mobile.main import _sync_module_ownership

    ent = Entitlements(state_path=tmp_path / "entitlement.json")
    _sync_module_ownership(ent, MODULE_VALVES, True)
    assert MODULE_VALVES in ent.owned_modules()


def test_sync_module_ownership_cofa_modul_po_revoke(tmp_path):
    from tpof.mobile.entitlements import MODULE_VALVES, Entitlements
    from tpof.mobile.main import _sync_module_ownership

    ent = Entitlements(state_path=tmp_path / "entitlement.json")
    ent.grant_module(MODULE_VALVES)
    _sync_module_ownership(ent, MODULE_VALVES, False)
    assert MODULE_VALVES not in ent.owned_modules()


def test_pdf_output_dir_na_desktopie_zwraca_cwd():
    from tpof.mobile.main import _pdf_output_dir

    out = _pdf_output_dir()
    assert out.exists()
    assert out.is_dir()


def test_main_bez_kivymd_rzuca_systemexit(monkeypatch):
    """Gdy KivyMD nie jest dostępne, main() powinien zakończyć się czytelnym SystemExit."""
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name.startswith("kivymd") or name.startswith("kivy"):
            raise ImportError(f"symulowany brak: {name}")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    from tpof.mobile.main import main

    with pytest.raises(SystemExit) as exc_info:
        main()
    assert "KivyMD" in str(exc_info.value)

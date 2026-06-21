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


def test_przelacznik_podpowiedzi_uzywa_obslugiwanego_trybu_kivymd():
    source = (
        Path(__file__).parents[1] / "tpof" / "mobile" / "main.py"
    ).read_text(encoding="utf-8")

    assert 'helper_text_mode = "none"' not in source
    assert 'field.helper_text_mode = "on_focus"' in source


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

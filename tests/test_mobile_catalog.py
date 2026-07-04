"""Behavior tests for mobile catalog helpers."""
from __future__ import annotations


def test_mobilna_lista_ukrywa_wylacznie_techniczne_rekordy_ctp():
    from tpof.core import list_products, load_products
    from tpof.mobile.catalog import _mobile_product_names
    from tpof.mobile.paths import DATA_PATH

    catalog = load_products(DATA_PATH)
    desktop_names = list_products(catalog, "różne")
    mobile_names = _mobile_product_names(catalog, "różne")

    assert any(name.casefold().endswith("_ctp aldi") for name in desktop_names)
    assert not any(name.casefold().endswith("_ctp aldi") for name in mobile_names)
    assert set(mobile_names).issubset(desktop_names)


def test_mobilny_filtr_nie_ukrywa_ctp_w_innych_kategoriach():
    from tpof.core import Product
    from tpof.mobile.catalog import _mobile_product_names

    product = Product("Test_CTP ALDI", "warzywa", 1, 1, 1, 1, 1)
    assert _mobile_product_names({"warzywa": [product]}, "warzywa") == [
        product.nazwa
    ]


def test_kolejnosc_kategorii_mobilnych_ma_wyrozniony_poczatek():
    from tpof.mobile.catalog import _ordered_mobile_categories

    featured, remaining = _ordered_mobile_categories(
        ["ryby", "warzywa", "owoce", "drób", "sery"]
    )

    assert featured == ["owoce", "warzywa"]
    assert remaining == ["drób", "ryby", "sery"]


def test_safe_image_path_dla_istniejacego_produktu():
    from tpof.mobile.catalog import _safe_image_path

    # W assets/images jest "Banany.webp".
    path = _safe_image_path("Banany")
    assert path is not None
    assert path.endswith(".webp")


def test_safe_image_path_dla_nieistniejacego():
    from tpof.mobile.catalog import _safe_image_path

    assert _safe_image_path("NieistniejacyProdukt_12345") is None

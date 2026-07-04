"""Behavior tests for the mobile i18n translation layer."""
from __future__ import annotations

from tpof.mobile.i18n import I18N, display_category, translate


def test_translate_zwraca_jezyk_pl_i_en():
    assert translate("pl", "product") == "Produkt"
    assert translate("en", "product") == "Product"


def test_translate_nieznany_jezyk_uzywa_polskiego():
    assert translate("xx", "product") == translate("pl", "product")


def test_translate_jezyki_fallback_uzywaja_angielskiego():
    for lang in ("es", "fr", "it", "pt", "ja", "zh"):
        assert translate(lang, "product") == translate("en", "product")


def test_translate_brakujacy_klucz_zwraca_sam_klucz():
    assert translate("pl", "__nieistniejacy_klucz__") == "__nieistniejacy_klucz__"
    assert translate("en", "__nieistniejacy_klucz__") == "__nieistniejacy_klucz__"


def test_translate_interpoluje_parametry():
    text = translate("pl", "custom_product_limit", limit=250)
    assert "250" in text
    assert "{limit}" not in text


def test_translate_bez_kwargs_zostawia_surowy_szablon():
    # Bez kwargs szablon nie jest formatowany (zachowanie 1:1 z dawnego _t).
    assert translate("pl", "custom_product_limit") == I18N["pl"]["custom_product_limit"]


def test_display_category_en_mapuje_a_pl_zostawia():
    assert display_category("en", "owoce") == "fruit"
    assert display_category("en", "różne") == "miscellaneous"
    assert display_category("pl", "owoce") == "owoce"


def test_display_category_pusty_i_nieznany():
    assert display_category("en", "") == ""
    assert display_category("pl", None) == ""
    assert display_category("en", "nieznana_kategoria") == "nieznana kategoria"

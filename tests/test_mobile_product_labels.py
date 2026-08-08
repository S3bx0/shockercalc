"""Coverage and behavior guards for localized product labels."""

from __future__ import annotations


def test_all_visible_mobile_products_have_english_labels():
    from tpof.core import load_products
    from tpof.mobile.catalog import _is_mobile_hidden_product
    from tpof.mobile.paths import DATA_PATH
    from tpof.mobile.product_labels import PRODUCT_LABELS_EN

    catalog = load_products(DATA_PATH)
    visible_names = {
        product.nazwa
        for category, products in catalog.items()
        for product in products
        if not _is_mobile_hidden_product(category, product.nazwa)
    }

    assert visible_names - PRODUCT_LABELS_EN.keys() == set()


def test_display_product_changes_only_the_english_label():
    from tpof.mobile.product_labels import display_product

    assert display_product("pl", "Wiśnie słodkie") == "Wiśnie słodkie"
    assert display_product("en", "Wiśnie słodkie") == "Sweet cherries"
    assert display_product("en", "Własny produkt") == "Własny produkt"
    assert display_product("en", None) == ""

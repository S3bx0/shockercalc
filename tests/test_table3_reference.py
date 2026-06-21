from __future__ import annotations

from tpof.core import find_product, load_products
from tpof.mobile.paths import DATA_PATH


def test_table3_zawiera_uzupelnione_produkty_ashrae():
    catalog = load_products(DATA_PATH)
    expected = {
        "warzywa": {
            "Bataty",
            "Chrzan",
            "Czosnek",
            "Kapusta liściasta",
            "Seler korzeniowy",
            "Seler naciowy",
        },
        "owoce": {"Cytryny", "Porzeczki czerwone i białe"},
    }

    for category, names in expected.items():
        available = {product.nazwa for product in catalog[category]}
        assert names <= available


def test_table3_nie_ma_zduplikowanych_nazw_w_kategorii():
    catalog = load_products(DATA_PATH)

    for category, products in catalog.items():
        names = [product.nazwa for product in products]
        assert len(names) == len(set(names)), f"Duplikat w kategorii {category}"


def test_poprawione_rekordy_maja_wartosci_z_tabeli_ashrae():
    catalog = load_products(DATA_PATH)

    broccoli = find_product(catalog, "warzywa", "Brokuły")
    beets = find_product(catalog, "warzywa", "Buraki")
    leeks = find_product(catalog, "warzywa", "Pory")
    salted_yolk = find_product(catalog, "jajka", "Żółtko solone")

    assert broccoli is not None and (broccoli.popiol, broccoli.c1, broccoli.c2, broccoli.L1) == (
        0.92,
        4.01,
        1.82,
        303.0,
    )
    assert beets is not None and (beets.popiol, beets.c1, beets.c2, beets.L1) == (
        1.08,
        3.91,
        1.94,
        293.0,
    )
    assert leeks is not None and (leeks.wodaprocent, leeks.c1, leeks.c2, leeks.L1) == (
        83.0,
        3.77,
        1.91,
        277.0,
    )
    assert salted_yolk is not None and salted_yolk.tluszcz == 23.0


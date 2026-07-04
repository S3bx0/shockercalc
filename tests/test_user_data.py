import json

import pytest

from tpof.mobile.user_data import (
    CustomProductStore,
    UiPreferences,
    create_custom_product,
)
from tpof.mobile.validation import _numeric_input_filter


VALID_PRODUCT = {
    "nazwa": "Produkt testowy",
    "kategoria": "Moje produkty",
    "wilgotnosc": "72,5",
    "bialko": "12",
    "tluszcz": "4",
    "weglowodany": "8",
    "blonnik": "2",
    "popiol": "1",
    "t_zam": "-1,2",
    "c1": "3,7",
    "c2": "1,9",
    "l1": "240",
}


def test_hints_are_enabled_by_default_and_persist(tmp_path):
    path = tmp_path / "preferences.json"
    preferences = UiPreferences(path)

    assert preferences.hints_enabled is True
    preferences.set_hints_enabled(False)

    assert UiPreferences(path).hints_enabled is False


def test_unit_system_defaults_to_metric_and_persists(tmp_path):
    path = tmp_path / "preferences.json"
    preferences = UiPreferences(path)

    assert preferences.unit_system == "metric"
    preferences.set_unit_system("imperial")

    assert UiPreferences(path).unit_system == "metric"


@pytest.mark.parametrize("stored_value", ["imperial", "us", "unknown"])
def test_unit_system_file_values_fallback_to_metric(tmp_path, stored_value):
    path = tmp_path / "preferences.json"
    path.write_text(json.dumps({"unit_system": stored_value}), encoding="utf-8")

    assert UiPreferences(path).unit_system == "metric"


def test_labor_rate_values_persist_and_reset(tmp_path):
    path = tmp_path / "preferences.json"
    preferences = UiPreferences(path)

    preferences.set_labor_rate_values(
        {"labor_hourly_rate": "222", "workdays_per_week": "6"}
    )

    restored = UiPreferences(path)
    assert restored.labor_rate_values["labor_hourly_rate"] == "222"
    assert restored.labor_rate_values["workdays_per_week"] == "6"

    restored.reset_labor_rate_values()

    assert UiPreferences(path).labor_rate_values["labor_hourly_rate"] == "130.0"
    assert UiPreferences(path).labor_rate_values["workdays_per_week"] == "5"


def test_recent_products_are_deduplicated_limited_and_persisted(tmp_path):
    path = tmp_path / "preferences.json"
    preferences = UiPreferences(path)

    preferences.add_recent_product("owoce", "Banany", limit=3)
    preferences.add_recent_product("warzywa", "Brokuły", limit=3)
    preferences.add_recent_product("owoce", "Ananas", limit=3)
    preferences.add_recent_product("owoce", "Banany", limit=3)

    restored = UiPreferences(path)
    assert restored.recent_products == [
        ("owoce", "Banany"),
        ("owoce", "Ananas"),
        ("warzywa", "Brokuły"),
    ]
    assert restored.recent_products_for_category(
        "OWOCE", ["Ananas", "Banany", "Arbuz"]
    ) == ["Banany", "Ananas"]


def test_recent_products_ignore_missing_catalog_entries(tmp_path):
    preferences = UiPreferences(tmp_path / "preferences.json")
    preferences.add_recent_product("owoce", "Usunięty produkt")

    assert preferences.recent_products_for_category("owoce", ["Banany"]) == []


def test_numeric_filter_accepts_polish_decimal_comma_and_minus():
    assert _numeric_input_filter("-12,5 kg") == "-12,5"


def test_custom_product_uses_decimal_comma_and_normalizes_category():
    product = create_custom_product(VALID_PRODUCT)

    assert product.kategoria == "moje_produkty"
    assert product.wodaprocent == 72.5
    assert product.T_zam == -1.2
    assert product.c1 == 3.7


def test_custom_product_category_normalization_strips_diacritics():
    product = create_custom_product(dict(VALID_PRODUCT, kategoria="Drób i mięso"))

    assert product.kategoria == "drob_i_mieso"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("nazwa", ""),
        ("kategoria", ""),
        ("wilgotnosc", "101"),
        ("c1", "0"),
        ("c2", "bad"),
        ("l1", "-1"),
        ("t_zam", "-90"),
        ("t_zam", "20"),
        ("bialko", "-1"),
    ],
)
def test_custom_product_rejects_invalid_required_values(field, value):
    data = dict(VALID_PRODUCT)
    data[field] = value

    with pytest.raises(ValueError, match=field):
        create_custom_product(data)


def test_custom_product_rejects_macro_sum_above_100_percent():
    data = dict(
        VALID_PRODUCT,
        bialko="40",
        tluszcz="30",
        weglowodany="20",
        blonnik="8",
        popiol="5",
    )

    with pytest.raises(ValueError, match="makroskladniki"):
        create_custom_product(data)


def test_store_upserts_and_merges_products(tmp_path):
    path = tmp_path / "custom_products.json"
    store = CustomProductStore(path)
    product = create_custom_product(VALID_PRODUCT)
    store.upsert(product)

    changed = dict(VALID_PRODUCT, c1="4.1")
    store.upsert(create_custom_product(changed))

    catalog = {}
    store.merge_into(catalog)

    assert len(catalog["moje_produkty"]) == 1
    assert catalog["moje_produkty"][0].c1 == 4.1
    assert store.contains("Moje produkty", "produkt TESTOWY") is True
    assert store.contains("Moje produkty", "inny produkt") is False
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw["zywnosc"]["moje_produkty"][0]["nazwa"] == "Produkt testowy"


def test_store_cache_is_invalidated_after_upsert(tmp_path):
    path = tmp_path / "custom_products.json"
    store = CustomProductStore(path)

    assert store.count() == 0
    store.upsert(create_custom_product(VALID_PRODUCT))

    assert store.count() == 1

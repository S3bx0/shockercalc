import json
from decimal import Decimal
from http.client import BadStatusLine, IncompleteRead

import pytest

from tpof.mobile.currency import (
    NBP_RATE_URL,
    ExchangeRates,
    convert_display_amount,
    convert_display_amount_to_pln,
    fetch_nbp_exchange_rates,
    format_exchange_rate,
    format_money,
    get_exchange_rates,
    load_cached_rates,
    save_cached_rates,
)


def test_nbp_endpoint_requires_https():
    assert NBP_RATE_URL.startswith("https://")
    assert not NBP_RATE_URL.startswith("http://")


def test_fetch_nbp_exchange_rates_uses_injected_fetcher():
    def fetcher(code):
        mid = "4.25" if code == "EUR" else "3.90"
        return {"code": code, "rates": [{"effectiveDate": "2026-07-06", "mid": mid}]}

    rates = fetch_nbp_exchange_rates(fetcher=fetcher)

    assert rates.rate_for("EUR") == Decimal("4.25")
    assert rates.rate_for("USD") == Decimal("3.90")
    assert rates.date == "2026-07-06"
    assert rates.from_cache is False


def test_currency_cache_roundtrip(tmp_path):
    path = tmp_path / "exchange_rates.json"
    save_cached_rates(
        path,
        ExchangeRates(
            {"PLN": Decimal("1"), "EUR": Decimal("4.25"), "USD": Decimal("3.90")},
            date="2026-07-06",
        ),
    )

    loaded = load_cached_rates(path)

    assert loaded is not None
    assert loaded.rate_for("EUR") == Decimal("4.25")
    assert loaded.date == "2026-07-06"
    assert loaded.from_cache is True


def test_get_exchange_rates_falls_back_to_cache_after_fetch_error(tmp_path):
    path = tmp_path / "exchange_rates.json"
    save_cached_rates(
        path,
        ExchangeRates(
            {"PLN": Decimal("1"), "EUR": Decimal("4.10"), "USD": Decimal("3.80")},
            date="2026-07-05",
        ),
    )

    def fetcher(_code):
        raise OSError("offline")

    rates = get_exchange_rates(path, fetcher=fetcher)

    assert rates.rate_for("EUR") == Decimal("4.10")
    assert rates.date == "2026-07-05"
    assert rates.from_cache is True


def test_format_money_is_only_a_presentation_conversion():
    rates = ExchangeRates(
        {"PLN": Decimal("1"), "EUR": Decimal("4"), "USD": Decimal("2")},
        date="2026-07-06",
    )
    original = Decimal("40")

    assert format_money(original, "PLN", rates, "pl") == "40,00 zł"
    assert format_money(original, "EUR", rates, "pl") == "10,00 EUR"
    assert format_money(original, "USD", rates, "en") == "20.00 USD"
    assert original == Decimal("40")


def test_format_exchange_rate_shows_pln_per_unit_for_settings_card():
    rates = ExchangeRates(
        {"PLN": Decimal("1"), "EUR": Decimal("4.2519"), "USD": Decimal("3.905")}
    )

    assert format_exchange_rate("PLN", rates, "pl") == "1 PLN = 1,0000 PLN"
    assert format_exchange_rate("EUR", rates, "pl") == "1 EUR = 4,2519 PLN"
    assert format_exchange_rate("USD", rates, "en") == "1 USD = 3.9050 PLN"
    assert format_exchange_rate("GBP", rates, "en") is None
    assert format_exchange_rate("EUR", ExchangeRates({"PLN": Decimal("1")}), "en") is None


def test_display_amount_is_converted_to_internal_pln():
    rates = ExchangeRates(
        {"PLN": Decimal("1"), "EUR": Decimal("4.25"), "USD": Decimal("3.40")},
        date="2026-07-10",
    )

    assert convert_display_amount_to_pln(Decimal("10"), "EUR", rates) == Decimal("42.50")
    assert convert_display_amount(Decimal("10"), "EUR", "USD", rates) == Decimal("12.50")


def test_display_amount_conversion_requires_requested_rate():
    rates = ExchangeRates({"PLN": Decimal("1")})

    try:
        convert_display_amount_to_pln(Decimal("10"), "EUR", rates)
    except ValueError as exc:
        assert "EUR" in str(exc)
    else:
        raise AssertionError("missing exchange rate should fail")


@pytest.mark.parametrize("value", ["NaN", "sNaN", "Infinity", "-Infinity", "0", "-1", True, None, [], {}])
def test_invalid_rates_are_rejected_from_network_and_cache(tmp_path, value):
    def fetcher(code):
        return {"code": code, "rates": [{"mid": value, "effectiveDate": "2026-09-04"}]}

    with pytest.raises(ValueError):
        fetch_nbp_exchange_rates(fetcher=fetcher)
    path = tmp_path / "rates.json"
    path.write_text(json.dumps({
        "date": "2026-09-04", "rates": {"PLN": "1", "EUR": value, "USD": "3.90"},
    }))
    assert load_cached_rates(path) is None


@pytest.mark.parametrize("value", ["NaN", "sNaN", "Infinity", "-Infinity", "0", "-1"])
def test_rate_lookup_does_not_leak_nonfinite_values_to_formatters(value):
    rates = ExchangeRates({"EUR": Decimal(value)})
    assert rates.rate_for("EUR") is None
    assert format_money(40, "EUR", rates, "en") == "40.00 PLN"


@pytest.mark.parametrize("payload", [[], None, "rates", {}, {"rates": []}, {"rates": None}])
def test_invalid_cache_shapes_are_ignored(tmp_path, payload):
    path = tmp_path / "rates.json"
    path.write_text(json.dumps(payload))
    assert load_cached_rates(path) is None
    assert get_exchange_rates(path, auto_update=False).rate_for("EUR") is None


@pytest.mark.parametrize("date", [None, [], 20260904, "", "yesterday", "2026-02-30", "20260904", "2026-09-04T00:00:00"])
def test_invalid_rate_dates_are_rejected_from_network_and_cache(tmp_path, date):
    with pytest.raises(ValueError):
        fetch_nbp_exchange_rates(fetcher=lambda code: {
            "code": code, "rates": [{"mid": "4.25", "effectiveDate": date}],
        })
    path = tmp_path / "rates.json"
    path.write_text(json.dumps({
        "date": date, "rates": {"PLN": "1", "EUR": "4.25", "USD": "3.90"},
    }))
    assert load_cached_rates(path) is None


@pytest.mark.parametrize("payload", [
    [], None, {}, {"code": "USD", "rates": [{"mid": "4.25", "effectiveDate": "2026-09-04"}]},
    {"code": "EUR", "rates": []}, {"code": "EUR", "rates": [None]},
    {"code": "EUR", "rates": {}},
])
def test_nbp_requires_matching_currency_code_and_rate_shape(payload):
    with pytest.raises(ValueError):
        fetch_nbp_exchange_rates(fetcher=lambda _code: payload)


def test_positive_rates_are_not_limited_to_arbitrary_market_range(tmp_path):
    rates = fetch_nbp_exchange_rates(fetcher=lambda code: {
        "code": code,
        "rates": [{"mid": "0.25" if code == "EUR" else "12.5", "effectiveDate": "2026-09-04"}],
    })
    path = tmp_path / "rates.json"
    save_cached_rates(path, rates)
    cached = load_cached_rates(path)
    assert cached is not None
    assert cached.rate_for("EUR") == Decimal("0.25")
    assert cached.rate_for("USD") == Decimal("12.5")


@pytest.mark.parametrize("error", [IncompleteRead(b"partial"), BadStatusLine("invalid"), ValueError("bad response")])
def test_failed_or_partial_network_fetch_keeps_valid_cache(tmp_path, error):
    path = tmp_path / "rates.json"
    save_cached_rates(path, ExchangeRates(
        {"PLN": Decimal(1), "EUR": Decimal("4.1"), "USD": Decimal("3.8")}, date="2026-09-03",
    ))
    previous = path.read_bytes()

    def fetcher(code):
        if code == "USD":
            raise error
        return {"code": code, "rates": [{"mid": "4.25", "effectiveDate": "2026-09-04"}]}

    rates = get_exchange_rates(path, fetcher=fetcher)
    assert rates.from_cache and rates.rate_for("EUR") == Decimal("4.1")
    assert path.read_bytes() == previous


def test_invalid_snapshot_cannot_overwrite_valid_cache(tmp_path):
    path = tmp_path / "rates.json"
    save_cached_rates(path, ExchangeRates(
        {"PLN": Decimal(1), "EUR": Decimal("4.1"), "USD": Decimal("3.8")}, date="2026-09-03",
    ))
    previous = path.read_bytes()
    with pytest.raises(ValueError):
        save_cached_rates(path, ExchangeRates({"PLN": Decimal(1)}))
    assert path.read_bytes() == previous


def test_cache_cannot_change_base_currency(tmp_path):
    path = tmp_path / "rates.json"
    path.write_text(json.dumps({
        "date": "2026-09-04", "rates": {"PLN": "2", "EUR": "4.25", "USD": "3.90"},
    }))
    assert load_cached_rates(path) is None

from decimal import Decimal

from tpof.mobile.currency import (
    ExchangeRates,
    fetch_nbp_exchange_rates,
    format_money,
    get_exchange_rates,
    load_cached_rates,
    save_cached_rates,
)


def test_fetch_nbp_exchange_rates_uses_injected_fetcher():
    def fetcher(code):
        mid = "4.25" if code == "EUR" else "3.90"
        return {"rates": [{"effectiveDate": "2026-07-06", "mid": mid}]}

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

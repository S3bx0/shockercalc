import json
from decimal import Decimal

import pytest

from tpof.mobile.currency import (
    CACHE_MAX_AGE_S,
    ExchangeRates,
    get_exchange_rates,
    load_cached_rates,
    save_cached_rates,
)


def _cache(tmp_path, fetched_at=100_000):
    path = tmp_path / "exchange_rates.json"
    save_cached_rates(path, ExchangeRates(
        {"PLN": Decimal(1), "EUR": Decimal("4.2"), "USD": Decimal("3.9")},
        date="2026-09-04", fetched_at=fetched_at,
    ))
    return path


def _fetcher(calls):
    def fetch(code):
        calls.append(code)
        return {"code": code, "rates": [{"effectiveDate": "2026-09-04", "mid": "4.25"}]}
    return fetch


@pytest.mark.parametrize("age", [0, 1, 6 * 3600 - 1])
def test_fresh_download_is_reused_without_network(tmp_path, age):
    path = _cache(tmp_path)
    original = path.read_bytes()
    calls = []
    rates = get_exchange_rates(path, fetcher=_fetcher(calls), now=lambda: 100_000 + age)
    assert calls == []
    assert rates.from_cache and rates.fetched_at == 100_000
    assert rates.rate_for("EUR") == Decimal("4.2")
    assert path.read_bytes() == original  # Reading must not extend the TTL.


@pytest.mark.parametrize("age", [-1, 6 * 3600, 10 * 3600])
def test_expired_or_future_download_is_refreshed(tmp_path, age):
    path = _cache(tmp_path)
    calls = []
    rates = get_exchange_rates(path, fetcher=_fetcher(calls), now=lambda: 100_000 + age)
    assert calls == ["EUR", "USD"]
    assert not rates.from_cache
    assert rates.fetched_at == 100_000 + age
    assert load_cached_rates(path).fetched_at == rates.fetched_at


@pytest.mark.parametrize("stamp", [None, "100000", True, [], {}, -1, float("nan"), float("inf"), 10**400])
def test_invalid_timestamp_keeps_rates_available_but_stale(tmp_path, stamp):
    path = _cache(tmp_path)
    payload = json.loads(path.read_text())
    payload["fetched_at"] = stamp
    path.write_text(json.dumps(payload))
    cached = load_cached_rates(path)
    assert cached is not None and cached.fetched_at is None
    assert cached.rate_for("EUR") == Decimal("4.2")
    calls = []
    get_exchange_rates(path, fetcher=_fetcher(calls), now=lambda: 100_000)
    assert calls == ["EUR", "USD"]


def test_legacy_cache_without_timestamp_is_migrated_on_success(tmp_path):
    path = _cache(tmp_path)
    payload = json.loads(path.read_text())
    del payload["fetched_at"]
    path.write_text(json.dumps(payload))
    calls = []
    rates = get_exchange_rates(path, fetcher=_fetcher(calls), now=lambda: 200_000)
    assert calls == ["EUR", "USD"]
    assert rates.date == "2026-09-04"  # Effective date is not the TTL clock.
    assert json.loads(path.read_text())["fetched_at"] == 200_000


def test_timestamp_records_completed_download_not_start(tmp_path):
    clock = iter([200_000, 200_010])
    calls = []
    rates = get_exchange_rates(_cache(tmp_path), fetcher=_fetcher(calls), now=lambda: next(clock))
    assert rates.fetched_at == 200_010


def test_manual_force_bypasses_fresh_cache(tmp_path):
    calls = []
    rates = get_exchange_rates(_cache(tmp_path), force=True, fetcher=_fetcher(calls), now=lambda: 100_001)
    assert calls == ["EUR", "USD"]
    assert rates.fetched_at == 100_001


@pytest.mark.parametrize("has_cache", [False, True])
def test_disabled_updates_never_download_even_when_forced(tmp_path, has_cache):
    path = _cache(tmp_path) if has_cache else tmp_path / "missing.json"
    calls = []
    rates = get_exchange_rates(path, auto_update=False, force=True, fetcher=_fetcher(calls))
    assert calls == []
    assert rates.from_cache is has_cache


@pytest.mark.parametrize("force", [False, True])
def test_offline_fallback_does_not_rejuvenate_cache(tmp_path, force):
    path = _cache(tmp_path)
    original = path.read_bytes()

    def offline(_code):
        raise OSError("offline")

    rates = get_exchange_rates(path, force=force, fetcher=offline, now=lambda: 200_000)
    assert rates.from_cache and rates.fetched_at == 100_000
    assert path.read_bytes() == original


def test_custom_ttl_can_expire_cache_before_default_six_hours(tmp_path):
    assert CACHE_MAX_AGE_S == 6 * 3600
    calls = []
    get_exchange_rates(_cache(tmp_path), max_age_s=5, fetcher=_fetcher(calls), now=lambda: 100_005)
    assert calls == ["EUR", "USD"]

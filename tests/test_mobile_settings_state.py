from __future__ import annotations

from decimal import Decimal
from http.client import IncompleteRead

import pytest

from tpof.mobile.currency import ExchangeRates
from tpof.mobile.settings_state import SettingsStateController
from tpof.mobile.user_data import UiPreferences


def _translate(key: str, **values: object) -> str:
    suffix = ",".join(f"{name}={value}" for name, value in sorted(values.items()))
    return f"{key}:{suffix}" if suffix else key


def _controller(
    tmp_path,
    *,
    prepare_preferences=None,
    load_exchange_rates=None,
    run_background_immediately: bool = False,
):
    preferences = UiPreferences(tmp_path / "preferences.json")
    if prepare_preferences is not None:
        prepare_preferences(preferences)

    ui_refreshes: list[bool] = []
    labor_conversions: list[str] = []
    labor_refreshes: list[bool] = []
    messages: list[str] = []
    scheduled: list[tuple[object, float]] = []
    background: list[object] = []

    def schedule_once(callback, delay):
        scheduled.append((callback, delay))
        return object()

    def start_background(callback):
        background.append(callback)
        if run_background_immediately:
            callback()

    kwargs = {}
    if load_exchange_rates is not None:
        kwargs["load_exchange_rates"] = load_exchange_rates

    controller = SettingsStateController(
        preferences=preferences,
        translate=_translate,
        refresh_settings_ui=lambda: ui_refreshes.append(True),
        convert_labor_currency=labor_conversions.append,
        refresh_labor_results=lambda: labor_refreshes.append(True),
        show_message=messages.append,
        schedule_once=schedule_once,
        start_background=start_background,
        **kwargs,
    )
    return {
        "controller": controller,
        "preferences": preferences,
        "ui_refreshes": ui_refreshes,
        "labor_conversions": labor_conversions,
        "labor_refreshes": labor_refreshes,
        "messages": messages,
        "scheduled": scheduled,
        "background": background,
    }


def test_settings_state_restores_persisted_values_and_cache_path(tmp_path):
    def prepare(preferences):
        preferences.set_display_currency("EUR")
        preferences.set_currency_auto_update(False)

    state = _controller(tmp_path, prepare_preferences=prepare)
    controller = state["controller"]

    assert controller.unit_system == "metric"
    assert controller.display_currency == "EUR"
    assert controller.currency_auto_update is False
    assert controller.cache_path == tmp_path / "exchange_rates.json"


def test_imperial_units_remain_disabled_until_conversion_exists(tmp_path):
    state = _controller(tmp_path)
    controller = state["controller"]

    assert controller.set_unit_system("imperial") is False
    assert controller.unit_system == "metric"
    assert state["messages"] == ["units_imperial_disabled"]

    assert controller.set_unit_system("metric") is True
    assert state["messages"][-1] == "units_metric_active"
    assert UiPreferences(tmp_path / "preferences.json").unit_system == "metric"


def test_invalid_currency_falls_back_to_pln_without_network_refresh(tmp_path):
    state = _controller(tmp_path)
    controller = state["controller"]

    assert controller.set_display_currency("GBP") == "PLN"

    assert controller.display_currency == "PLN"
    assert state["labor_conversions"] == ["PLN"]
    assert len(state["ui_refreshes"]) == 1
    assert len(state["labor_refreshes"]) == 1
    assert state["background"] == []
    assert UiPreferences(tmp_path / "preferences.json").display_currency == "PLN"


def test_currency_change_preserves_conversion_order_and_applies_async_rates(tmp_path):
    rates = ExchangeRates(
        {
            "PLN": Decimal("1"),
            "EUR": Decimal("4.25"),
            "USD": Decimal("3.90"),
        },
        date="2026-07-27",
    )
    load_calls = []

    def load_rates(path, *, auto_update, force=False):
        load_calls.append((path, auto_update))
        return rates

    state = _controller(
        tmp_path,
        load_exchange_rates=load_rates,
        run_background_immediately=True,
    )
    controller = state["controller"]
    previous_currencies = []
    original_convert = controller._convert_labor_currency

    def capture_conversion(target):
        previous_currencies.append((controller.display_currency, target))
        original_convert(target)

    controller._convert_labor_currency = capture_conversion

    assert controller.set_display_currency("eur") == "EUR"

    assert previous_currencies == [("PLN", "EUR")]
    assert controller.display_currency == "EUR"
    assert controller.refresh_running is True
    assert load_calls == [(tmp_path / "exchange_rates.json", True)]
    assert len(state["scheduled"]) == 1

    callback, delay = state["scheduled"][0]
    assert delay == 0
    callback()

    assert previous_currencies == [("PLN", "EUR"), ("EUR", "EUR")]
    assert controller.refresh_running is False
    assert controller.exchange_rates == rates
    assert state["messages"][-1].startswith("labor_currency_note_rate:")


def test_duplicate_online_refresh_is_ignored_while_worker_is_running(tmp_path):
    state = _controller(tmp_path)
    controller = state["controller"]

    assert controller.refresh_exchange_rates_async() is True
    assert controller.refresh_running is True
    assert controller.refresh_exchange_rates_async() is False

    assert len(state["background"]) == 1
    assert len(state["ui_refreshes"]) == 1


def test_disabling_auto_update_loads_cache_synchronously(tmp_path):
    cached = ExchangeRates(
        {
            "PLN": Decimal("1"),
            "EUR": Decimal("4.20"),
            "USD": Decimal("3.80"),
        },
        date="2026-07-26",
        from_cache=True,
    )
    load_calls = []

    def load_rates(path, *, auto_update, force=False):
        load_calls.append((path, auto_update))
        return cached

    state = _controller(tmp_path, load_exchange_rates=load_rates)
    controller = state["controller"]

    assert controller.toggle_currency_auto_update() is False

    assert controller.currency_auto_update is False
    assert controller.exchange_rates == cached
    assert load_calls == [(tmp_path / "exchange_rates.json", False)]
    assert state["background"] == []
    assert len(state["ui_refreshes"]) == 2
    assert len(state["labor_refreshes"]) == 1
    assert UiPreferences(tmp_path / "preferences.json").currency_auto_update is False


def test_status_and_rate_notes_reflect_missing_cached_and_live_data(tmp_path):
    state = _controller(tmp_path)
    controller = state["controller"]

    assert controller.status_text() == "settings_currency_status_missing"
    assert controller.rate_note() == "labor_currency_note_pln"

    controller._display_currency = "EUR"
    assert controller.rate_note() == "labor_currency_note_missing:currency=EUR"

    cached = ExchangeRates(
        {"PLN": Decimal("1"), "EUR": Decimal("4.20")},
        date="2026-07-26",
        from_cache=True,
    )
    controller.apply_exchange_rates(cached)

    assert controller.status_text().startswith("settings_currency_status_cached:")
    assert controller.rate_note().startswith("labor_currency_note_cached:")


@pytest.mark.parametrize("error", [IncompleteRead(b"partial"), RuntimeError("loader failed"), ValueError("bad cache")])
def test_worker_failure_preserves_snapshot_and_unlocks_refresh_on_ui_thread(tmp_path, error):
    calls = []

    def load_rates(path, *, auto_update, force=False):
        calls.append((path, auto_update))
        raise error

    state = _controller(tmp_path, load_exchange_rates=load_rates)
    controller = state["controller"]
    cached = ExchangeRates({"EUR": Decimal("4.1")}, date="2026-09-03", from_cache=True)
    controller.apply_exchange_rates(cached)
    controller.refresh_exchange_rates_async()
    before_worker = (len(state["ui_refreshes"]), len(state["labor_refreshes"]))
    state["background"][0]()
    assert controller.refresh_running is True
    assert (len(state["ui_refreshes"]), len(state["labor_refreshes"])) == before_worker
    state["scheduled"][0][0]()
    assert controller.exchange_rates is cached
    assert controller.refresh_running is False
    assert len(calls) == 1  # No second unguarded cache load in the exception path.
    assert controller.refresh_exchange_rates_async() is True


def test_thread_start_failure_does_not_lock_refresh(tmp_path):
    state = _controller(tmp_path)
    controller = state["controller"]
    start = controller._start_background

    def broken_start(_worker):
        raise RuntimeError("thread unavailable")

    controller._start_background = broken_start
    assert controller.refresh_exchange_rates_async() is False
    assert controller.refresh_running is False
    controller._start_background = start
    assert controller.refresh_exchange_rates_async() is True


@pytest.mark.parametrize("callback_name", ["_convert_labor_currency", "_refresh_settings_ui", "_refresh_labor_results", "_show_message"])
def test_ui_callback_failure_does_not_lock_refresh(tmp_path, callback_name):
    state = _controller(tmp_path, load_exchange_rates=lambda *_args, **_kwargs: ExchangeRates({}))
    controller = state["controller"]
    controller._display_currency = "EUR"
    controller.refresh_exchange_rates_async(notify=True)
    state["background"][0]()
    original = getattr(controller, callback_name)

    def broken_callback(*_args):
        raise RuntimeError("UI callback failed")

    setattr(controller, callback_name, broken_callback)
    state["scheduled"][0][0]()
    assert controller.refresh_running is False
    setattr(controller, callback_name, original)
    assert controller.refresh_exchange_rates_async() is True


def test_scheduler_failure_never_calls_ui_from_worker(tmp_path):
    state = _controller(tmp_path, load_exchange_rates=lambda *_args, **_kwargs: ExchangeRates({}))
    controller = state["controller"]

    def broken_schedule(*_args):
        raise RuntimeError("scheduler stopped")

    controller._schedule_once = broken_schedule
    controller.refresh_exchange_rates_async()
    before_worker = len(state["ui_refreshes"])
    state["background"][0]()
    assert len(state["ui_refreshes"]) == before_worker
    assert state["labor_refreshes"] == []
    assert controller.refresh_running is False


def test_disabling_auto_update_ignores_queued_result_and_preserves_new_refresh(tmp_path):
    old = ExchangeRates({"EUR": Decimal("4.2")}, date="2026-09-03")
    cached = ExchangeRates({"EUR": Decimal("4.1")}, date="2026-09-02", from_cache=True)
    state = _controller(tmp_path, load_exchange_rates=lambda _path, *, auto_update, force=False: old if auto_update else cached)
    controller = state["controller"]
    controller.refresh_exchange_rates_async()
    state["background"][0]()
    old_callback = state["scheduled"][0][0]
    assert controller.toggle_currency_auto_update() is False
    assert controller.refresh_running is False
    assert controller.exchange_rates is cached
    before = len(state["ui_refreshes"])
    old_callback()
    assert controller.exchange_rates is cached
    assert len(state["ui_refreshes"]) == before

    assert controller.toggle_currency_auto_update() is True
    old_callback()
    assert controller.refresh_running is True  # Old completion cannot unlock a newer request.
    state["background"][1]()
    state["scheduled"][1][0]()
    assert controller.exchange_rates is old
    assert controller.refresh_running is False


def test_cancelled_queued_worker_does_not_start_network_request(tmp_path):
    calls = []

    def load_rates(_path, *, auto_update, force=False):
        calls.append(auto_update)
        return ExchangeRates({})

    state = _controller(tmp_path, load_exchange_rates=load_rates)
    controller = state["controller"]
    controller.refresh_exchange_rates_async()
    controller.toggle_currency_auto_update()
    state["background"][0]()
    assert calls == [False]
    assert state["scheduled"] == []
    assert controller.refresh_running is False


def test_invalid_cache_during_disable_keeps_current_rates(tmp_path):
    def load_rates(*_args, **_kwargs):
        raise ValueError("bad cache")

    state = _controller(tmp_path, load_exchange_rates=load_rates)
    controller = state["controller"]
    cached = ExchangeRates({"EUR": Decimal("4.1")}, date="2026-09-03", from_cache=True)
    controller.apply_exchange_rates(cached)
    controller.refresh_exchange_rates_async()
    controller.toggle_currency_auto_update()
    assert controller.exchange_rates is cached
    assert controller.refresh_running is False


def test_only_explicit_manual_refresh_forces_download(tmp_path):
    calls = []

    def load_rates(_path, *, auto_update, force=False):
        calls.append((auto_update, force))
        return ExchangeRates({})

    state = _controller(tmp_path, load_exchange_rates=load_rates)
    controller = state["controller"]
    controller.set_display_currency("EUR")
    state["background"][0]()
    state["scheduled"][0][0]()
    assert calls == [(True, False)]
    assert controller.refresh_exchange_rates_now() is True
    assert controller.refresh_exchange_rates_now() is False  # No parallel manual requests.
    state["background"][1]()
    state["scheduled"][1][0]()
    assert calls == [(True, False), (True, True)]
    assert controller.refresh_running is False
    assert state["messages"][-1] == "labor_currency_note_missing:currency=EUR"


def test_manual_refresh_cannot_override_disabled_updates(tmp_path):
    calls = []

    def load_rates(_path, *, auto_update, force=False):
        calls.append((auto_update, force))
        return ExchangeRates({})

    state = _controller(
        tmp_path, load_exchange_rates=load_rates,
        prepare_preferences=lambda prefs: prefs.set_currency_auto_update(False),
    )
    assert state["controller"].refresh_exchange_rates_now() is True
    assert calls == [(False, False)]
    assert state["background"] == []

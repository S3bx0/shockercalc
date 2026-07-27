from __future__ import annotations

from decimal import Decimal

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

    def load_rates(path, *, auto_update):
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

    def load_rates(path, *, auto_update):
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

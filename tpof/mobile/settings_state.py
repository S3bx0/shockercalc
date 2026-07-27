"""Application settings state isolated from the Kivy application shell."""

from __future__ import annotations

import threading
from collections.abc import Callable
from pathlib import Path

from tpof.mobile.currency import (
    SUPPORTED_DISPLAY_CURRENCIES,
    ExchangeRates,
    default_exchange_rates,
    get_exchange_rates,
)
from tpof.mobile.user_data import UiPreferences


class SettingsStateController:
    """Owns persisted UI settings and exchange-rate refresh orchestration."""

    def __init__(
        self,
        *,
        preferences: UiPreferences,
        translate: Callable[..., str],
        refresh_settings_ui: Callable[[], None],
        convert_labor_currency: Callable[[str], None],
        refresh_labor_results: Callable[[], None],
        show_message: Callable[[str], None],
        schedule_once: Callable[[Callable[..., object], float], object],
        load_exchange_rates: Callable[..., ExchangeRates] = get_exchange_rates,
        start_background: Callable[[Callable[[], None]], None] | None = None,
    ) -> None:
        self._preferences = preferences
        self._translate = translate
        self._refresh_settings_ui = refresh_settings_ui
        self._convert_labor_currency = convert_labor_currency
        self._refresh_labor_results = refresh_labor_results
        self._show_message = show_message
        self._schedule_once = schedule_once
        self._load_exchange_rates = load_exchange_rates
        self._start_background = start_background or self._start_thread

        self._unit_system = preferences.unit_system
        self._display_currency = preferences.display_currency
        self._currency_auto_update = preferences.currency_auto_update
        self._exchange_rates = default_exchange_rates()
        self._refresh_running = False

    @property
    def unit_system(self) -> str:
        return self._unit_system

    @property
    def display_currency(self) -> str:
        return self._display_currency

    @property
    def currency_auto_update(self) -> bool:
        return self._currency_auto_update

    @property
    def exchange_rates(self) -> ExchangeRates:
        return self._exchange_rates

    @property
    def refresh_running(self) -> bool:
        return self._refresh_running

    @property
    def cache_path(self) -> Path:
        return self._preferences.path.parent / "exchange_rates.json"

    def refresh_ui(self) -> None:
        self._refresh_settings_ui()

    def set_unit_system(self, unit_system: str) -> bool:
        """Keep metric units active until full Imperial conversion exists."""

        if str(unit_system).casefold() == "imperial":
            self._show_message(self._translate("units_imperial_disabled"))
            return False
        self._unit_system = "metric"
        self._preferences.set_unit_system("metric")
        self._show_message(self._translate("units_metric_active"))
        return True

    def rate_note(self) -> str:
        currency = self._display_currency
        rates = self._exchange_rates
        if currency == "PLN":
            return self._translate("labor_currency_note_pln")
        if rates.rate_for(currency) is None:
            return self._translate(
                "labor_currency_note_missing",
                currency=currency,
            )
        values = {
            "currency": currency,
            "date": rates.date or "—",
            "source": rates.source or "NBP",
        }
        key = "labor_currency_note_cached" if rates.from_cache else "labor_currency_note_rate"
        return self._translate(key, **values)

    def status_text(self) -> str:
        if self._refresh_running:
            return self._translate("settings_currency_refreshing")
        rates = self._exchange_rates
        if not rates.date:
            return self._translate("settings_currency_status_missing")
        key = (
            "settings_currency_status_cached"
            if rates.from_cache
            else "settings_currency_status"
        )
        return self._translate(
            key,
            date=rates.date,
            source=rates.source or "NBP",
        )

    def refresh_exchange_rates_async(self, notify: bool = False) -> bool:
        if not self._currency_auto_update:
            self._exchange_rates = self._load_exchange_rates(
                self.cache_path,
                auto_update=False,
            )
            self.refresh_ui()
            self._refresh_labor_results()
            return True
        if self._refresh_running:
            return False

        self._refresh_running = True
        self.refresh_ui()
        cache_path = self.cache_path

        def worker() -> None:
            rates = self._load_exchange_rates(cache_path, auto_update=True)
            self._schedule_once(
                lambda *_args: self.apply_exchange_rates(
                    rates,
                    notify=notify,
                ),
                0,
            )

        self._start_background(worker)
        return True

    def apply_exchange_rates(
        self,
        rates: ExchangeRates,
        notify: bool = False,
    ) -> None:
        self._refresh_running = False
        self._exchange_rates = rates
        self._convert_labor_currency(self._display_currency)
        self.refresh_ui()
        self._refresh_labor_results()
        if notify and self._display_currency != "PLN":
            self._show_message(self.rate_note())

    def set_display_currency(self, currency: str) -> str:
        value = str(currency or "").strip().upper()
        if value not in SUPPORTED_DISPLAY_CURRENCIES:
            value = "PLN"

        # The labor field still uses the previous display currency here, so
        # convert it before exposing and persisting the new target currency.
        self._convert_labor_currency(value)
        self._display_currency = value
        self._preferences.set_display_currency(value)
        self.refresh_ui()
        self._refresh_labor_results()
        if value != "PLN":
            self.refresh_exchange_rates_async(notify=True)
        return value

    def toggle_currency_auto_update(self) -> bool:
        self._currency_auto_update = not self._currency_auto_update
        self._preferences.set_currency_auto_update(self._currency_auto_update)
        self.refresh_ui()
        self.refresh_exchange_rates_async(notify=True)
        return self._currency_auto_update

    @staticmethod
    def _start_thread(callback: Callable[[], None]) -> None:
        threading.Thread(target=callback, daemon=True).start()

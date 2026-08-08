"""State and dependency coordination for the mobile labor-cost tab."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from decimal import Decimal
from typing import Any

from tpof.labor import CostBreakdown
from tpof.mobile.currency import (
    ExchangeRates,
    convert_display_amount,
)
from tpof.mobile.tabs.labor_results import (
    LaborChartRow,
    LaborResultsPresentationMixin,
    LaborTabPresenter,
)
from tpof.mobile.tabs.labor_view import (
    LaborTabView,
    LaborTabViewCompositionMixin,
)
from tpof.mobile.tabs.labor_workflow import LaborCalculationWorkflowMixin

__all__ = (
    "LaborChartRow",
    "LaborResultsPresentationMixin",
    "LaborTabController",
    "LaborTabPresenter",
    "LaborTabView",
)


class LaborTabController(
    LaborCalculationWorkflowMixin,
    LaborResultsPresentationMixin,
    LaborTabViewCompositionMixin,
):
    """Owns the labor tab's view, state, validation and calculation workflow."""

    def __init__(
        self,
        *,
        translate: Callable[..., str],
        get_language: Callable[[], str],
        get_display_currency: Callable[[], str],
        get_exchange_rates: Callable[[], ExchangeRates],
        get_rate_values: Callable[[], Mapping[str, object]],
        reset_rate_values: Callable[[], None],
        is_pro: Callable[[], bool],
        open_rates_dialog: Callable[[], None],
        card_bg: Callable[[], Any],
        total_color: Any,
        chart_factory: Callable[..., Any],
        numeric_input_filter: Callable[..., Any],
        register_themed_card: Callable[[Any], None],
        bind_keyboard_scroll: Callable[[tuple[Any, ...], Any], None],
        style_button: Callable[[Any, str], None],
        clear_field_error: Callable[[Any], None],
        mark_field_error: Callable[[Any, str | None], None],
        show_message: Callable[[str], None],
        log_event: Callable[[str, Mapping[str, object] | None], None],
        get_active_tab: Callable[[], str],
        is_dark: Callable[[], bool],
        announce_result: Callable[[str], bool] | None = None,
    ) -> None:
        self._translate = translate
        self._get_language = get_language
        self._get_display_currency = get_display_currency
        self._get_exchange_rates = get_exchange_rates
        self._get_rate_values = get_rate_values
        self._reset_rate_values = reset_rate_values
        self._is_pro = is_pro
        self._open_rates_dialog = open_rates_dialog
        self._card_bg = card_bg
        self._total_color = total_color
        self._chart_factory = chart_factory
        self._numeric_input_filter = numeric_input_filter
        self._register_themed_card = register_themed_card
        self._bind_keyboard_scroll = bind_keyboard_scroll
        self._style_button = style_button
        self._clear_field_error = clear_field_error
        self._mark_field_error = mark_field_error
        self._show_message = show_message
        self._log_event = log_event
        self._get_active_tab = get_active_tab
        self._is_dark = is_dark
        self._announce_result = announce_result or (lambda _message: False)
        self._presenter = LaborTabPresenter(
            translate=translate,
            get_language=get_language,
            chart_colors=getattr(chart_factory, "SEGMENT_COLORS", {}),
        )
        self.use_highways = False
        self.has_additional = False
        self.additional_currency = self._normalized_currency(
            self._get_display_currency()
        )
        self.last_breakdown: CostBreakdown | None = None
        self._chart_dialog: Any | None = None
        self.view: LaborTabView | None = None

    @property
    def scroll(self) -> Any | None:
        """Return the tab scroll widget after the view has been built."""

        return None if self.view is None else self.view.scroll

    def result_color(self) -> Any:
        return self._total_color() if callable(self._total_color) else self._total_color

    def hint_field_items(self) -> tuple[tuple[Any, str], ...]:
        """Expose labor inputs to the app-wide optional hint coordinator."""

        if self.view is None:
            return ()
        return (
            (self.view.people_input, "hint_labor_people"),
            (self.view.days_input, "hint_labor_days"),
            (self.view.distance_input, "hint_labor_distance"),
            (self.view.lifts_input, "hint_labor_lifts"),
            (self.view.containers_input, "hint_labor_containers"),
            (self.view.additional_input, "hint_labor_additional"),
        )

    @staticmethod
    def _normalized_currency(currency: str) -> str:
        value = str(currency or "PLN").strip().upper()
        return value if value in {"PLN", "EUR", "USD"} else "PLN"

    @staticmethod
    def _dp(value: float) -> float:
        try:
            from kivy.metrics import dp

            return float(dp(value))
        except ImportError:  # pragma: no cover - unit-test host without Kivy
            return value

    def set_highways(self, enabled: bool) -> None:
        self.use_highways = bool(enabled)
        if self.view is None:
            return
        self.view.highways_button.text = self._translate(
            "labor_highways_on" if self.use_highways else "labor_highways_off"
        )
        self._style_button(
            self.view.highways_button,
            "primary" if self.use_highways else "dark",
        )

    def toggle_highways(self) -> None:
        self.set_highways(not self.use_highways)

    def set_additional_enabled(self, enabled: bool) -> None:
        self.has_additional = bool(enabled)
        if self.view is None:
            return
        self.view.additional_button.text = self._translate(
            "labor_additional_on"
            if self.has_additional
            else "labor_additional_off"
        )
        self._style_button(
            self.view.additional_button,
            "primary" if self.has_additional else "dark",
        )
        expanded_height = getattr(
            self.view.additional_box,
            "expanded_height",
            self._dp(60),
        )
        self.view.additional_box.height = expanded_height if self.has_additional else 0
        self.view.additional_box.opacity = 1 if self.has_additional else 0
        self.view.additional_box.disabled = not self.has_additional
        if not self.has_additional:
            self.view.additional_input.text = ""
            self._clear_field_error(self.view.additional_input)

    def toggle_additional(self) -> None:
        self.set_additional_enabled(not self.has_additional)

    def additional_hint(self) -> str:
        return (
            f"{self._translate('labor_additional')} "
            f"[{self.additional_currency}]"
        )

    def refresh_additional_hint(self) -> None:
        if self.view is not None:
            self.view.additional_input.hint_text = self.additional_hint()

    @staticmethod
    def _editable_currency_text(value: Decimal) -> str:
        text = format(value, "f")
        if "." in text:
            text = text.rstrip("0").rstrip(".")
        return text or "0"

    def convert_additional_field_currency(self, target_currency: str) -> bool:
        target = self._normalized_currency(target_currency)
        source = self.additional_currency
        field = None if self.view is None else self.view.additional_input
        raw = (getattr(field, "text", "") or "").strip() if field is not None else ""
        if not raw:
            self.additional_currency = target
            self.refresh_additional_hint()
            return True
        if source == target:
            self.refresh_additional_hint()
            return True
        try:
            converted = convert_display_amount(
                Decimal(raw.replace(",", ".")),
                source,
                target,
                self._get_exchange_rates(),
            )
        except (ValueError, ArithmeticError):
            return False
        assert field is not None
        field.text = self._editable_currency_text(converted)
        self.additional_currency = target
        self.refresh_additional_hint()
        return True

    def refresh_texts(self) -> None:
        if self.view is None:
            return
        self.view.title_label.text = self._translate("labor_title")
        self.view.hint_label.text = self._translate("labor_hint")
        self.view.people_input.hint_text = self._translate("labor_people")
        self.view.days_input.hint_text = self._translate("labor_days")
        self.view.distance_input.hint_text = self._translate("labor_distance")
        self.view.lifts_input.hint_text = self._translate("labor_lifts")
        self.view.containers_input.hint_text = self._translate("labor_containers")
        self.refresh_additional_hint()
        self.view.rates_button.text = self._translate("labor_rates_button")
        self.view.calculate_button.text = self._translate("labor_calculate")
        self.view.result_title_label.text = self._translate("labor_result")
        self.set_highways(self.use_highways)
        self.set_additional_enabled(self.has_additional)
        self.refresh_results()

    def apply_theme(self) -> None:
        if self.view is None:
            return
        self.view.total_label.text_color = self.result_color()
        self.view.chart.set_dark(self._is_dark())
        for button, variant in (
            (
                self.view.highways_button,
                "primary" if self.use_highways else "dark",
            ),
            (
                self.view.additional_button,
                "primary" if self.has_additional else "dark",
            ),
            (self.view.rates_button, "pro"),
            (self.view.calculate_button, "ice"),
        ):
            self._style_button(button, variant)

    def open_rates(self) -> None:
        if not self._is_pro():
            self._show_message(self._translate("labor_rates_pro_required"))
            return
        self._open_rates_dialog()

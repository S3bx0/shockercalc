"""Framework-independent presentation logic for the mobile labor-cost tab."""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from tpof.labor import (
    CalculationInput,
    CostBreakdown,
    calculate_cost_breakdown,
    default_rate_config,
    rate_config_from_values,
    validate_calculation_inputs,
)
from tpof.mobile.currency import (
    ExchangeRates,
    convert_display_amount,
    convert_display_amount_to_pln,
    format_money,
)

Color = tuple[float, float, float, float]
log = logging.getLogger(__name__)

_CHART_LABEL_KEYS = (
    ("labor_cost", "labor_labor_cost"),
    ("travel_cost", "labor_travel_cost"),
    ("lift_cost", "labor_lift_cost"),
    ("container_cost", "labor_container_cost"),
    ("hotel_cost", "labor_hotel_cost"),
    ("allowance_cost", "labor_allowance_cost"),
    ("regenerative_meal_cost", "labor_meal_cost"),
    ("additional_costs_value", "labor_additional_costs"),
)


@dataclass(frozen=True)
class LaborChartRow:
    """A normalized cost segment ready for chart and legend widgets."""

    key: str
    label: str
    value: Decimal
    percent: float
    color: Color


class LaborTabPresenter:
    """Converts labor-domain results into localized, UI-ready values."""

    _fallback_color: Color = (0.79, 0.96, 1.0, 1.0)

    def __init__(
        self,
        *,
        translate: Callable[..., str],
        get_language: Callable[[], str],
        chart_colors: Mapping[str, Color],
    ) -> None:
        self._translate = translate
        self._get_language = get_language
        self._chart_colors = dict(chart_colors)

    def travel_mode_text(self, mode: str) -> str:
        if self._get_language() == "pl":
            return mode
        translations = {
            "Dojazd dzienny": "Daily travel",
            "Delegacja tygodniowa": "Weekly delegation",
        }
        return translations.get(mode, mode)

    def chart_rows(self, breakdown: Any | None) -> list[LaborChartRow]:
        if breakdown is None:
            return []
        rows: list[tuple[str, str, Decimal, Color]] = []
        total = Decimal("0")
        for attr, label_key in _CHART_LABEL_KEYS:
            value = Decimal(str(getattr(breakdown, attr, Decimal("0")) or "0"))
            if value <= 0:
                continue
            total += value
            label = self._translate(label_key, value="").split(":")[0].strip()
            rows.append(
                (
                    attr,
                    label,
                    value,
                    self._chart_colors.get(attr, self._fallback_color),
                )
            )
        if total <= 0:
            return []
        return [
            LaborChartRow(
                key=key,
                label=label,
                value=value,
                percent=float((value / total) * Decimal("100")),
                color=color,
            )
            for key, label, value, color in rows
        ]


@dataclass(frozen=True)
class LaborTabView:
    """Widget references exposed by the labor tab's view boundary."""

    scroll: Any
    input_card: Any
    title_label: Any
    hint_label: Any
    people_input: Any
    days_input: Any
    distance_input: Any
    lifts_input: Any
    containers_input: Any
    highways_button: Any
    additional_button: Any
    additional_input: Any
    additional_box: Any
    calculate_button: Any
    rates_button: Any
    result_card: Any
    result_title_label: Any
    total_label: Any
    currency_note: Any
    chart: Any
    chart_hint: Any
    chart_legend: Any
    result_labels: dict[str, tuple[Any, str]]
    travel_mode_label: Any
    travel_details_label: Any

    @property
    def input_fields(self) -> tuple[Any, ...]:
        return (
            self.people_input,
            self.days_input,
            self.distance_input,
            self.lifts_input,
            self.containers_input,
            self.additional_input,
        )


class LaborTabController:
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

    def build(self) -> LaborTabView:
        """Create the complete labor tab and retain its typed widget boundary."""

        from kivy.metrics import dp
        from kivymd.uix.boxlayout import MDBoxLayout
        from kivymd.uix.button import MDRaisedButton
        from kivymd.uix.card import MDCard
        from kivymd.uix.label import MDLabel
        from kivymd.uix.scrollview import MDScrollView
        from kivymd.uix.textfield import MDTextField

        scroll = MDScrollView()
        content = MDBoxLayout(
            orientation="vertical",
            padding=[dp(16), dp(14), dp(16), dp(18)],
            spacing=dp(14),
            size_hint_y=None,
        )
        content.bind(minimum_height=content.setter("height"))

        input_card = MDCard(
            orientation="vertical",
            padding=dp(14),
            spacing=dp(10),
            size_hint_y=None,
            radius=[16, 16, 16, 16],
            elevation=3,
            md_bg_color=self._card_bg(),
        )
        input_card.bind(minimum_height=input_card.setter("height"))
        self._register_themed_card(input_card)

        title_label = MDLabel(
            text=self._translate("labor_title"),
            font_style="H6",
            size_hint_y=None,
            height=dp(36),
        )
        input_card.add_widget(title_label)
        hint_label = MDLabel(
            text=self._translate("labor_hint"),
            font_style="Caption",
            theme_text_color="Hint",
            size_hint_y=None,
            height=dp(38),
        )
        input_card.add_widget(hint_label)

        people_input = MDTextField(
            hint_text=self._translate("labor_people"), input_filter="int"
        )
        days_input = MDTextField(
            hint_text=self._translate("labor_days"), input_filter="int"
        )
        distance_input = MDTextField(
            hint_text=self._translate("labor_distance"), input_filter="int"
        )
        lifts_input = MDTextField(
            hint_text=self._translate("labor_lifts"), input_filter="int"
        )
        containers_input = MDTextField(
            hint_text=self._translate("labor_containers"), input_filter="int"
        )
        for field in (
            people_input,
            days_input,
            distance_input,
            lifts_input,
            containers_input,
        ):
            field.size_hint_y = None
            field.height = dp(60)
            input_card.add_widget(field)

        toggle_row = MDBoxLayout(
            orientation="horizontal",
            spacing=dp(8),
            size_hint_y=None,
            height=dp(46),
        )
        highways_button = MDRaisedButton(
            text=self._translate("labor_highways_off"),
            size_hint_x=0.5,
            size_hint_y=None,
            height=dp(44),
            font_size="13sp",
            on_release=lambda *_: self.toggle_highways(),
        )
        additional_button = MDRaisedButton(
            text=self._translate("labor_additional_off"),
            size_hint_x=0.5,
            size_hint_y=None,
            height=dp(44),
            font_size="13sp",
            on_release=lambda *_: self.toggle_additional(),
        )
        toggle_row.add_widget(highways_button)
        toggle_row.add_widget(additional_button)
        input_card.add_widget(toggle_row)

        additional_input = MDTextField(
            hint_text=self.additional_hint(),
            input_filter=self._numeric_input_filter,
        )
        additional_input.size_hint_y = None
        additional_input.height = dp(60)
        additional_box = MDBoxLayout(
            orientation="vertical", size_hint_y=None, height=0
        )
        additional_box.add_widget(additional_input)
        input_card.add_widget(additional_box)

        calculate_button = MDRaisedButton(
            text=self._translate("labor_calculate"),
            icon="calculator-variant",
            size_hint_x=0.64,
            size_hint_y=None,
            height=dp(50),
            font_size="15sp",
            on_release=lambda *_: self.calculate(),
        )
        rates_button = MDRaisedButton(
            text=self._translate("labor_rates_button"),
            icon="tune-variant",
            size_hint_x=0.36,
            size_hint_y=None,
            height=dp(50),
            font_size="13sp",
            on_release=lambda *_: self.open_rates(),
        )
        action_row = MDBoxLayout(
            orientation="horizontal",
            spacing=dp(8),
            size_hint_y=None,
            height=dp(52),
        )
        action_row.add_widget(rates_button)
        action_row.add_widget(calculate_button)
        input_card.add_widget(action_row)
        content.add_widget(input_card)

        result_card = MDCard(
            orientation="vertical",
            padding=dp(14),
            spacing=dp(8),
            size_hint_y=None,
            radius=[16, 16, 16, 16],
            elevation=3,
            md_bg_color=self._card_bg(),
        )
        result_card.bind(minimum_height=result_card.setter("height"))
        self._register_themed_card(result_card)

        result_title_label = MDLabel(
            text=self._translate("labor_result"),
            font_style="H6",
            size_hint_y=None,
            height=dp(36),
        )
        result_card.add_widget(result_title_label)
        total_label = MDLabel(
            text=self._translate("labor_total_cost", value="—"),
            font_style="H6",
            halign="center",
            size_hint_y=None,
            height=dp(44),
            theme_text_color="Custom",
            text_color=self._total_color,
        )
        result_card.add_widget(total_label)
        currency_note = MDLabel(
            text=self._translate("labor_currency_note_pln"),
            halign="center",
            size_hint_y=None,
            height=dp(30),
            theme_text_color="Hint",
            font_style="Caption",
        )
        result_card.add_widget(currency_note)
        chart = self._chart_factory(
            size_hint_y=None,
            height=dp(210),
            on_release=lambda *_: self.open_chart_dialog(),
        )
        result_card.add_widget(chart)
        chart_hint = MDLabel(
            text=self._translate("labor_chart_empty"),
            halign="center",
            size_hint_y=None,
            height=dp(24),
            theme_text_color="Hint",
            font_style="Caption",
        )
        result_card.add_widget(chart_hint)
        chart_legend = MDBoxLayout(
            orientation="vertical",
            spacing=dp(3),
            size_hint_y=None,
            height=0,
        )
        result_card.add_widget(chart_legend)

        result_labels: dict[str, tuple[Any, str]] = {}
        for attr, key in _CHART_LABEL_KEYS:
            label = MDLabel(
                text=self._translate(key, value="—"),
                size_hint_y=None,
                height=dp(28),
                theme_text_color="Secondary",
            )
            result_labels[attr] = (label, key)
        travel_mode_label = MDLabel(
            text=self._translate("labor_travel_mode", value="—"),
            size_hint_y=None,
            height=dp(28),
            theme_text_color="Secondary",
        )
        travel_details_label = MDLabel(
            text=self._translate(
                "labor_travel_details", trips="—", toll_days="—", nights="—"
            ),
            size_hint_y=None,
            height=dp(32),
            theme_text_color="Hint",
            font_style="Caption",
        )
        result_card.add_widget(travel_mode_label)
        result_card.add_widget(travel_details_label)
        content.add_widget(result_card)

        view = LaborTabView(
            scroll=scroll,
            input_card=input_card,
            title_label=title_label,
            hint_label=hint_label,
            people_input=people_input,
            days_input=days_input,
            distance_input=distance_input,
            lifts_input=lifts_input,
            containers_input=containers_input,
            highways_button=highways_button,
            additional_button=additional_button,
            additional_input=additional_input,
            additional_box=additional_box,
            calculate_button=calculate_button,
            rates_button=rates_button,
            result_card=result_card,
            result_title_label=result_title_label,
            total_label=total_label,
            currency_note=currency_note,
            chart=chart,
            chart_hint=chart_hint,
            chart_legend=chart_legend,
            result_labels=result_labels,
            travel_mode_label=travel_mode_label,
            travel_details_label=travel_details_label,
        )
        self.view = view
        self._bind_keyboard_scroll(view.input_fields, scroll)
        scroll.add_widget(content)
        self.set_highways(False)
        self.set_additional_enabled(False)
        self.render_results(None)
        return view

    @property
    def scroll(self) -> Any | None:
        """Return the tab scroll widget after the view has been built."""

        return None if self.view is None else self.view.scroll

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
        self.view.additional_box.height = self._dp(60) if self.has_additional else 0
        self.view.additional_box.opacity = 1 if self.has_additional else 0
        self.view.additional_box.disabled = not self.has_additional
        if not self.has_additional:
            self.view.additional_input.text = ""
            self._clear_field_error(self.view.additional_input)

    def toggle_additional(self) -> None:
        self.set_additional_enabled(not self.has_additional)

    def clear_validation(self) -> None:
        if self.view is None:
            return
        for field in self.view.input_fields:
            self._clear_field_error(field)

    def _invalid_field_message(self, name_key: str) -> str:
        return self._translate(
            "invalid_field",
            name=self._translate(name_key),
        )

    def _parse_int(
        self,
        field: Any,
        name_key: str,
        *,
        min_value: int,
        allow_zero: bool,
        default_empty: int | None = None,
    ) -> int:
        raw = (getattr(field, "text", "") or "").strip()
        if not raw and default_empty is not None:
            return default_empty
        message = self._invalid_field_message(name_key)
        if not raw:
            self._mark_field_error(field, None)
            raise ValueError(message)
        try:
            value = int(raw)
        except (TypeError, ValueError) as exc:
            self._mark_field_error(field, message)
            raise ValueError(message) from exc
        if value < min_value or (not allow_zero and value == 0):
            self._mark_field_error(field, message)
            raise ValueError(message)
        return value

    def _parse_decimal(self, field: Any, name_key: str) -> Decimal:
        raw = (getattr(field, "text", "") or "").strip()
        message = self._invalid_field_message(name_key)
        if not raw:
            self._mark_field_error(field, None)
            raise ValueError(message)
        try:
            value = Decimal(raw.replace(",", "."))
        except Exception as exc:
            self._mark_field_error(field, message)
            raise ValueError(message) from exc
        if value < 0:
            self._mark_field_error(field, message)
            raise ValueError(message)
        return value

    def format_money(self, value: Any) -> str:
        if value is None:
            return "—"
        return format_money(
            value,
            self._get_display_currency(),
            self._get_exchange_rates(),
            self._get_language(),
        )

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

    def _currency_rate_note(self) -> str:
        currency = self._normalized_currency(self._get_display_currency())
        rates = self._get_exchange_rates()
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
        key = (
            "labor_currency_note_cached"
            if rates.from_cache
            else "labor_currency_note_rate"
        )
        return self._translate(key, **values)

    def _chart_rows(self, breakdown: CostBreakdown | None) -> list[LaborChartRow]:
        return self._presenter.chart_rows(breakdown)

    def _set_chart_data(
        self,
        chart: Any,
        breakdown: CostBreakdown | None,
        *,
        animate: bool = True,
    ) -> None:
        rows = self._chart_rows(breakdown)
        items = [
            {
                "key": row.key,
                "label": row.label,
                "value": row.value,
                "color": row.color,
            }
            for row in rows
        ]
        total = "—" if breakdown is None else self.format_money(breakdown.total_cost)
        chart.set_dark(self._is_dark())
        chart.set_data(
            items,
            center_label=self._translate("labor_chart_total"),
            center_value=total,
            animate=animate,
        )

    def _render_chart_legend(self, breakdown: CostBreakdown | None) -> None:
        if self.view is None or self.view.chart_legend is None:
            return
        from kivy.metrics import dp
        from kivymd.uix.boxlayout import MDBoxLayout
        from kivymd.uix.card import MDCard
        from kivymd.uix.label import MDLabel

        legend = self.view.chart_legend
        legend.clear_widgets()
        rows = self._chart_rows(breakdown)
        self.view.chart_hint.text = (
            self._translate("labor_chart_tap")
            if rows
            else self._translate("labor_chart_empty")
        )
        if not rows:
            legend.height = 0
            return
        shown = rows[:4]
        legend.height = len(shown) * dp(42)
        for chart_row in shown:
            row = MDBoxLayout(
                orientation="horizontal",
                spacing=dp(8),
                size_hint_y=None,
                height=dp(42),
            )
            swatch = MDCard(
                size_hint=(None, None),
                size=(dp(12), dp(12)),
                pos_hint={"center_y": 0.5},
                radius=[dp(3), dp(3), dp(3), dp(3)],
                elevation=0,
                md_bg_color=chart_row.color,
            )
            name = MDLabel(
                text=chart_row.label,
                theme_text_color="Primary",
                font_size="12sp",
                size_hint_x=0.47,
                valign="middle",
            )
            name.bind(
                width=lambda widget, width: setattr(
                    widget,
                    "text_size",
                    (width, None),
                )
            )
            amount = MDLabel(
                text=(
                    f"{chart_row.percent:.1f}% · "
                    f"{self.format_money(chart_row.value)}"
                ),
                halign="right",
                valign="middle",
                theme_text_color="Primary",
                font_size="11.5sp",
                size_hint_x=0.53,
            )
            amount.bind(
                width=lambda widget, width: setattr(
                    widget,
                    "text_size",
                    (width, None),
                )
            )
            row.add_widget(swatch)
            row.add_widget(name)
            row.add_widget(amount)
            legend.add_widget(row)
        if len(rows) > len(shown):
            self.view.chart_hint.text = self._translate("labor_chart_tap")

    def close_chart_dialog(self) -> None:
        if self._chart_dialog is not None:
            self._chart_dialog.dismiss()
            self._chart_dialog = None

    def open_chart_dialog(self) -> None:
        self.close_chart_dialog()
        rows = self._chart_rows(self.last_breakdown)
        if not rows:
            self._show_message(self._translate("labor_chart_empty"))
            return
        from kivy.core.window import Window
        from kivy.metrics import dp
        from kivymd.uix.boxlayout import MDBoxLayout
        from kivymd.uix.button import MDFlatButton
        from kivymd.uix.card import MDCard
        from kivymd.uix.dialog import MDDialog
        from kivymd.uix.label import MDLabel
        from kivymd.uix.scrollview import MDScrollView

        content = MDBoxLayout(
            orientation="vertical",
            spacing=dp(8),
            padding=[0, dp(4), 0, 0],
            size_hint_y=None,
            height=max(dp(320), min(dp(460), Window.height * 0.62)),
        )
        chart = self._chart_factory(size_hint_y=None, height=dp(210))
        self._set_chart_data(chart, self.last_breakdown, animate=True)
        content.add_widget(chart)
        detail_scroll = MDScrollView(size_hint=(1, 1))
        detail_list = MDBoxLayout(
            orientation="vertical",
            spacing=dp(4),
            size_hint_y=None,
        )
        detail_list.bind(minimum_height=detail_list.setter("height"))
        for chart_row in rows:
            row = MDBoxLayout(
                orientation="horizontal",
                spacing=dp(8),
                size_hint_y=None,
                height=dp(46),
            )
            swatch = MDCard(
                size_hint=(None, None),
                size=(dp(13), dp(13)),
                pos_hint={"center_y": 0.5},
                radius=[dp(3), dp(3), dp(3), dp(3)],
                elevation=0,
                md_bg_color=chart_row.color,
            )
            name = MDLabel(
                text=chart_row.label,
                theme_text_color="Primary",
                font_size="12sp",
                size_hint_x=0.48,
                valign="middle",
            )
            name.bind(
                width=lambda widget, width: setattr(
                    widget,
                    "text_size",
                    (width, None),
                )
            )
            amount = MDLabel(
                text=(
                    f"{self.format_money(chart_row.value)} · "
                    f"{chart_row.percent:.1f}%"
                ),
                halign="right",
                valign="middle",
                theme_text_color="Primary",
                font_size="11.5sp",
                size_hint_x=0.52,
            )
            amount.bind(
                width=lambda widget, width: setattr(
                    widget,
                    "text_size",
                    (width, None),
                )
            )
            row.add_widget(swatch)
            row.add_widget(name)
            row.add_widget(amount)
            detail_list.add_widget(row)
        detail_scroll.add_widget(detail_list)
        content.add_widget(detail_scroll)
        self._chart_dialog = MDDialog(
            title=self._translate("labor_chart_details"),
            type="custom",
            content_cls=content,
            buttons=[
                MDFlatButton(
                    text=self._translate("close"),
                    on_release=lambda *_: self.close_chart_dialog(),
                )
            ],
        )
        self._chart_dialog.size_hint_x = 0.94
        self._chart_dialog.open()

    def render_results(self, breakdown: CostBreakdown | None) -> None:
        self.last_breakdown = breakdown
        if self.view is None:
            return
        dash = "—"
        self.view.total_label.text = self._translate(
            "labor_total_cost",
            value=(
                dash
                if breakdown is None
                else self.format_money(breakdown.total_cost)
            ),
        )
        self.view.currency_note.text = self._currency_rate_note()
        self._set_chart_data(
            self.view.chart,
            breakdown,
            animate=breakdown is not None,
        )
        self._render_chart_legend(breakdown)
        for attr, (label, key) in self.view.result_labels.items():
            value = (
                dash
                if breakdown is None
                else self.format_money(getattr(breakdown, attr))
            )
            label.text = self._translate(key, value=value)
        self.view.travel_mode_label.text = self._translate(
            "labor_travel_mode",
            value=(
                dash
                if breakdown is None
                else self._presenter.travel_mode_text(breakdown.travel_mode)
            ),
        )
        self.view.travel_details_label.text = self._translate(
            "labor_travel_details",
            trips=dash if breakdown is None else breakdown.travel_round_trips,
            toll_days=dash if breakdown is None else breakdown.highway_toll_days,
            nights=dash if breakdown is None else breakdown.hotel_nights,
        )

    def refresh_results(self) -> None:
        self.render_results(self.last_breakdown)

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

    def _rate_config(self) -> Any:
        try:
            return rate_config_from_values(self._get_rate_values())
        except ValueError:
            self._reset_rate_values()
            return default_rate_config()

    def open_rates(self) -> None:
        if not self._is_pro():
            self._show_message(self._translate("labor_rates_pro_required"))
            return
        self._open_rates_dialog()

    def invalidate_results(self) -> None:
        self.render_results(None)

    def calculate(self) -> bool:
        if self.view is None:
            return False
        self.clear_validation()
        try:
            people = self._parse_int(
                self.view.people_input,
                "labor_people",
                min_value=1,
                allow_zero=False,
            )
            days = self._parse_int(
                self.view.days_input,
                "labor_days",
                min_value=1,
                allow_zero=False,
            )
            distance = self._parse_int(
                self.view.distance_input,
                "labor_distance",
                min_value=0,
                allow_zero=True,
            )
            lifts = self._parse_int(
                self.view.lifts_input,
                "labor_lifts",
                min_value=0,
                allow_zero=True,
                default_empty=0,
            )
            containers = self._parse_int(
                self.view.containers_input,
                "labor_containers",
                min_value=0,
                allow_zero=True,
                default_empty=0,
            )
            additional = (
                self._parse_decimal(
                    self.view.additional_input,
                    "labor_additional",
                )
                if self.has_additional
                else Decimal("0")
            )
            if self.has_additional:
                try:
                    additional = convert_display_amount_to_pln(
                        additional,
                        self.additional_currency,
                        self._get_exchange_rates(),
                    )
                except ValueError as exc:
                    message = self._translate(
                        "labor_currency_input_missing",
                        currency=self.additional_currency,
                    )
                    self._mark_field_error(
                        self.view.additional_input,
                        message,
                    )
                    raise ValueError(message) from exc
            errors = validate_calculation_inputs(
                people,
                days,
                distance,
                lifts,
                containers,
                self.has_additional,
                additional,
            )
            if errors:
                raise ValueError(errors[0])
            self._log_event(
                "calculation_started",
                {
                    "calculator": "labor",
                    "screen": self._get_active_tab(),
                },
            )
            breakdown = calculate_cost_breakdown(
                CalculationInput(
                    number_of_people=people,
                    number_of_days=days,
                    distance_km_one_way=distance,
                    use_highways=self.use_highways,
                    number_of_lifts=lifts,
                    number_of_containers=containers,
                    additional_costs_value=additional,
                ),
                self._rate_config(),
            )
            self.render_results(breakdown)
            self._log_event(
                "calculation_finished",
                {
                    "calculator": "labor",
                    "travel_mode": breakdown.travel_mode,
                    "has_additional": self.has_additional,
                },
            )
            self.view.scroll.scroll_to(
                self.view.result_card,
                padding=self._dp(12),
                animate=True,
            )
            return True
        except ValueError as exc:
            self._show_message(
                self._translate(
                    "labor_validation_error",
                    message=str(exc),
                )
            )
            self._log_event(
                "calculation_error",
                {
                    "calculator": "labor",
                    "error": str(exc)[:120],
                },
            )
            return False
        except Exception as exc:  # pragma: no cover - UI safeguard
            log.exception("Błąd obliczeń robocizny")
            self._show_message(self._translate("calc_error", error=exc))
            return False

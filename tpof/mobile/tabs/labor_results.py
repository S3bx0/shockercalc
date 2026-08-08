"""Result and chart presentation for the mobile labor-cost tab."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from tpof.labor import CostBreakdown
from tpof.mobile.currency import ExchangeRates, format_money
from tpof.mobile.tabs.labor_view import (
    LABOR_RESULT_LABEL_KEYS,
    LaborTabView,
)

Color = tuple[float, float, float, float]


@dataclass(frozen=True)
class LaborChartRow:
    """A normalized cost segment ready for chart and legend widgets."""

    key: str
    label: str
    value: Decimal
    percent: float
    color: Color


class LaborTabPresenter:
    """Convert labor-domain results into localized, UI-ready values."""

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
        for attr, label_key in LABOR_RESULT_LABEL_KEYS:
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


class LaborResultsPresentationMixin:
    """Render labor results and charts without owning calculations."""

    _translate: Callable[..., str]
    _get_language: Callable[[], str]
    _get_display_currency: Callable[[], str]
    _get_exchange_rates: Callable[[], ExchangeRates]
    _chart_factory: Callable[..., Any]
    _show_message: Callable[[str], None]
    _is_dark: Callable[[], bool]
    _presenter: LaborTabPresenter
    _chart_dialog: Any | None

    last_breakdown: CostBreakdown | None
    view: LaborTabView | None

    def format_money(self, value: Any) -> str:
        if value is None:
            return "—"
        return format_money(
            value,
            self._get_display_currency(),
            self._get_exchange_rates(),
            self._get_language(),
        )

    def _currency_rate_note(self) -> str:
        currency = str(self._get_display_currency() or "PLN").strip().upper()
        if currency not in {"PLN", "EUR", "USD"}:
            currency = "PLN"
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

    def _chart_rows(
        self,
        breakdown: CostBreakdown | None,
    ) -> list[LaborChartRow]:
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
                    size_hint_y=None,
                    height=dp(48),
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

    def invalidate_results(self) -> None:
        self.render_results(None)

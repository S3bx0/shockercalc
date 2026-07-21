"""Settings dialog controller isolated from the mobile application shell."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from tpof.mobile.constants import BRAND_ICE
from tpof.mobile.currency import (
    SUPPORTED_DISPLAY_CURRENCIES,
    ExchangeRates,
    format_exchange_rate,
)

log = logging.getLogger(__name__)


class SettingsDialogController:
    """Owns settings-dialog widgets and delegates state changes to the app."""

    def __init__(
        self,
        *,
        translate: Callable[..., str],
        style_button: Callable[[Any, str], None],
        card_bg: Callable[[], Any],
        get_display_currency: Callable[[], str],
        get_exchange_rates: Callable[[], ExchangeRates],
        get_language: Callable[[], str],
        get_auto_update: Callable[[], bool],
        get_status_text: Callable[[], str],
        on_set_unit_system: Callable[[str], None],
        on_set_display_currency: Callable[[str], None],
        on_toggle_auto_update: Callable[[], None],
    ) -> None:
        self._translate = translate
        self._style_button = style_button
        self._card_bg = card_bg
        self._get_display_currency = get_display_currency
        self._get_exchange_rates = get_exchange_rates
        self._get_language = get_language
        self._get_auto_update = get_auto_update
        self._get_status_text = get_status_text
        self._on_set_unit_system = on_set_unit_system
        self._on_set_display_currency = on_set_display_currency
        self._on_toggle_auto_update = on_toggle_auto_update

        self._dialog: Any | None = None
        self._currency_buttons: dict[str, Any] = {}
        self._currency_rate_labels: dict[str, Any] = {}
        self._currency_auto_button: Any | None = None
        self._currency_status: Any | None = None

    @property
    def is_open(self) -> bool:
        return self._dialog is not None

    def close(self, *_args) -> None:
        if self._dialog is not None:
            self._dialog.dismiss()
        self._dialog = None
        self._currency_buttons = {}
        self._currency_rate_labels = {}
        self._currency_auto_button = None
        self._currency_status = None

    def refresh(self) -> None:
        """Refreshes the current dialog from application-owned settings state."""

        selected = self._get_display_currency()
        for code, button in self._currency_buttons.items():
            self._style_button(button, "ice" if code == selected else "muted")

        rates = self._get_exchange_rates()
        language = self._get_language()
        for code, label in self._currency_rate_labels.items():
            label.text = format_exchange_rate(code, rates, language) or self._translate(
                "settings_currency_rate_missing", currency=code
            )

        auto_update = self._get_auto_update()
        if self._currency_auto_button is not None:
            self._currency_auto_button.text = self._translate(
                "settings_currency_auto_on" if auto_update else "settings_currency_auto_off"
            )
            self._style_button(
                self._currency_auto_button,
                "ice" if auto_update else "muted",
            )
        if self._currency_status is not None:
            self._currency_status.text = self._get_status_text()

    def open(self) -> bool:
        """Builds and opens the dialog. Kivy imports stay lazy for unit tests."""

        self.close()
        try:
            from kivy.core.window import Window
            from kivy.metrics import dp
            from kivymd.uix.boxlayout import MDBoxLayout
            from kivymd.uix.button import MDFlatButton, MDRaisedButton
            from kivymd.uix.card import MDCard
            from kivymd.uix.dialog import MDDialog
            from kivymd.uix.label import MDLabel
            from kivymd.uix.scrollview import MDScrollView

            content = MDBoxLayout(
                orientation="vertical",
                spacing=dp(10),
                size_hint_y=None,
            )
            content.bind(minimum_height=content.setter("height"))
            content.add_widget(
                MDLabel(
                    text=self._translate("settings_intro"),
                    theme_text_color="Hint",
                    font_style="Body2",
                    adaptive_height=True,
                )
            )
            content.add_widget(
                MDLabel(
                    text=self._translate("units_title"),
                    theme_text_color="Custom",
                    text_color=BRAND_ICE,
                    font_style="Subtitle1",
                    adaptive_height=True,
                )
            )
            content.add_widget(
                MDLabel(
                    text=self._translate("units_metric_active"),
                    theme_text_color="Custom",
                    text_color=(0.85, 0.98, 1.0, 1),
                    font_style="Body2",
                    adaptive_height=True,
                )
            )
            content.add_widget(
                MDLabel(
                    text=self._translate("units_imperial_disabled"),
                    theme_text_color="Hint",
                    font_style="Caption",
                    adaptive_height=True,
                )
            )

            metric_row = MDBoxLayout(
                orientation="horizontal",
                size_hint_y=None,
                height=dp(42),
            )
            metric_button = MDRaisedButton(
                text=self._translate("units_metric"),
                size_hint_x=1,
                on_release=lambda *_: self._on_set_unit_system("metric"),
            )
            self._style_button(metric_button, "ice")
            metric_row.add_widget(metric_button)
            content.add_widget(metric_row)

            imperial_row = MDBoxLayout(
                orientation="horizontal",
                size_hint_y=None,
                height=dp(42),
            )
            imperial_row.add_widget(
                MDFlatButton(
                    text=self._translate("units_imperial"),
                    size_hint_x=1,
                    disabled=True,
                )
            )
            content.add_widget(imperial_row)
            content.add_widget(
                MDLabel(
                    text=self._translate("settings_currency_title"),
                    theme_text_color="Custom",
                    text_color=BRAND_ICE,
                    font_style="Subtitle1",
                    adaptive_height=True,
                )
            )
            content.add_widget(
                MDLabel(
                    text=self._translate("settings_currency_hint"),
                    theme_text_color="Hint",
                    font_style="Caption",
                    adaptive_height=True,
                )
            )

            currency_row = MDBoxLayout(
                orientation="horizontal",
                spacing=dp(8),
                size_hint_y=None,
                height=dp(42),
            )
            for code in SUPPORTED_DISPLAY_CURRENCIES:
                button = MDRaisedButton(
                    text=code,
                    size_hint_x=1,
                    on_release=lambda _button, selected=code: (
                        self._on_set_display_currency(selected)
                    ),
                )
                self._currency_buttons[code] = button
                currency_row.add_widget(button)
            content.add_widget(currency_row)

            rates_card = MDCard(
                orientation="vertical",
                padding=[dp(12), dp(10), dp(12), dp(10)],
                spacing=dp(6),
                size_hint_y=None,
                height=dp(270),
                radius=[dp(14), dp(14), dp(14), dp(14)],
                elevation=2,
                md_bg_color=self._card_bg(),
            )
            rates_card.add_widget(
                MDLabel(
                    text=self._translate("settings_currency_rates_title"),
                    theme_text_color="Custom",
                    text_color=BRAND_ICE,
                    font_style="Subtitle2",
                    size_hint_y=None,
                    height=dp(28),
                )
            )
            for code in SUPPORTED_DISPLAY_CURRENCIES:
                rate_label = MDLabel(
                    text="",
                    theme_text_color="Primary",
                    font_style="Body2",
                    halign="center",
                    valign="middle",
                    size_hint_y=None,
                    height=dp(32),
                )
                rate_label.bind(
                    size=lambda widget, size: setattr(widget, "text_size", size)
                )
                self._currency_rate_labels[code] = rate_label
                rates_card.add_widget(rate_label)

            auto_row = MDBoxLayout(
                orientation="horizontal",
                size_hint_y=None,
                height=dp(42),
            )
            self._currency_auto_button = MDRaisedButton(
                text="",
                size_hint_x=1,
                on_release=lambda *_: self._on_toggle_auto_update(),
            )
            auto_row.add_widget(self._currency_auto_button)
            rates_card.add_widget(auto_row)
            self._currency_status = MDLabel(
                text="",
                theme_text_color="Hint",
                font_style="Caption",
                halign="center",
                valign="middle",
                size_hint_y=None,
                height=dp(54),
            )
            self._currency_status.bind(
                size=lambda widget, size: setattr(widget, "text_size", size)
            )
            rates_card.add_widget(self._currency_status)
            content.add_widget(rates_card)

            settings_scroll = MDScrollView(
                size_hint=(1, None),
                height=max(dp(300), min(dp(560), Window.height * 0.68)),
                do_scroll_x=False,
            )
            settings_scroll.add_widget(content)
            self.refresh()
            self._dialog = MDDialog(
                title=self._translate("settings_title"),
                type="custom",
                content_cls=settings_scroll,
                buttons=[
                    MDFlatButton(
                        text=self._translate("close"),
                        on_release=self.close,
                    ),
                ],
            )
            self._dialog.open()
            return True
        except Exception:
            log.exception("Ustawienia aplikacji")
            self.close()
            return False

"""Labor-rate editor dialog isolated from the mobile application shell."""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping
from typing import Any

from tpof.labor import RATE_CONFIG_FIELDS

log = logging.getLogger(__name__)


class LaborRatesDialogController:
    """Owns labor-rate widgets and delegates persistent state to the app."""

    def __init__(
        self,
        *,
        translate: Callable[..., str],
        get_values: Callable[[], Mapping[str, object]],
        save_values: Callable[[Mapping[str, object]], None],
        reset_values: Callable[[], None],
        clear_field_error: Callable[[Any], None],
        mark_field_error: Callable[[Any], None],
        numeric_input_filter: Callable[..., Any],
        invalidate_results: Callable[[], None],
        show_message: Callable[[str], None],
        on_opened: Callable[[], None],
        on_saved: Callable[[], None],
        on_reset: Callable[[], None],
        report_exception: Callable[[Exception, str], None],
    ) -> None:
        self._translate = translate
        self._get_values = get_values
        self._save_values = save_values
        self._reset_values = reset_values
        self._clear_field_error = clear_field_error
        self._mark_field_error = mark_field_error
        self._numeric_input_filter = numeric_input_filter
        self._invalidate_results = invalidate_results
        self._show_message = show_message
        self._on_opened = on_opened
        self._on_saved = on_saved
        self._on_reset = on_reset
        self._report_exception = report_exception

        self._dialog: Any | None = None
        self._fields: dict[str, Any] = {}

    @property
    def is_open(self) -> bool:
        return self._dialog is not None

    def close(self, *_args: object) -> None:
        if self._dialog is not None:
            self._dialog.dismiss()
        self._dialog = None
        self._fields = {}

    def rate_text_values(self) -> dict[str, str]:
        values = self._get_values()
        return {key: str(values.get(key, "")) for key in RATE_CONFIG_FIELDS}

    def open(self) -> bool:
        """Build and open the dialog. Kivy imports stay lazy for unit tests."""

        self.close()
        try:
            from kivy.metrics import dp
            from kivy.uix.scrollview import ScrollView
            from kivymd.uix.boxlayout import MDBoxLayout
            from kivymd.uix.button import MDFlatButton, MDRaisedButton
            from kivymd.uix.dialog import MDDialog
            from kivymd.uix.label import MDLabel
            from kivymd.uix.textfield import MDTextField

            outer = MDBoxLayout(
                orientation="vertical",
                spacing=dp(8),
                size_hint_y=None,
                height=dp(540),
            )
            outer.add_widget(
                MDLabel(
                    text=self._translate("labor_rates_intro"),
                    theme_text_color="Hint",
                    font_style="Caption",
                    adaptive_height=True,
                )
            )
            scroll = ScrollView()
            form = MDBoxLayout(
                orientation="vertical",
                spacing=dp(8),
                padding=[0, dp(4), dp(8), dp(8)],
                size_hint_y=None,
            )
            form.bind(minimum_height=form.setter("height"))
            values = self.rate_text_values()
            for key in RATE_CONFIG_FIELDS:
                field = MDTextField(
                    hint_text=self._translate(f"labor_rate_{key}"),
                    text=values.get(key, ""),
                    input_filter=(
                        "int" if key == "workdays_per_week" else self._numeric_input_filter
                    ),
                    size_hint_y=None,
                    height=dp(62),
                )
                field.bind(text=lambda widget, _value: self._clear_field_error(widget))
                self._fields[key] = field
                form.add_widget(field)
            scroll.add_widget(form)
            outer.add_widget(scroll)

            self._dialog = MDDialog(
                title=self._translate("labor_rates_title"),
                type="custom",
                content_cls=outer,
                buttons=[
                    MDFlatButton(
                        text=self._translate("labor_rates_factory"),
                        on_release=self.reset,
                    ),
                    MDFlatButton(
                        text=self._translate("cancel"),
                        on_release=self.close,
                    ),
                    MDRaisedButton(
                        text=self._translate("save"),
                        on_release=self.save,
                    ),
                ],
            )
            self._dialog.open()
            self._on_opened()
            return True
        except Exception as exc:
            self._report_exception(exc, "open_labor_rates")
            log.exception("Formularz stawek robocizny")
            self.close()
            self._show_message(self._translate("calc_error", error=exc))
            return False

    def save(self, *_args: object) -> bool:
        values = {key: field.text for key, field in self._fields.items()}
        try:
            self._save_values(values)
        except ValueError as exc:
            message = str(exc)
            self._mark_errors(message)
            self._show_message(self._translate("labor_rates_invalid", message=message))
            return False
        self._invalidate_results()
        self.close()
        self._show_message(self._translate("labor_rates_saved"))
        self._on_saved()
        return True

    def reset(self, *_args: object) -> None:
        self._reset_values()
        values = self.rate_text_values()
        for key, field in self._fields.items():
            field.text = values.get(key, "")
            self._clear_field_error(field)
        self._invalidate_results()
        self._show_message(self._translate("labor_rates_reset"))
        self._on_reset()

    def _mark_errors(self, message: str) -> None:
        marked = False
        for key, field in self._fields.items():
            if key in message:
                self._mark_field_error(field)
                marked = True
        if not marked:
            for field in self._fields.values():
                self._mark_field_error(field)

"""Custom-product editor isolated from the mobile application shell."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from tpof.core import Product, list_categories
from tpof.mobile.user_data import CustomProductStore, create_custom_product

log = logging.getLogger(__name__)

CUSTOM_PRODUCT_FIELD_KEYS = (
    "nazwa",
    "kategoria",
    "wilgotnosc",
    "t_zam",
    "c1",
    "c2",
    "l1",
    "bialko",
    "tluszcz",
    "weglowodany",
    "blonnik",
    "popiol",
)


class CustomProductDialogController:
    """Owns the custom-product form, validation and local persistence."""

    def __init__(
        self,
        *,
        translate: Callable[..., str],
        is_pro: Callable[[], bool],
        get_product_limit: Callable[[], int],
        store: CustomProductStore,
        catalog: dict[str, list[Product]],
        categories: list[str],
        get_selected_category: Callable[[], str | None],
        select_saved_product: Callable[[Product], None],
        numeric_input_filter: Callable[..., Any],
        clear_field_error: Callable[[Any], None],
        mark_field_error: Callable[[Any, str | None], None],
        show_message: Callable[[str], None],
        log_event: Callable[..., None],
        record_exception: Callable[[Exception, str], None],
    ) -> None:
        self._translate = translate
        self._is_pro = is_pro
        self._get_product_limit = get_product_limit
        self._store = store
        self._catalog = catalog
        self._categories = categories
        self._get_selected_category = get_selected_category
        self._select_saved_product = select_saved_product
        self._numeric_input_filter = numeric_input_filter
        self._clear_field_error = clear_field_error
        self._mark_field_error = mark_field_error
        self._show_message = show_message
        self._log_event = log_event
        self._record_exception = record_exception

        self._dialog: Any | None = None
        self._fields: dict[str, Any] = {}

    @property
    def is_open(self) -> bool:
        return self._dialog is not None

    def field_specs(self) -> list[tuple[str, str, Any | None, str]]:
        selected_category = self._get_selected_category() or ""
        return [
            ("nazwa", "custom_name", None, ""),
            ("kategoria", "custom_category", None, selected_category),
            ("wilgotnosc", "custom_moisture", self._numeric_input_filter, ""),
            ("t_zam", "custom_tzam", self._numeric_input_filter, ""),
            ("c1", "custom_c1", self._numeric_input_filter, ""),
            ("c2", "custom_c2", self._numeric_input_filter, ""),
            ("l1", "custom_l1", self._numeric_input_filter, ""),
            ("bialko", "custom_protein", self._numeric_input_filter, ""),
            ("tluszcz", "custom_fat", self._numeric_input_filter, ""),
            ("weglowodany", "custom_carbs", self._numeric_input_filter, ""),
            ("blonnik", "custom_fiber", self._numeric_input_filter, ""),
            ("popiol", "custom_ash", self._numeric_input_filter, ""),
        ]

    def open(self) -> bool:
        if not self._is_pro():
            self._show_message(self._translate("custom_product_pro"))
            return False
        limit = max(1, self._get_product_limit())
        if self._store.count() >= limit:
            self._show_message(
                self._translate(
                    "custom_product_limit",
                    limit=limit,
                )
            )
            return False

        self.close()
        try:
            from kivy.metrics import dp
            from kivy.uix.scrollview import ScrollView
            from kivymd.uix.boxlayout import MDBoxLayout
            from kivymd.uix.button import MDFlatButton, MDRaisedButton
            from kivymd.uix.dialog import MDDialog
            from kivymd.uix.textfield import MDTextField

            outer = MDBoxLayout(
                orientation="vertical",
                size_hint_y=None,
                height=dp(520),
            )
            scroll = ScrollView()
            form = MDBoxLayout(
                orientation="vertical",
                spacing=dp(8),
                padding=[0, dp(4), dp(8), dp(8)],
                size_hint_y=None,
            )
            form.bind(minimum_height=form.setter("height"))
            for key, label_key, input_filter, value in self.field_specs():
                field = MDTextField(
                    hint_text=self._translate(label_key),
                    text=value,
                    input_filter=input_filter,
                    size_hint_y=None,
                    height=dp(62),
                )
                field.bind(
                    text=lambda widget, _value: self._clear_field_error(widget)
                )
                self._fields[key] = field
                form.add_widget(field)
            scroll.add_widget(form)
            outer.add_widget(scroll)

            self._dialog = MDDialog(
                title=self._translate("custom_product_title"),
                type="custom",
                content_cls=outer,
                buttons=[
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
            self._log_event(
                "settings_opened",
                {"section": "custom_product"},
            )
            return True
        except Exception as exc:
            self._record_exception(exc, "open_custom_product")
            log.exception("Formularz własnego produktu")
            self.close()
            self._show_message(self._translate("calc_error", error=exc))
            return False

    def close(self, *_args: object) -> None:
        if self._dialog is not None:
            self._dialog.dismiss()
        self._dialog = None
        self._fields = {}

    def save(self, *_args: object) -> bool:
        values = {key: field.text for key, field in self._fields.items()}
        try:
            product = create_custom_product(values)
            self._store.upsert(product)
        except ValueError as exc:
            field = self._fields.get(str(exc))
            if field is not None:
                self._mark_field_error(
                    field,
                    self._translate("custom_required"),
                )
            self._show_message(self._translate("custom_required"))
            return False
        except OSError as exc:
            self._record_exception(exc, "save_custom_product")
            self._show_message(self._translate("calc_error", error=exc))
            return False

        self._store.merge_into(self._catalog)
        self._categories[:] = list_categories(self._catalog)
        self._select_saved_product(product)
        self.close()
        self._show_message(self._translate("custom_product_saved"))
        self._log_event("custom_product_saved")
        return True

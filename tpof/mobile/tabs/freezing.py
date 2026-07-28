"""Mobile freezing-tab view boundary, state and calculation workflow."""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from tpof.core import (
    FreezingInputs,
    FreezingResults,
    Product,
    calculate_freezing,
    find_product,
)
from tpof.mobile.catalog import (
    _mobile_product_names,
    _ordered_mobile_categories,
    _search_product_names,
)
from tpof.mobile.constants import (
    ABSOLUTE_ZERO_C,
    STAGE_COLORS,
    TEMP_HIGH_ERROR_C,
    TEMP_HIGH_STRONG_WARNING_C,
    TEMP_HIGH_WARNING_C,
    TEMP_LOW_STRONG_WARNING_C,
    TEMP_LOW_WARNING_C,
)
from tpof.mobile.tabs.freezing_view import (
    FreezingStageView,
    FreezingTabView,
    FreezingTabViewCompositionMixin,
)

__all__ = [
    "FreezingStageView",
    "FreezingTabController",
    "FreezingTabView",
]

log = logging.getLogger(__name__)


class FreezingTabController(FreezingTabViewCompositionMixin):
    """Own the freezing tab's view, selection, validation and results."""

    def __init__(
        self,
        *,
        catalog: dict[str, list[Product]],
        categories: list[str],
        translate: Callable[..., str],
        display_category: Callable[[str | None], str],
        card_bg: Callable[[], Any],
        total_color: Any,
        numeric_input_filter: Callable[..., Any],
        register_themed_card: Callable[[Any], None],
        bind_keyboard_scroll: Callable[[tuple[Any, ...], Any], None],
        style_button: Callable[[Any, str], None],
        clear_field_error: Callable[[Any], None],
        mark_field_error: Callable[[Any, str | None], None],
        show_message: Callable[[str], None],
        log_event: Callable[[str, Mapping[str, object] | None], None],
        record_exception: Callable[[BaseException, str], None],
        ensure_product_access: Callable[[str, str], bool],
        is_product_selectable: Callable[[int], bool],
        recent_products: Callable[[str, Sequence[str]], Sequence[str]],
        add_recent_product: Callable[[str, str], None],
        is_custom_product: Callable[[str, str], bool],
        resolve_product_image: Callable[[str], str | None],
        on_add_custom_product: Callable[[], None],
        on_export_pdf: Callable[[], None],
        menu_factory: Callable[..., Any],
        is_compact: Callable[[], bool],
        menu_text_color: Callable[[], Any],
        divider_color: Callable[[], Any],
        hints_enabled: Callable[[], bool],
    ) -> None:
        self._catalog = catalog
        self._categories = categories
        self._translate = translate
        self._display_category = display_category
        self._card_bg = card_bg
        self._total_color = total_color
        self._numeric_input_filter = numeric_input_filter
        self._register_themed_card = register_themed_card
        self._bind_keyboard_scroll = bind_keyboard_scroll
        self._style_button = style_button
        self._clear_field_error = clear_field_error
        self._mark_field_error = mark_field_error
        self._show_message = show_message
        self._log_event = log_event
        self._record_exception = record_exception
        self._ensure_product_access = ensure_product_access
        self._is_product_selectable = is_product_selectable
        self._recent_products = recent_products
        self._add_recent_product = add_recent_product
        self._is_custom_product = is_custom_product
        self._resolve_product_image = resolve_product_image
        self._on_add_custom_product = on_add_custom_product
        self._on_export_pdf = on_export_pdf
        self._menu_factory = menu_factory
        self._is_compact = is_compact
        self._menu_text_color = menu_text_color
        self._divider_color = divider_color
        self._hints_enabled = hints_enabled

        self.selected_category: str | None = None
        self.selected_product: str | None = None
        self.mass_unit = "kg"
        self.last_results: FreezingResults | None = None
        self.view: FreezingTabView | None = None

        self._category_menu: Any | None = None
        self._product_dialog: Any | None = None
        self._product_search_field: Any | None = None
        self._product_results_list: Any | None = None
        self._product_dialog_names: list[str] = []
        self._product_dialog_indexes: dict[str, int] = {}

    @property
    def scroll(self) -> Any | None:
        """Return the built tab scroll widget."""

        return self.view.scroll if self.view is not None else None

    def hint_field_items(self) -> tuple[tuple[Any, str], ...]:
        """Return the freezing fields and their contextual hint keys."""

        if self.view is None:
            return ()
        return (
            (self.view.mass_input, "hint_mass"),
            (self.view.temp_start_input, "hint_temp_start"),
            (self.view.temp_end_input, "hint_temp_end"),
            (self.view.time_input, "hint_time"),
        )

    def total_text(self, total: float | None = None) -> str:
        value = "—" if total is None else f"{total:.2f}"
        return self._translate("total_power", value=value)

    def set_custom_product_available(self, available: bool) -> None:
        if self.view is not None:
            self.view.add_product_button.opacity = 1 if available else 0.72

    def set_mass_unit(self, unit: str) -> None:
        self.mass_unit = "t" if unit == "t" else "kg"
        if self.view is not None:
            self.view.unit_button.text = self.mass_unit
            self._style_button(self.view.unit_button, "ice")

    def toggle_mass_unit(self) -> None:
        self.set_mass_unit("t" if self.mass_unit == "kg" else "kg")

    def show_product_image(self, image_path: str | None) -> None:
        if self.view is None:
            return
        self.view.image_box.clear_widgets()
        if image_path:
            self.view.product_image.source = image_path
            self.view.product_image.opacity = 1
            self.view.image_box.add_widget(self.view.product_image)
            return
        self.view.product_image.source = ""
        self.view.product_image.opacity = 0
        self.view.image_box.add_widget(self.view.image_placeholder)

    def select_category(self, category: str) -> None:
        """Select a category and clear a stale product selection."""

        self.selected_category = category
        self.selected_product = None
        if self.view is not None:
            self.view.category_button.text = self._display_category(category)
            self.view.product_button.text = self._translate("choose_product")
            self.view.product_button.disabled = False
            self.view.category_error_line.opacity = 0
            self.view.product_error_line.opacity = 0
            self.show_product_image(None)
        if self._category_menu is not None:
            self._category_menu.dismiss()

    def select_product(self, name: str, *, image_path: str | None = None) -> None:
        """Select a product in the active category."""

        if self.selected_category is None:
            return
        self.selected_product = name
        self._add_recent_product(self.selected_category, name)
        if self.view is not None:
            self.view.product_button.text = name
            self.view.product_error_line.opacity = 0
            resolved = (
                image_path
                if image_path is not None
                else self._resolve_product_image(name)
            )
            self.show_product_image(resolved)
        self.close_product_dialog()

    def select_saved_product(self, product: Product) -> None:
        """Select a newly persisted custom product without resolving an image."""

        self.select_category(product.kategoria)
        self.selected_product = product.nazwa
        self._add_recent_product(product.kategoria, product.nazwa)
        if self.view is not None:
            self.view.product_button.text = product.nazwa
            self.show_product_image(None)

    def open_category_menu(self, caller: Any) -> None:
        from kivy.metrics import dp
        from kivymd.uix.menu import MDDropdownMenu

        item_height = dp(46 if self._is_compact() else 52)
        featured, remaining = _ordered_mobile_categories(
            self._categories,
            self._display_category,
        )
        ordered = featured + remaining
        items = [
            {
                "text": self._display_category(category),
                "viewclass": "OneLineListItem",
                "height": item_height,
                "theme_text_color": "Custom",
                "text_color": self._menu_text_color(),
                "on_release": lambda value=category: self.select_category(value),
            }
            for category in ordered
        ]
        if featured and remaining:
            items.insert(
                len(featured),
                {
                    "viewclass": "MDSeparator",
                    "height": dp(1),
                    "color": self._divider_color(),
                },
            )
        self._category_menu = self._menu_factory(
            caller,
            items,
            3.7,
            dp(390),
            dp,
            MDDropdownMenu,
        )
        self._category_menu.open()

    def open_product_menu(self, _caller: Any) -> None:
        from kivy.core.window import Window
        from kivy.metrics import dp
        from kivy.uix.scrollview import ScrollView
        from kivymd.uix.boxlayout import MDBoxLayout
        from kivymd.uix.button import MDFlatButton
        from kivymd.uix.dialog import MDDialog
        from kivymd.uix.list import MDList
        from kivymd.uix.textfield import MDTextField

        if not self.selected_category:
            return
        self.close_product_dialog()
        self._product_dialog_names = _mobile_product_names(
            self._catalog,
            self.selected_category,
        )
        self._product_dialog_indexes = {
            name: index for index, name in enumerate(self._product_dialog_names)
        }
        outer = MDBoxLayout(
            orientation="vertical",
            spacing=dp(8),
            size_hint_y=None,
            height=min(dp(520), max(dp(340), Window.height * 0.66)),
        )
        self._product_search_field = MDTextField(
            hint_text=self._translate("search_products"),
            icon_right="magnify",
            mode="rectangle",
            size_hint_y=None,
            height=dp(58),
        )
        outer.add_widget(self._product_search_field)
        results_scroll = ScrollView(do_scroll_x=False)
        self._product_results_list = MDList()
        results_scroll.add_widget(self._product_results_list)
        outer.add_widget(results_scroll)
        self._product_dialog = MDDialog(
            title=self._translate("product_picker_title"),
            type="custom",
            content_cls=outer,
            buttons=[
                MDFlatButton(
                    text=self._translate("close"),
                    on_release=lambda *_: self.close_product_dialog(),
                )
            ],
        )
        self._product_search_field.bind(
            text=lambda _field, value: self.refresh_product_search_results(value)
        )
        self.refresh_product_search_results("")
        self._product_dialog.open()

    def _add_product_search_item(self, name: str, item_height: Any) -> None:
        from kivymd.uix.list import OneLineListItem

        if self._product_results_list is None:
            return
        index = self._product_dialog_indexes.get(name, 10**9)
        allowed = self._is_product_selectable(index)
        item = OneLineListItem(
            text=(
                name
                if allowed
                else f"{name}{self._translate('locked_suffix')}"
            ),
            height=item_height,
            theme_text_color="Custom",
            text_color=(
                self._menu_text_color()
                if allowed
                else (0.55, 0.58, 0.62, 1)
            ),
            on_release=(
                (lambda *_args, value=name: self.select_product(value))
                if allowed
                else (lambda *_args: self.on_locked_product())
            ),
        )
        self._product_results_list.add_widget(item)

    def _add_product_search_heading(self, text: str, dp: Any) -> None:
        from kivymd.uix.label import MDLabel

        if self._product_results_list is None:
            return
        self._product_results_list.add_widget(
            MDLabel(
                text=text,
                size_hint_y=None,
                height=dp(34),
                font_style="Caption",
                theme_text_color="Secondary",
                padding=(dp(12), 0),
            )
        )

    def refresh_product_search_results(self, query: str) -> None:
        from kivy.metrics import dp

        if self._product_results_list is None:
            return
        self._product_results_list.clear_widgets()
        names = _search_product_names(self._product_dialog_names, query)
        item_height = dp(46 if self._is_compact() else 52)
        if not names:
            self._add_product_search_heading(
                self._translate("no_products_found"),
                dp,
            )
            return
        if not str(query or "").strip():
            recent = list(
                self._recent_products(
                    self.selected_category or "",
                    self._product_dialog_names,
                )
            )[:4]
            if recent:
                self._add_product_search_heading(
                    self._translate("recent_products"),
                    dp,
                )
                for name in recent:
                    self._add_product_search_item(name, item_height)
                self._add_product_search_heading(
                    self._translate("all_products"),
                    dp,
                )
        for name in names:
            self._add_product_search_item(name, item_height)

    def close_product_dialog(self) -> None:
        if self._product_dialog is not None:
            self._product_dialog.dismiss()
        self._product_dialog = None
        self._product_search_field = None
        self._product_results_list = None

    def on_locked_product(self) -> None:
        self.close_product_dialog()
        self._show_message(self._translate("product_locked"))

    def clear_validation(self) -> None:
        if self.view is None:
            return
        self.view.category_error_line.opacity = 0
        self.view.product_error_line.opacity = 0
        for field in self.view.input_fields:
            self._clear_field_error(field)

    def _parse_required_field(self, field: Any, name_key: str) -> float:
        name = self._translate(name_key)
        raw = (getattr(field, "text", "") or "").strip()
        if not raw:
            self._mark_field_error(field, None)
            raise ValueError(self._translate("invalid_field", name=name))
        try:
            return float(raw.replace(",", "."))
        except (TypeError, ValueError, AttributeError) as exc:
            message = self._translate("invalid_field", name=name)
            self._mark_field_error(field, message)
            raise ValueError(message) from exc

    def temperature_warning(self, field_name: str, value: float) -> str | None:
        if value >= TEMP_HIGH_STRONG_WARNING_C:
            return self._translate(
                "temperature_warning_high_strong",
                field=field_name,
                value=value,
            )
        if value >= TEMP_HIGH_WARNING_C:
            return self._translate(
                "temperature_warning_high",
                field=field_name,
                value=value,
            )
        if value <= TEMP_LOW_STRONG_WARNING_C:
            return (
                self._translate(
                    "temperature_warning_low_strong",
                    field=field_name,
                    value=value,
                )
                + " "
                + self._translate("temperature_warning_co2")
            )
        if value <= TEMP_LOW_WARNING_C:
            return self._translate(
                "temperature_warning_low",
                field=field_name,
                value=value,
            )
        return None

    def validate_temperature(
        self,
        field: Any,
        field_name: str,
        value: float,
    ) -> str | None:
        if value < ABSOLUTE_ZERO_C:
            message = self._translate(
                "temperature_error_absolute",
                field=field_name,
            )
            self._mark_field_error(field, message)
            raise ValueError(message)
        if value > TEMP_HIGH_ERROR_C:
            message = self._translate(
                "temperature_error_high",
                field=field_name,
                limit=TEMP_HIGH_ERROR_C,
            )
            self._mark_field_error(field, message)
            raise ValueError(message)
        return self.temperature_warning(field_name, value)

    def calculate(self) -> bool:
        """Validate the form, calculate freezing demand and render the result."""

        if self.view is None:
            return False
        self.clear_validation()
        self._log_event("calculation_started", {"calculator": "freezing"})
        try:
            if not self.selected_category:
                self.view.category_error_line.opacity = 1
                self.view.product_error_line.opacity = 1
                self.view.scroll.scroll_y = 1
                self._show_message(self._translate("pick_product_error"))
                return False
            if not self.selected_product:
                self.view.product_error_line.opacity = 1
                self.view.scroll.scroll_y = 1
                self._show_message(self._translate("pick_product_error"))
                return False
            product = find_product(
                self._catalog,
                self.selected_category,
                self.selected_product,
            )
            if product is None:
                self.view.product_error_line.opacity = 1
                self._show_message(self._translate("missing_product_error"))
                return False
            if not self._ensure_product_access(
                self.selected_category,
                self.selected_product,
            ):
                return False

            mass = self._parse_required_field(
                self.view.mass_input,
                "field_mass",
            )
            if mass <= 0:
                message = self._translate(
                    "invalid_field",
                    name=self._translate("field_mass"),
                )
                self._mark_field_error(self.view.mass_input, message)
                raise ValueError(message)
            if self.mass_unit == "t":
                mass *= 1000.0

            temp_start = self._parse_required_field(
                self.view.temp_start_input,
                "field_temp_start",
            )
            temp_end = self._parse_required_field(
                self.view.temp_end_input,
                "field_temp_end",
            )
            warnings = [
                warning
                for warning in (
                    self.validate_temperature(
                        self.view.temp_start_input,
                        self._translate("field_temp_start"),
                        temp_start,
                    ),
                    self.validate_temperature(
                        self.view.temp_end_input,
                        self._translate("field_temp_end"),
                        temp_end,
                    ),
                )
                if warning
            ]
            if warnings:
                self._show_message(warnings[0])

            time_h = self._parse_required_field(
                self.view.time_input,
                "field_time",
            )
            if time_h <= 0:
                message = self._translate(
                    "invalid_field",
                    name=self._translate("field_time"),
                )
                self._mark_field_error(self.view.time_input, message)
                raise ValueError(message)

            inputs = FreezingInputs(
                masa_kg=mass,
                T_pocz_C=temp_start,
                T_konc_C=temp_end,
                czas_h=time_h,
            )
            results = calculate_freezing(inputs, product)
            self.last_results = results
            self.render_results(results)
            self._log_event(
                "calculation_finished",
                {
                    "calculator": "freezing",
                    "mass_unit": self.mass_unit,
                    "custom_product": self._is_custom_product(
                        product.kategoria,
                        product.nazwa,
                    ),
                },
            )
            return True
        except ValueError as exc:
            self._show_message(str(exc))
            return False
        except Exception as exc:  # pragma: no cover - UI safety net
            self._record_exception(exc, "calculate_freezing")
            log.exception("Freezing calculation failed")
            self._show_message(self._translate("calc_error", error=exc))
            return False

    def render_results(
        self,
        results: FreezingResults,
        *,
        scroll: bool = True,
    ) -> None:
        if self.view is None:
            return
        total = results.P_total_kW or 0.0
        self.view.total_label.text = self.total_text(total)
        values = {
            "schladzanie": results.P_schladzanie_kW,
            "zamrozenie": results.P_zamrozenie_kW,
            "domrozenie": results.P_domrozenie_kW,
        }
        for key, value in values.items():
            percent = (value / total * 100.0) if total > 0 else 0.0
            stage = self.view.stages[key]
            stage.bar.color = STAGE_COLORS[key]
            stage.bar.value = percent
            stage.value_label.text = f"{value:.2f} kW ({percent:.0f}%)"
        if scroll:
            try:
                from kivy.metrics import dp

                self.view.scroll.scroll_to(
                    self.view.results_card,
                    padding=dp(12),
                    animate=True,
                )
            except Exception:  # pragma: no cover - cosmetic only
                pass

    def reset_inputs(self) -> None:
        if self.view is None:
            return
        for field in self.view.input_fields:
            field.text = ""
        self.view.total_label.text = self.total_text()
        for key, stage in self.view.stages.items():
            stage.bar.value = 0
            # KivyMD 1.2 can leave the last progress-fill texture visible on
            # Android after assigning an exact zero. Hiding the fill color
            # guarantees an empty bar; render_results restores its stage color.
            stage.bar.color = (*STAGE_COLORS[key][:3], 0)
            stage.value_label.text = "—"
        self.last_results = None
        self.clear_validation()

    def refresh_texts(self) -> None:
        if self.view is None:
            return
        view = self.view
        view.product_title_label.text = self._translate("product")
        view.category_button.text = (
            self._display_category(self.selected_category)
            if self.selected_category
            else self._translate("choose_category")
        )
        view.product_button.text = (
            self.selected_product or self._translate("choose_product")
        )
        view.image_placeholder_label.text = self._translate("image_placeholder")
        view.product_hint_label.text = self._translate("product_hint")
        view.params_title_label.text = self._translate("params")
        view.mass_input.hint_text = self._translate("mass")
        view.temp_start_input.hint_text = self._translate("temperature_start")
        view.temp_end_input.hint_text = self._translate("temperature_end")
        view.time_input.hint_text = self._translate("work_time")
        view.calculate_button.text = self._translate("calculate")
        view.clear_button.text = self._translate("clear")
        view.results_title_label.text = self._translate("result")
        for key, label_key in (
            ("schladzanie", "cooling"),
            ("zamrozenie", "freezing"),
            ("domrozenie", "deep_freezing"),
        ):
            view.stages[key].name_label.text = self._translate(label_key)
        if self.last_results is not None:
            self.render_results(self.last_results, scroll=False)
        else:
            view.total_label.text = self.total_text()

    def apply_theme(self) -> None:
        if self.view is None:
            return
        self.set_mass_unit(self.mass_unit)
        for button, variant in (
            (self.view.category_button, "primary"),
            (self.view.product_button, "primary"),
            (self.view.calculate_button, "primary"),
            (self.view.pdf_button, "ice"),
            (self.view.clear_button, "dark"),
        ):
            self._style_button(button, variant)

    def apply_layout(self, metrics: Mapping[str, Any]) -> None:
        """Apply shared responsive metrics to the complete freezing view."""

        if self.view is None:
            return
        from kivy.metrics import dp

        view = self.view
        compact = bool(metrics["compact"])
        card_padding = [
            metrics["card_pad_x"],
            metrics["card_pad_top"],
            metrics["card_pad_x"],
            metrics["card_pad_bottom"],
        ]
        view.content.padding = [
            metrics["content_pad"],
            metrics["content_top"],
            metrics["content_pad"],
            metrics["content_bottom"],
        ]
        view.content.spacing = metrics["content_spacing"]
        view.product_card.padding = card_padding
        view.product_card.spacing = dp(10 if compact else 12)
        view.product_card.height = metrics["product_card_h"]
        view.product_title_label.height = metrics["title_h"]
        view.product_title_label.font_size = f'{metrics["title_sp"]}sp'
        view.product_title_row.height = metrics["title_h"]
        view.add_product_button.width = metrics["toolbar_btn_w"]
        view.add_product_button.icon_size = f'{metrics["toolbar_btn_sp"]}sp'
        view.product_hint_label.height = metrics["product_hint_h"]
        view.product_hint_label.opacity = 1 if self._hints_enabled() else 0
        view.product_hint_label.font_size = f'{metrics["caption_sp"]}sp'
        view.product_body.orientation = (
            "horizontal" if metrics["product_horizontal"] else "vertical"
        )
        view.product_body.height = metrics["product_body_h"]
        view.product_body.spacing = metrics["product_body_spacing"]
        view.product_controls.spacing = dp(10 if compact else 12)
        view.product_controls.size_hint_x = (
            0.46 if metrics["product_horizontal"] else 1
        )
        view.product_controls.size_hint_y = (
            1 if metrics["product_horizontal"] else None
        )
        view.product_controls.height = metrics["product_controls_h"]
        view.product_controls.padding = [
            0,
            dp(6 if compact else 8),
            0,
            dp(6 if compact else 8),
        ]
        view.image_box.size_hint_x = (
            0.54 if metrics["product_horizontal"] else 1
        )
        view.image_box.size_hint_y = (
            1 if metrics["product_horizontal"] else None
        )
        view.image_box.height = metrics["product_image_h"]
        view.image_placeholder.padding = [
            0,
            metrics["placeholder_top"],
            0,
            metrics["placeholder_bottom"],
        ]
        view.image_placeholder_icon.font_size = (
            f'{metrics["placeholder_icon_sp"]}sp'
        )
        view.image_placeholder_label.font_size = f'{metrics["caption_sp"]}sp'
        for button in (view.category_button, view.product_button):
            button.height = metrics["button_h"]
            button.font_size = f'{metrics["button_sp"]}sp'
        for box in (view.category_field_box, view.product_field_box):
            box.height = metrics["button_h"] + dp(2)
        view.params_card.padding = card_padding
        view.params_card.spacing = metrics["card_spacing"]
        view.params_card.height = metrics["params_h"]
        view.params_title_label.height = metrics["title_h"]
        view.params_title_label.font_size = f'{metrics["title_sp"]}sp'
        view.mass_row.height = metrics["field_h"] + dp(8)
        view.mass_row.spacing = dp(8 if compact else 10)
        view.unit_button.width = metrics["unit_w"]
        view.unit_button.height = metrics["unit_h"]
        view.unit_button.font_size = f'{metrics["body_sp"]}sp'
        for field in view.input_fields:
            field.height = metrics["field_h"]
            field.font_size = f'{metrics["body_sp"]}sp'
        view.results_card.padding = card_padding
        view.results_card.spacing = metrics["results_spacing"]
        view.results_card.height = metrics["results_h"]
        view.results_title_row.height = metrics["title_h"]
        view.results_title_label.font_size = f'{metrics["title_sp"]}sp'
        view.action_row.height = metrics["action_h"]
        view.action_row.spacing = dp(6 if compact else 8)
        view.action_row.padding = [
            0,
            dp(8 if compact else 9),
            0,
            dp(7 if compact else 8),
        ]
        for button in (
            view.calculate_button,
            view.pdf_button,
            view.clear_button,
        ):
            button.height = metrics["action_button_h"]
            button.font_size = f'{metrics["action_sp"]}sp'
        view.total_label.height = metrics["total_h"]
        view.total_label.font_size = f'{metrics["total_sp"]}sp'
        for stage in view.stages.values():
            stage.row.height = metrics["stage_row_h"]
            stage.head.height = metrics["stage_head_h"]
            stage.icon_chip.width = metrics["stage_icon_w"]
            stage.icon_chip.height = metrics["stage_icon_w"]
            if hasattr(stage.icon, "font_size"):
                stage.icon.font_size = f'{metrics["stage_icon_sp"]}sp'
            stage.name_label.font_size = f'{metrics["body_sp"]}sp'
            stage.value_label.font_size = f'{metrics["body_sp"]}sp'

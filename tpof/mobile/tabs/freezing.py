"""Mobile freezing-tab controller and result-presentation boundary."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any

from tpof.core import FreezingResults, Product
from tpof.mobile.constants import STAGE_COLORS
from tpof.mobile.tabs.freezing_products import FreezingProductSelectionMixin
from tpof.mobile.tabs.freezing_view import (
    FreezingStageView,
    FreezingTabView,
    FreezingTabViewCompositionMixin,
)
from tpof.mobile.tabs.freezing_workflow import FreezingCalculationWorkflowMixin

__all__ = [
    "FreezingStageView",
    "FreezingTabController",
    "FreezingTabView",
]

class FreezingTabController(
    FreezingProductSelectionMixin,
    FreezingCalculationWorkflowMixin,
    FreezingTabViewCompositionMixin,
):
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

        self._initialize_product_selection()
        self.mass_unit = "kg"
        self.last_results: FreezingResults | None = None
        self.view: FreezingTabView | None = None

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

    def set_mass_unit(self, unit: str) -> None:
        self.mass_unit = "t" if unit == "t" else "kg"
        if self.view is not None:
            self.view.unit_button.text = self.mass_unit
            self._style_button(self.view.unit_button, "ice")

    def toggle_mass_unit(self) -> None:
        self.set_mass_unit("t" if self.mass_unit == "kg" else "kg")

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

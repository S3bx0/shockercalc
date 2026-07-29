"""Coordinator for the mobile freezing-tab module boundaries."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any

from tpof.core import FreezingResults, Product
from tpof.mobile.tabs.freezing_presentation import FreezingTabPresentationMixin
from tpof.mobile.tabs.freezing_products import FreezingProductSelectionMixin
from tpof.mobile.tabs.freezing_results import FreezingResultsPresentationMixin
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
    FreezingResultsPresentationMixin,
    FreezingTabPresentationMixin,
    FreezingTabViewCompositionMixin,
):
    """Coordinate freezing-tab boundaries and shared UI state."""

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

    def set_mass_unit(self, unit: str) -> None:
        self.mass_unit = "t" if unit == "t" else "kg"
        if self.view is not None:
            self.view.unit_button.text = self.mass_unit
            self._style_button(self.view.unit_button, "ice")

    def toggle_mass_unit(self) -> None:
        self.set_mass_unit("t" if self.mass_unit == "kg" else "kg")

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

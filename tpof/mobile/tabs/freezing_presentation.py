"""Theme and responsive layout presentation for the mobile freezing tab."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any, Protocol, cast

from tpof.mobile.tabs.freezing_view import FreezingTabView


class _MassUnitPresenter(Protocol):
    def set_mass_unit(self, unit: str) -> None: ...

    def result_color(self) -> Any: ...


class FreezingTabPresentationMixin:
    """Apply shared theme and layout state to an already-built freezing view."""

    _style_button: Callable[[Any, str], None]
    _hints_enabled: Callable[[], bool]

    mass_unit: str
    view: FreezingTabView | None

    def apply_theme(self) -> None:
        if self.view is None:
            return
        presenter = cast(_MassUnitPresenter, self)
        self.view.total_label.text_color = presenter.result_color()
        presenter.set_mass_unit(self.mass_unit)
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

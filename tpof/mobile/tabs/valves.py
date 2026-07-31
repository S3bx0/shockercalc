"""Framework-independent presentation logic for the decompression-valves tab."""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping
from typing import Any

from tpof.core import ZAWORY, ValveResults, calculate_decompression_valves
from tpof.mobile.tabs.valves_view import (
    ValvesTabView,
    ValvesTabViewCompositionMixin,
)

log = logging.getLogger(__name__)


class ValvesTabController(ValvesTabViewCompositionMixin):
    """Own the valves tab's state, validation and calculation workflow."""

    def __init__(
        self,
        *,
        translate: Callable[..., str],
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
        can_calculate: Callable[[], bool],
        on_access_denied: Callable[[], None],
        on_buy: Callable[[], None],
        on_watch: Callable[[], None],
        menu_factory: Callable[..., Any],
        is_compact: Callable[[], bool],
        menu_text_color: Callable[[], Any],
    ) -> None:
        self._translate = translate
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
        self._can_calculate = can_calculate
        self._on_access_denied = on_access_denied
        self._on_buy = on_buy
        self._on_watch = on_watch
        self._menu_factory = menu_factory
        self._is_compact = is_compact
        self._menu_text_color = menu_text_color

        self.valve_type = "Maxi Elebar"
        self.input_mode = "K"
        self.last_results: ValveResults | None = None
        self.last_total_flow: float | None = None
        self._type_menu: Any | None = None
        self.view: ValvesTabView | None = None

    @property
    def scroll(self) -> Any | None:
        """Return the tab scroll widget after the view has been built."""

        return None if self.view is None else self.view.scroll

    @staticmethod
    def _dp(value: float) -> float:
        try:
            from kivy.metrics import dp

            return float(dp(value))
        except ImportError:  # pragma: no cover - unit-test host without Kivy
            return value

    def hint_field_items(self) -> tuple[tuple[Any, str], ...]:
        """Expose valve inputs to the app-wide optional hint coordinator."""

        if self.view is None:
            return ()
        return (
            (self.view.volume_input, "hint_valve_volume"),
            (self.view.length_input, "hint_valve_length"),
            (self.view.width_input, "hint_valve_width"),
            (self.view.height_input, "hint_valve_height"),
            (self.view.temp_before_input, "hint_valve_temp_before"),
            (self.view.temp_after_input, "hint_valve_temp_after"),
            (self.view.coolers_input, "hint_valve_coolers"),
            (self.view.flow_input, "hint_valve_flow"),
        )

    def set_input_mode(self, mode: str) -> None:
        """Switch between direct-volume (K) and dimensions (W) input."""

        self.input_mode = "W" if mode == "W" else "K"
        if self.view is None:
            return
        volume_mode = self.input_mode == "K"
        self.view.volume_box.height = self._dp(60) if volume_mode else 0
        self.view.volume_box.opacity = 1 if volume_mode else 0
        self.view.volume_box.disabled = not volume_mode
        self.view.dimensions_box.height = 0 if volume_mode else self._dp(180)
        self.view.dimensions_box.opacity = 0 if volume_mode else 1
        self.view.dimensions_box.disabled = volume_mode
        self.style_mode_buttons()

    def style_mode_buttons(self) -> None:
        if self.view is None:
            return
        volume_mode = self.input_mode == "K"
        self._style_button(
            self.view.volume_mode_button,
            "ice" if volume_mode else "muted",
        )
        self._style_button(
            self.view.dimensions_mode_button,
            "muted" if volume_mode else "ice",
        )

    def open_type_menu(self, caller: Any) -> None:
        """Open the responsive valve-type menu."""

        from kivy.metrics import dp
        from kivymd.uix.menu import MDDropdownMenu

        item_height = dp(46 if self._is_compact() else 52)
        items = [
            {
                "text": name,
                "viewclass": "OneLineListItem",
                "height": item_height,
                "theme_text_color": "Custom",
                "text_color": self._menu_text_color(),
                "on_release": lambda selected=name: self.pick_valve_type(selected),
            }
            for name in ZAWORY
        ]
        self._type_menu = self._menu_factory(
            caller,
            items,
            4.4,
            dp(300),
            dp,
            MDDropdownMenu,
        )
        self._type_menu.open()

    def pick_valve_type(self, name: str) -> None:
        if name not in ZAWORY:
            raise ValueError(f"Unknown valve type: {name}")
        self.valve_type = name
        if self.view is not None:
            self.view.type_button.text = name
        if self._type_menu is not None:
            self._type_menu.dismiss()
        if self.last_results is not None:
            self.calculate()

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

    def _parse_required_field(self, field: Any, name_key: str) -> float:
        raw = (getattr(field, "text", "") or "").strip()
        message = self._invalid_field_message(name_key)
        if not raw:
            self._mark_field_error(field, None)
            raise ValueError(message)
        try:
            return float(raw.replace(",", "."))
        except (TypeError, ValueError, AttributeError) as exc:
            self._mark_field_error(field, message)
            raise ValueError(message) from exc

    def refresh_lock_ui(self, locked: bool) -> None:
        """Show or collapse the access card without owning entitlement policy."""

        if self.view is None:
            return
        self.view.lock_card.height = self._dp(196) if locked else 0
        self.view.lock_card.opacity = 1 if locked else 0
        self.view.lock_card.disabled = not locked

    def render_results(self, results: ValveResults | None) -> None:
        self.last_results = results
        if self.view is None:
            return
        dash = "—"
        self.view.count_label.text = self._translate(
            "valve_count",
            value=dash if results is None else results.ilosc_zaworow,
        )
        self.view.delta_label.text = self._translate(
            "valve_delta_t",
            value=dash if results is None else f"{results.delta_T:.2f}",
        )
        self.view.total_flow_label.text = self._translate(
            "valve_total_flow",
            value=(
                dash
                if results is None or self.last_total_flow is None
                else f"{self.last_total_flow:.1f}"
            ),
        )
        self.view.flow_label.text = self._translate(
            "valve_flow",
            value=dash if results is None else f"{results.Q:.1f}",
        )
        self.view.unit_flow_label.text = self._translate(
            "valve_unit_flow",
            value=dash if results is None else results.przeplyw_zaworu,
        )

    def refresh_texts(self) -> None:
        if self.view is None:
            return
        self.view.locked_label.text = self._translate("valve_locked")
        self.view.buy_button.text = self._translate("valve_buy")
        self.view.watch_button.text = self._translate("valve_watch_ad")
        self.view.title_label.text = self._translate("valve_title")
        self.view.type_button.text = self.valve_type
        self.view.volume_mode_button.text = self._translate("valve_mode_volume")
        self.view.dimensions_mode_button.text = self._translate("valve_mode_dims")
        self.view.volume_input.hint_text = self._translate("valve_volume")
        self.view.length_input.hint_text = self._translate("valve_length")
        self.view.width_input.hint_text = self._translate("valve_width")
        self.view.height_input.hint_text = self._translate("valve_height")
        self.view.temp_before_input.hint_text = self._translate("valve_temp_before")
        self.view.temp_after_input.hint_text = self._translate("valve_temp_after")
        self.view.coolers_input.hint_text = self._translate("valve_coolers")
        self.view.flow_input.hint_text = self._translate("valve_flow_per")
        self.view.calculate_button.text = self._translate("valve_calculate")
        self.view.result_title_label.text = self._translate("valve_result")
        self.render_results(self.last_results)

    def apply_theme(self) -> None:
        if self.view is None:
            return
        for button, variant in (
            (self.view.buy_button, "pro"),
            (self.view.watch_button, "ice"),
            (self.view.type_button, "primary"),
            (self.view.calculate_button, "ice"),
        ):
            self._style_button(button, variant)
        self.style_mode_buttons()

    def calculate(self) -> bool:
        """Validate inputs, calculate valve requirements and render the result."""

        if self.view is None:
            return False
        if not self._can_calculate():
            self._on_access_denied()
            return False

        self.clear_validation()
        self._log_event("calculation_started", {"calculator": "valves"})
        try:
            if self.input_mode == "W":
                length = self._parse_required_field(
                    self.view.length_input,
                    "valve_length",
                )
                width = self._parse_required_field(
                    self.view.width_input,
                    "valve_width",
                )
                height = self._parse_required_field(
                    self.view.height_input,
                    "valve_height",
                )
                volume = length * width * height
            else:
                volume = self._parse_required_field(
                    self.view.volume_input,
                    "valve_volume",
                )
            temp_before = self._parse_required_field(
                self.view.temp_before_input,
                "valve_temp_before",
            )
            temp_after = self._parse_required_field(
                self.view.temp_after_input,
                "valve_temp_after",
            )
            coolers_value = self._parse_required_field(
                self.view.coolers_input,
                "valve_coolers",
            )
            if not coolers_value.is_integer():
                message = self._invalid_field_message("valve_coolers")
                self._mark_field_error(self.view.coolers_input, message)
                raise ValueError(message)
            coolers = int(coolers_value)
            if coolers < 1:
                message = self._translate("valve_coolers_min")
                self._mark_field_error(self.view.coolers_input, message)
                raise ValueError(message)
            flow_per_cooler = self._parse_required_field(
                self.view.flow_input,
                "valve_flow_per",
            )
            if flow_per_cooler <= 0:
                message = self._translate("valve_flow_positive")
                self._mark_field_error(self.view.flow_input, message)
                raise ValueError(message)

            total_flow = flow_per_cooler * coolers
            results = calculate_decompression_valves(
                volume,
                temp_before,
                temp_after,
                total_flow,
                self.valve_type,
            )
            self.last_total_flow = total_flow
            self.render_results(results)
            self._log_event(
                "calculation_finished",
                {"calculator": "valves"},
            )
            return True
        except ValueError as exc:
            self._show_message(str(exc))
            return False
        except Exception as exc:  # pragma: no cover - UI safeguard
            self._record_exception(exc, "calculate_valves")
            log.exception("Obliczenia zaworów")
            self._show_message(self._translate("calc_error", error=exc))
            return False

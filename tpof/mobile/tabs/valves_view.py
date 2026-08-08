"""Kivy view composition for the mobile decompression-valves tab."""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from typing import Any


@dataclass(frozen=True)
class ValvesTabView:
    """Widget references exposed by the valves tab's view boundary."""

    scroll: Any
    lock_card: Any
    locked_label: Any
    buy_button: Any
    watch_button: Any
    input_card: Any
    title_label: Any
    type_button: Any
    volume_mode_button: Any
    dimensions_mode_button: Any
    volume_box: Any
    volume_input: Any
    dimensions_box: Any
    length_input: Any
    width_input: Any
    height_input: Any
    temp_before_input: Any
    temp_after_input: Any
    coolers_input: Any
    flow_input: Any
    calculate_button: Any
    result_card: Any
    result_title_label: Any
    count_label: Any
    delta_label: Any
    total_flow_label: Any
    flow_label: Any
    unit_flow_label: Any

    @property
    def input_fields(self) -> tuple[Any, ...]:
        """Return inputs in keyboard-navigation order."""

        return (
            self.volume_input,
            self.length_input,
            self.width_input,
            self.height_input,
            self.temp_before_input,
            self.temp_after_input,
            self.coolers_input,
            self.flow_input,
        )


class ValvesTabViewCompositionMixin:
    """Build the Kivy widget tree while the controller owns behavior."""

    view: ValvesTabView | None

    def build(self: Any) -> ValvesTabView:
        """Create the complete valves tab and retain its typed widget boundary."""

        from kivy.metrics import Metrics, dp
        from kivymd.uix.boxlayout import MDBoxLayout
        from kivymd.uix.button import MDRaisedButton
        from kivymd.uix.card import MDCard
        from kivymd.uix.label import MDLabel
        from kivymd.uix.scrollview import MDScrollView
        from kivymd.uix.textfield import MDTextField

        font_scale = max(1.0, min(2.0, float(Metrics.fontscale)))
        large_text = font_scale >= 1.5
        self._large_text_layout = large_text

        def content_h(value: float) -> float:
            return round(value * font_scale, 2)

        def control_sp(value: float) -> str:
            return f"{round(value / sqrt(font_scale), 2)}sp"

        scroll = MDScrollView()
        content = MDBoxLayout(
            orientation="vertical",
            padding=[dp(16), dp(16), dp(16), dp(20)],
            spacing=dp(14),
            size_hint_y=None,
        )
        content.bind(minimum_height=content.setter("height"))

        lock_card = MDCard(
            orientation="vertical",
            padding=dp(14),
            spacing=dp(10),
            size_hint_y=None,
            height=dp(content_h(196)),
            radius=[16, 16, 16, 16],
            elevation=3,
            md_bg_color=self._card_bg(),
        )
        self._register_themed_card(lock_card)
        locked_label = MDLabel(
            text=self._translate("valve_locked"),
            font_style="Subtitle1",
            size_hint_y=None,
            height=dp(content_h(64)),
            theme_text_color="Secondary",
        )
        lock_card.add_widget(locked_label)
        buy_button = MDRaisedButton(
            text=self._translate("valve_buy"),
            icon="cart",
            size_hint_x=1,
            size_hint_y=None,
            height=dp(content_h(50)),
            font_size=control_sp(15),
            on_release=lambda *_: self._on_buy(),
        )
        lock_card.add_widget(buy_button)
        watch_button = MDRaisedButton(
            text=self._translate("valve_watch_ad"),
            icon="play-circle-outline",
            size_hint_x=1,
            size_hint_y=None,
            height=dp(content_h(50)),
            font_size=control_sp(15),
            on_release=lambda *_: self._on_watch(),
        )
        lock_card.add_widget(watch_button)
        content.add_widget(lock_card)

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
            text=self._translate("valve_title"),
            font_style="H6",
            size_hint_y=None,
            height=dp(content_h(36)),
        )
        input_card.add_widget(title_label)
        type_button = MDRaisedButton(
            text=self.valve_type,
            size_hint_x=1,
            size_hint_y=None,
            height=dp(content_h(52)),
            font_size=control_sp(15),
            on_release=lambda caller: self.open_type_menu(caller),
        )
        input_card.add_widget(type_button)

        mode_box = MDBoxLayout(
            orientation="vertical" if large_text else "horizontal",
            spacing=dp(8),
            size_hint_y=None,
            height=dp(content_h(104) if large_text else 48),
        )
        volume_mode_button = MDRaisedButton(
            text=self._translate("valve_mode_volume"),
            size_hint_x=1 if large_text else 0.5,
            size_hint_y=None,
            height=dp(content_h(48)),
            font_size=control_sp(13),
            on_release=lambda *_: self.set_input_mode("K"),
        )
        dimensions_mode_button = MDRaisedButton(
            text=self._translate("valve_mode_dims"),
            size_hint_x=1 if large_text else 0.5,
            size_hint_y=None,
            height=dp(content_h(48)),
            font_size=control_sp(13),
            on_release=lambda *_: self.set_input_mode("W"),
        )
        mode_box.add_widget(volume_mode_button)
        mode_box.add_widget(dimensions_mode_button)
        input_card.add_widget(mode_box)

        volume_input = MDTextField(
            hint_text=self._translate(
                "valve_volume_short" if large_text else "valve_volume"
            ),
            input_filter=self._numeric_input_filter,
        )
        volume_input.size_hint_y = None
        volume_input.height = dp(content_h(60))
        volume_input.font_size = control_sp(16)
        volume_box = MDBoxLayout(
            orientation="vertical",
            size_hint_y=None,
            height=dp(content_h(60)),
        )
        volume_box.add_widget(volume_input)
        input_card.add_widget(volume_box)

        length_input = MDTextField(
            hint_text=self._translate("valve_length"),
            input_filter=self._numeric_input_filter,
        )
        width_input = MDTextField(
            hint_text=self._translate("valve_width"),
            input_filter=self._numeric_input_filter,
        )
        height_input = MDTextField(
            hint_text=self._translate("valve_height"),
            input_filter=self._numeric_input_filter,
        )
        dimensions_box = MDBoxLayout(
            orientation="vertical",
            size_hint_y=None,
            height=dp(content_h(180)),
        )
        for field in (length_input, width_input, height_input):
            field.size_hint_y = None
            field.height = dp(content_h(60))
            field.font_size = control_sp(16)
            dimensions_box.add_widget(field)
        input_card.add_widget(dimensions_box)

        temp_before_input = MDTextField(
            hint_text=self._translate("valve_temp_before"),
            input_filter=self._numeric_input_filter,
        )
        temp_after_input = MDTextField(
            hint_text=self._translate("valve_temp_after"),
            input_filter=self._numeric_input_filter,
        )
        coolers_input = MDTextField(
            hint_text=self._translate("valve_coolers"),
            input_filter="int",
        )
        flow_input = MDTextField(
            hint_text=self._translate("valve_flow_per"),
            input_filter=self._numeric_input_filter,
        )
        for field in (
            temp_before_input,
            temp_after_input,
            coolers_input,
            flow_input,
        ):
            field.size_hint_y = None
            field.height = dp(content_h(60))
            field.font_size = control_sp(16)
            input_card.add_widget(field)

        calculate_button = MDRaisedButton(
            text=self._translate("valve_calculate"),
            icon="calculator-variant",
            size_hint_x=1,
            size_hint_y=None,
            height=dp(content_h(50)),
            font_size=control_sp(15),
            on_release=lambda *_: self.calculate(),
        )
        input_card.add_widget(calculate_button)
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
            text=self._translate("valve_result"),
            font_style="H6",
            size_hint_y=None,
            height=dp(content_h(36)),
        )
        result_card.add_widget(result_title_label)
        count_label = MDLabel(
            text=self._translate("valve_count", value="—"),
            font_style="H6",
            halign="center",
            size_hint_y=None,
            height=dp(content_h(42)),
            theme_text_color="Custom",
            text_color=self.result_color(),
        )
        result_card.add_widget(count_label)
        delta_label = MDLabel(
            text=self._translate("valve_delta_t", value="—"),
            size_hint_y=None,
            height=dp(content_h(30)),
            theme_text_color="Secondary",
        )
        total_flow_label = MDLabel(
            text=self._translate("valve_total_flow", value="—"),
            size_hint_y=None,
            height=dp(content_h(30)),
            theme_text_color="Secondary",
        )
        flow_label = MDLabel(
            text=self._translate("valve_flow", value="—"),
            size_hint_y=None,
            height=dp(content_h(30)),
            theme_text_color="Secondary",
        )
        unit_flow_label = MDLabel(
            text=self._translate("valve_unit_flow", value="—"),
            size_hint_y=None,
            height=dp(content_h(30)),
            theme_text_color="Secondary",
        )
        for label in (
            delta_label,
            total_flow_label,
            flow_label,
            unit_flow_label,
        ):
            result_card.add_widget(label)
        content.add_widget(result_card)

        view = ValvesTabView(
            scroll=scroll,
            lock_card=lock_card,
            locked_label=locked_label,
            buy_button=buy_button,
            watch_button=watch_button,
            input_card=input_card,
            title_label=title_label,
            type_button=type_button,
            volume_mode_button=volume_mode_button,
            dimensions_mode_button=dimensions_mode_button,
            volume_box=volume_box,
            volume_input=volume_input,
            dimensions_box=dimensions_box,
            length_input=length_input,
            width_input=width_input,
            height_input=height_input,
            temp_before_input=temp_before_input,
            temp_after_input=temp_after_input,
            coolers_input=coolers_input,
            flow_input=flow_input,
            calculate_button=calculate_button,
            result_card=result_card,
            result_title_label=result_title_label,
            count_label=count_label,
            delta_label=delta_label,
            total_flow_label=total_flow_label,
            flow_label=flow_label,
            unit_flow_label=unit_flow_label,
        )
        self.view = view
        self._bind_keyboard_scroll(view.input_fields, scroll)
        scroll.add_widget(content)
        self.set_input_mode(self.input_mode)
        self.render_results(None)
        self.apply_theme()
        return view

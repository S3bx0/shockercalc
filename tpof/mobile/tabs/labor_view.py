"""Kivy view composition for the mobile labor-cost tab."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

LABOR_RESULT_LABEL_KEYS = (
    ("labor_cost", "labor_labor_cost"),
    ("travel_cost", "labor_travel_cost"),
    ("lift_cost", "labor_lift_cost"),
    ("container_cost", "labor_container_cost"),
    ("hotel_cost", "labor_hotel_cost"),
    ("allowance_cost", "labor_allowance_cost"),
    ("regenerative_meal_cost", "labor_meal_cost"),
    ("additional_costs_value", "labor_additional_costs"),
)


@dataclass(frozen=True)
class LaborTabView:
    """Widget references exposed by the labor tab's view boundary."""

    scroll: Any
    input_card: Any
    title_label: Any
    hint_label: Any
    people_input: Any
    days_input: Any
    distance_input: Any
    lifts_input: Any
    containers_input: Any
    highways_button: Any
    additional_button: Any
    additional_input: Any
    additional_box: Any
    calculate_button: Any
    rates_button: Any
    result_card: Any
    result_title_label: Any
    total_label: Any
    currency_note: Any
    chart: Any
    chart_hint: Any
    chart_legend: Any
    result_labels: dict[str, tuple[Any, str]]
    travel_mode_label: Any
    travel_details_label: Any

    @property
    def input_fields(self) -> tuple[Any, ...]:
        return (
            self.people_input,
            self.days_input,
            self.distance_input,
            self.lifts_input,
            self.containers_input,
            self.additional_input,
        )


class LaborTabViewCompositionMixin:
    """Build the Kivy widget tree while the controller owns behavior."""

    view: LaborTabView | None

    def build(self: Any) -> LaborTabView:
        """Create the complete labor tab and retain its typed widget boundary."""

        from kivy.metrics import dp
        from kivymd.uix.boxlayout import MDBoxLayout
        from kivymd.uix.button import MDRaisedButton
        from kivymd.uix.card import MDCard
        from kivymd.uix.label import MDLabel
        from kivymd.uix.scrollview import MDScrollView
        from kivymd.uix.textfield import MDTextField

        scroll = MDScrollView()
        content = MDBoxLayout(
            orientation="vertical",
            padding=[dp(16), dp(14), dp(16), dp(18)],
            spacing=dp(14),
            size_hint_y=None,
        )
        content.bind(minimum_height=content.setter("height"))

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
            text=self._translate("labor_title"),
            font_style="H6",
            size_hint_y=None,
            height=dp(36),
        )
        input_card.add_widget(title_label)
        hint_label = MDLabel(
            text=self._translate("labor_hint"),
            font_style="Caption",
            theme_text_color="Hint",
            size_hint_y=None,
            height=dp(38),
        )
        input_card.add_widget(hint_label)

        people_input = MDTextField(
            hint_text=self._translate("labor_people"), input_filter="int"
        )
        days_input = MDTextField(
            hint_text=self._translate("labor_days"), input_filter="int"
        )
        distance_input = MDTextField(
            hint_text=self._translate("labor_distance"), input_filter="int"
        )
        lifts_input = MDTextField(
            hint_text=self._translate("labor_lifts"), input_filter="int"
        )
        containers_input = MDTextField(
            hint_text=self._translate("labor_containers"), input_filter="int"
        )
        for field in (
            people_input,
            days_input,
            distance_input,
            lifts_input,
            containers_input,
        ):
            field.size_hint_y = None
            field.height = dp(60)
            input_card.add_widget(field)

        toggle_row = MDBoxLayout(
            orientation="horizontal",
            spacing=dp(8),
            size_hint_y=None,
            height=dp(46),
        )
        highways_button = MDRaisedButton(
            text=self._translate("labor_highways_off"),
            size_hint_x=0.5,
            size_hint_y=None,
            height=dp(44),
            font_size="13sp",
            on_release=lambda *_: self.toggle_highways(),
        )
        additional_button = MDRaisedButton(
            text=self._translate("labor_additional_off"),
            size_hint_x=0.5,
            size_hint_y=None,
            height=dp(44),
            font_size="13sp",
            on_release=lambda *_: self.toggle_additional(),
        )
        toggle_row.add_widget(highways_button)
        toggle_row.add_widget(additional_button)
        input_card.add_widget(toggle_row)

        additional_input = MDTextField(
            hint_text=self.additional_hint(),
            input_filter=self._numeric_input_filter,
        )
        additional_input.size_hint_y = None
        additional_input.height = dp(60)
        additional_box = MDBoxLayout(
            orientation="vertical", size_hint_y=None, height=0
        )
        additional_box.add_widget(additional_input)
        input_card.add_widget(additional_box)

        calculate_button = MDRaisedButton(
            text=self._translate("labor_calculate"),
            icon="calculator-variant",
            size_hint_x=0.64,
            size_hint_y=None,
            height=dp(50),
            font_size="15sp",
            on_release=lambda *_: self.calculate(),
        )
        rates_button = MDRaisedButton(
            text=self._translate("labor_rates_button"),
            icon="tune-variant",
            size_hint_x=0.36,
            size_hint_y=None,
            height=dp(50),
            font_size="13sp",
            on_release=lambda *_: self.open_rates(),
        )
        action_row = MDBoxLayout(
            orientation="horizontal",
            spacing=dp(8),
            size_hint_y=None,
            height=dp(52),
        )
        action_row.add_widget(rates_button)
        action_row.add_widget(calculate_button)
        input_card.add_widget(action_row)
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
            text=self._translate("labor_result"),
            font_style="H6",
            size_hint_y=None,
            height=dp(36),
        )
        result_card.add_widget(result_title_label)
        total_label = MDLabel(
            text=self._translate("labor_total_cost", value="—"),
            font_style="H6",
            halign="center",
            size_hint_y=None,
            height=dp(44),
            theme_text_color="Custom",
            text_color=self._total_color,
        )
        result_card.add_widget(total_label)
        currency_note = MDLabel(
            text=self._translate("labor_currency_note_pln"),
            halign="center",
            size_hint_y=None,
            height=dp(30),
            theme_text_color="Hint",
            font_style="Caption",
        )
        result_card.add_widget(currency_note)
        chart = self._chart_factory(
            size_hint_y=None,
            height=dp(210),
            on_release=lambda *_: self.open_chart_dialog(),
        )
        result_card.add_widget(chart)
        chart_hint = MDLabel(
            text=self._translate("labor_chart_empty"),
            halign="center",
            size_hint_y=None,
            height=dp(24),
            theme_text_color="Hint",
            font_style="Caption",
        )
        result_card.add_widget(chart_hint)
        chart_legend = MDBoxLayout(
            orientation="vertical",
            spacing=dp(3),
            size_hint_y=None,
            height=0,
        )
        result_card.add_widget(chart_legend)

        result_labels: dict[str, tuple[Any, str]] = {}
        for attr, key in LABOR_RESULT_LABEL_KEYS:
            label = MDLabel(
                text=self._translate(key, value="—"),
                size_hint_y=None,
                height=dp(28),
                theme_text_color="Secondary",
            )
            result_labels[attr] = (label, key)
        travel_mode_label = MDLabel(
            text=self._translate("labor_travel_mode", value="—"),
            size_hint_y=None,
            height=dp(28),
            theme_text_color="Secondary",
        )
        travel_details_label = MDLabel(
            text=self._translate(
                "labor_travel_details", trips="—", toll_days="—", nights="—"
            ),
            size_hint_y=None,
            height=dp(32),
            theme_text_color="Hint",
            font_style="Caption",
        )
        result_card.add_widget(travel_mode_label)
        result_card.add_widget(travel_details_label)
        content.add_widget(result_card)

        view = LaborTabView(
            scroll=scroll,
            input_card=input_card,
            title_label=title_label,
            hint_label=hint_label,
            people_input=people_input,
            days_input=days_input,
            distance_input=distance_input,
            lifts_input=lifts_input,
            containers_input=containers_input,
            highways_button=highways_button,
            additional_button=additional_button,
            additional_input=additional_input,
            additional_box=additional_box,
            calculate_button=calculate_button,
            rates_button=rates_button,
            result_card=result_card,
            result_title_label=result_title_label,
            total_label=total_label,
            currency_note=currency_note,
            chart=chart,
            chart_hint=chart_hint,
            chart_legend=chart_legend,
            result_labels=result_labels,
            travel_mode_label=travel_mode_label,
            travel_details_label=travel_details_label,
        )
        self.view = view
        self._bind_keyboard_scroll(view.input_fields, scroll)
        scroll.add_widget(content)
        self.set_highways(False)
        self.set_additional_enabled(False)
        self.render_results(None)
        return view

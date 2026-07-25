from decimal import Decimal
from types import SimpleNamespace

from tpof.labor import default_rate_values
from tpof.mobile.currency import default_exchange_rates
from tpof.mobile.tabs.labor import (
    LaborTabController,
    LaborTabPresenter,
    LaborTabView,
)


def _presenter(language="pl"):
    return LaborTabPresenter(
        translate=lambda key, **_kwargs: f"Label {key}:",
        get_language=lambda: language,
        chart_colors={"labor_cost": (1.0, 0.0, 0.0, 1.0)},
    )


def test_labor_presenter_builds_chart_rows_and_percentages():
    breakdown = SimpleNamespace(
        labor_cost=Decimal("300"),
        travel_cost=Decimal("100"),
        lift_cost=Decimal("0"),
    )

    rows = _presenter().chart_rows(breakdown)

    assert [row.key for row in rows] == ["labor_cost", "travel_cost"]
    assert [row.label for row in rows] == [
        "Label labor_labor_cost",
        "Label labor_travel_cost",
    ]
    assert [row.value for row in rows] == [Decimal("300"), Decimal("100")]
    assert [row.percent for row in rows] == [75.0, 25.0]
    assert rows[0].color == (1.0, 0.0, 0.0, 1.0)
    assert rows[1].color == (0.79, 0.96, 1.0, 1.0)


def test_labor_presenter_omits_empty_chart_and_localizes_known_travel_modes():
    presenter = _presenter(language="en")

    assert presenter.chart_rows(None) == []
    assert presenter.chart_rows(SimpleNamespace(labor_cost=Decimal("0"))) == []
    assert presenter.travel_mode_text("Dojazd dzienny") == "Daily travel"
    assert presenter.travel_mode_text("Delegacja tygodniowa") == "Weekly delegation"
    assert presenter.travel_mode_text("Custom mode") == "Custom mode"
    assert _presenter(language="pl").travel_mode_text("Dojazd dzienny") == "Dojazd dzienny"


def test_labor_tab_view_exposes_input_fields_in_keyboard_navigation_order():
    widgets = [object() for _ in range(6)]
    placeholder = object()
    view = LaborTabView(
        scroll=placeholder,
        input_card=placeholder,
        title_label=placeholder,
        hint_label=placeholder,
        people_input=widgets[0],
        days_input=widgets[1],
        distance_input=widgets[2],
        lifts_input=widgets[3],
        containers_input=widgets[4],
        highways_button=placeholder,
        additional_button=placeholder,
        additional_input=widgets[5],
        additional_box=placeholder,
        calculate_button=placeholder,
        rates_button=placeholder,
        result_card=placeholder,
        result_title_label=placeholder,
        total_label=placeholder,
        currency_note=placeholder,
        chart=placeholder,
        chart_hint=placeholder,
        chart_legend=placeholder,
        result_labels={},
        travel_mode_label=placeholder,
        travel_details_label=placeholder,
    )

    assert view.input_fields == tuple(widgets)


class _Widget:
    def __init__(self, text=""):
        self.text = text
        self.hint_text = ""
        self.height = 0
        self.opacity = 0
        self.disabled = False


class _Container(_Widget):
    def __init__(self):
        super().__init__()
        self.children = []

    def add_widget(self, widget):
        self.children.append(widget)

    def clear_widgets(self):
        self.children.clear()


class _Chart:
    def __init__(self):
        self.dark = None
        self.items = []
        self.center_label = ""
        self.center_value = ""

    def set_dark(self, dark):
        self.dark = dark

    def set_data(self, items, *, center_label, center_value, animate):
        self.items = items
        self.center_label = center_label
        self.center_value = center_value
        self.animate = animate


class _Scroll:
    def __init__(self):
        self.calls = []

    def scroll_to(self, widget, **kwargs):
        self.calls.append((widget, kwargs))


def _controller_view():
    placeholder = _Widget()
    result_card = _Widget()
    scroll = _Scroll()
    view = LaborTabView(
        scroll=scroll,
        input_card=placeholder,
        title_label=_Widget(),
        hint_label=_Widget(),
        people_input=_Widget("2"),
        days_input=_Widget("3"),
        distance_input=_Widget("10"),
        lifts_input=_Widget(""),
        containers_input=_Widget(""),
        highways_button=_Widget(),
        additional_button=_Widget(),
        additional_input=_Widget("25"),
        additional_box=_Widget(),
        calculate_button=_Widget(),
        rates_button=_Widget(),
        result_card=result_card,
        result_title_label=_Widget(),
        total_label=_Widget(),
        currency_note=_Widget(),
        chart=_Chart(),
        chart_hint=_Widget(),
        chart_legend=None,
        result_labels={
            "labor_cost": (_Widget(), "labor_labor_cost"),
            "additional_costs_value": (_Widget(), "labor_additional_costs"),
        },
        travel_mode_label=_Widget(),
        travel_details_label=_Widget(),
    )
    return view


def _controller():
    state = {
        "messages": [],
        "events": [],
        "marked": [],
        "cleared": [],
        "styled": [],
        "rates_opened": 0,
    }

    def translate(key, **kwargs):
        values = ",".join(f"{name}={value}" for name, value in sorted(kwargs.items()))
        return f"{key}({values})" if values else key

    def open_rates():
        state["rates_opened"] += 1

    controller = LaborTabController(
        translate=translate,
        get_language=lambda: "pl",
        get_display_currency=lambda: "PLN",
        get_exchange_rates=default_exchange_rates,
        get_rate_values=default_rate_values,
        reset_rate_values=lambda: None,
        is_pro=lambda: True,
        open_rates_dialog=open_rates,
        card_bg=lambda: (0, 0, 0, 1),
        total_color=(0, 1, 0, 1),
        chart_factory=lambda **_kwargs: _Chart(),
        numeric_input_filter=lambda *_args: True,
        register_themed_card=lambda _card: None,
        bind_keyboard_scroll=lambda _fields, _scroll: None,
        style_button=lambda button, variant: state["styled"].append(
            (button, variant)
        ),
        clear_field_error=lambda field: state["cleared"].append(field),
        mark_field_error=lambda field, message=None: state["marked"].append(
            (field, message)
        ),
        show_message=state["messages"].append,
        log_event=lambda name, payload=None: state["events"].append(
            (name, payload or {})
        ),
        get_active_tab=lambda: "labor",
        is_dark=lambda: False,
    )
    controller.view = _controller_view()
    return controller, state


def test_labor_controller_owns_toggle_state_and_optional_field():
    controller, state = _controller()
    view = controller.view
    assert view is not None

    controller.set_highways(True)
    controller.set_additional_enabled(True)

    assert controller.use_highways is True
    assert controller.has_additional is True
    assert view.highways_button.text == "labor_highways_on"
    assert view.additional_button.text == "labor_additional_on"
    assert view.additional_box.disabled is False

    controller.set_additional_enabled(False)

    assert controller.has_additional is False
    assert view.additional_input.text == ""
    assert view.additional_box.disabled is True
    assert view.additional_input in state["cleared"]


def test_labor_controller_calculates_and_retains_breakdown():
    controller, state = _controller()
    view = controller.view
    assert view is not None
    controller.set_highways(True)
    controller.set_additional_enabled(True)

    assert controller.calculate() is True

    breakdown = controller.last_breakdown
    assert breakdown is not None
    assert breakdown.additional_costs_value == Decimal("25.00")
    assert view.total_label.text.startswith("labor_total_cost(")
    assert view.chart.items
    assert view.scroll.calls[0][0] is view.result_card
    assert [name for name, _payload in state["events"]] == [
        "calculation_started",
        "calculation_finished",
    ]


def test_labor_controller_reports_invalid_required_field():
    controller, state = _controller()
    view = controller.view
    assert view is not None
    view.people_input.text = ""

    assert controller.calculate() is False

    assert controller.last_breakdown is None
    assert state["marked"][0][0] is view.people_input
    assert state["messages"][0].startswith("labor_validation_error(")
    assert state["events"][-1][0] == "calculation_error"

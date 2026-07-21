from decimal import Decimal
from types import SimpleNamespace

from tpof.mobile.tabs.labor import LaborTabPresenter, LaborTabView


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

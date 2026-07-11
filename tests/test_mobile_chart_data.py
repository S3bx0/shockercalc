from decimal import Decimal

from tpof.mobile.chart_data import prepare_cost_segments


def test_prepare_cost_segments_handles_empty_and_zero_values():
    assert prepare_cost_segments([]) == ([], Decimal("0"))
    assert prepare_cost_segments([{"label": "Zero", "value": 0}]) == (
        [],
        Decimal("0"),
    )


def test_prepare_cost_segments_single_category_fills_donut():
    segments, total = prepare_cost_segments(
        [{"key": "labor", "label": "Robocizna", "value": "52000"}]
    )

    assert total == Decimal("52000")
    assert len(segments) == 1
    assert segments[0].percent == 100.0
    assert segments[0].start_angle == 90.0
    assert segments[0].sweep_angle == 360.0


def test_prepare_cost_segments_preserves_percentages_and_skips_negative(caplog):
    segments, total = prepare_cost_segments(
        [
            {"key": "labor", "label": "Robocizna", "value": 72.8},
            {"key": "travel", "label": "Dojazd", "value": 8.8},
            {"key": "small", "label": "Mały koszt", "value": 0.4},
            {"key": "invalid", "label": "Błąd", "value": -5},
        ]
    )

    assert total == Decimal("82.0")
    assert [segment.key for segment in segments] == ["labor", "travel", "small"]
    assert sum(segment.sweep_angle for segment in segments) == 360.0
    assert segments[-1].percent < 1.0
    assert "Skipping negative chart value" in caplog.text


def test_prepare_cost_segments_keeps_long_labels_for_legend():
    label = "Posiłek regeneracyjny dla pracowników"

    segments, _total = prepare_cost_segments([{"label": label, "value": 10}])

    assert segments[0].label == label

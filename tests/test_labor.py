"""Tests for the mobile labor-cost calculator core."""

from decimal import Decimal

import pytest

from tpof.labor import (
    CalculationInput,
    RateConfig,
    calculate_cost_breakdown,
    default_rate_config,
    delegation_nights,
    delegation_travel_days,
    delegation_weeks,
    validate_calculation_inputs,
)


def build_rates(**overrides):
    values = {
        "labor_hourly_rate": Decimal("100"),
        "hours_per_day": Decimal("8"),
        "travel_rate_per_km": Decimal("2"),
        "highway_toll_per_travel_day": Decimal("50"),
        "lift_daily_rate": Decimal("10"),
        "lift_transport_cost": Decimal("7"),
        "container_daily_rate": Decimal("5"),
        "container_transport_cost": Decimal("11"),
        "hotel_rate_per_person": Decimal("20"),
        "allowance_per_person": Decimal("15"),
        "meal_per_person": Decimal("8"),
        "hotel_nights_multiplier": Decimal("1"),
        "local_return_distance_limit_km": Decimal("150"),
        "workdays_per_week": 5,
    }
    values.update(overrides)
    return RateConfig(**values)


def test_default_labor_rates_are_valid():
    default_rate_config().validate()


def test_labor_cost_breakdown_full_case_matches_desktop_logic():
    data = CalculationInput(
        number_of_people=2,
        number_of_days=3,
        distance_km_one_way=10,
        use_highways=True,
        number_of_lifts=1,
        number_of_containers=2,
        additional_costs_value=Decimal("5"),
    )

    result = calculate_cost_breakdown(data, build_rates())

    assert result.labor_cost == Decimal("4800.00")
    assert result.travel_cost == Decimal("270.00")
    assert result.lift_cost == Decimal("37.00")
    assert result.container_cost == Decimal("41.00")
    assert result.hotel_cost == Decimal("0.00")
    assert result.allowance_cost == Decimal("90.00")
    assert result.regenerative_meal_cost == Decimal("48.00")
    assert result.additional_costs_value == Decimal("5.00")
    assert result.total_cost == Decimal("5291.00")
    assert result.travel_mode == "Dojazd dzienny"
    assert result.travel_round_trips == 3
    assert result.highway_toll_days == 3
    assert result.hotel_nights == 0


def test_labor_delegation_mode_counts_travel_and_hotels():
    data = CalculationInput(
        number_of_people=2,
        number_of_days=5,
        distance_km_one_way=151,
        use_highways=True,
        number_of_lifts=0,
        number_of_containers=0,
        additional_costs_value=Decimal("0"),
    )

    result = calculate_cost_breakdown(data, build_rates())

    assert result.travel_cost == Decimal("704.00")
    assert result.hotel_cost == Decimal("160.00")
    assert result.travel_mode == "Delegacja tygodniowa"
    assert result.travel_round_trips == 1
    assert result.highway_toll_days == 2
    assert result.hotel_nights == 4


@pytest.mark.parametrize(
    "days,workdays,weeks,nights,travel_days",
    [
        (1, 5, 1, 0, 1),
        (5, 5, 1, 4, 2),
        (6, 5, 2, 4, 3),
        (10, 5, 2, 8, 4),
    ],
)
def test_labor_delegation_helpers(days, workdays, weeks, nights, travel_days):
    assert delegation_weeks(days, workdays) == weeks
    assert delegation_nights(days, workdays) == nights
    assert delegation_travel_days(days, workdays) == travel_days


def test_labor_validation_collects_errors():
    errors = validate_calculation_inputs(
        number_of_people=0,
        number_of_days=0,
        distance=-1,
        number_of_lifts=-1,
        number_of_containers=-1,
        has_additional_costs=True,
        additional_costs_value=-1,
    )

    assert len(errors) == 6
    assert any("Liczba osób" in error for error in errors)

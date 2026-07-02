"""Pure labor cost calculation logic ported from the desktop calculator."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, getcontext

from .models import CalculationInput, CostBreakdown, RateConfig

getcontext().rounding = ROUND_HALF_UP

Q = Decimal("0.01")
TRAVEL_MODE_DAILY = "Dojazd dzienny"
TRAVEL_MODE_DELEGATION = "Delegacja tygodniowa"


def quantize_money(value: Decimal) -> Decimal:
    return value.quantize(Q)


def delegation_weeks(days: int, workdays_per_week: int) -> int:
    return (days + workdays_per_week - 1) // workdays_per_week


def delegation_nights(days: int, workdays_per_week: int) -> int:
    full_weeks, remaining_days = divmod(days, workdays_per_week)
    return full_weeks * (workdays_per_week - 1) + max(0, remaining_days - 1)


def delegation_travel_days(days: int, workdays_per_week: int) -> int:
    full_weeks, remaining_days = divmod(days, workdays_per_week)
    return full_weeks * 2 + min(remaining_days, 2)


def calculate_cost_breakdown(data: CalculationInput, rates: RateConfig) -> CostBreakdown:
    ppl = int(data.number_of_people)
    days = int(data.number_of_days)
    km_one_way = Decimal(str(data.distance_km_one_way))
    lifts = int(data.number_of_lifts)
    containers = int(data.number_of_containers)
    add_costs = Decimal(str(data.additional_costs_value))
    workdays_per_week = max(1, int(rates.workdays_per_week))

    labor_cost = Decimal(ppl) * Decimal(days) * rates.hours_per_day * rates.labor_hourly_rate

    daily_km = Decimal(2) * km_one_way
    highway_toll = rates.highway_toll_per_travel_day if data.use_highways else Decimal(0)
    if km_one_way <= rates.local_return_distance_limit_km:
        travel_mode = TRAVEL_MODE_DAILY
        travel_round_trips = days
        highway_toll_days = days
        hotel_nights = 0
    else:
        travel_mode = TRAVEL_MODE_DELEGATION
        travel_round_trips = delegation_weeks(days, workdays_per_week)
        highway_toll_days = delegation_travel_days(days, workdays_per_week)
        hotel_nights = delegation_nights(days, workdays_per_week)

    travel_cost = (
        Decimal(travel_round_trips) * daily_km * rates.travel_rate_per_km
        + Decimal(highway_toll_days) * highway_toll
    )
    lift_cost = Decimal(lifts) * (Decimal(days) * rates.lift_daily_rate) + (
        rates.lift_transport_cost if lifts > 0 else Decimal(0)
    )
    container_cost = Decimal(containers) * (
        Decimal(days) * rates.container_daily_rate
    ) + (rates.container_transport_cost if containers > 0 else Decimal(0))
    hotel_cost = (
        Decimal(hotel_nights)
        * Decimal(ppl)
        * rates.hotel_nights_multiplier
        * rates.hotel_rate_per_person
    )
    allowance_cost = Decimal(days) * Decimal(ppl) * rates.allowance_per_person
    regenerative_meal_cost = Decimal(days) * Decimal(ppl) * rates.meal_per_person

    labor_cost = quantize_money(labor_cost)
    travel_cost = quantize_money(travel_cost)
    lift_cost = quantize_money(lift_cost)
    container_cost = quantize_money(container_cost)
    hotel_cost = quantize_money(hotel_cost)
    allowance_cost = quantize_money(allowance_cost)
    regenerative_meal_cost = quantize_money(regenerative_meal_cost)
    add_costs = quantize_money(add_costs)

    total_cost = quantize_money(
        labor_cost
        + travel_cost
        + lift_cost
        + container_cost
        + hotel_cost
        + allowance_cost
        + regenerative_meal_cost
        + add_costs
    )

    return CostBreakdown(
        labor_cost=labor_cost,
        travel_cost=travel_cost,
        lift_cost=lift_cost,
        container_cost=container_cost,
        hotel_cost=hotel_cost,
        allowance_cost=allowance_cost,
        regenerative_meal_cost=regenerative_meal_cost,
        additional_costs_value=add_costs,
        total_cost=total_cost,
        travel_mode=travel_mode,
        travel_round_trips=travel_round_trips,
        highway_toll_days=highway_toll_days if data.use_highways else 0,
        hotel_nights=hotel_nights,
    )

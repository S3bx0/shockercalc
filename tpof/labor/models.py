"""Domain models for the labor cost calculator."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class CalculationInput:
    number_of_people: int
    number_of_days: int
    distance_km_one_way: int
    use_highways: bool
    number_of_lifts: int
    number_of_containers: int
    additional_costs_value: Decimal


@dataclass(frozen=True)
class RateConfig:
    labor_hourly_rate: Decimal
    hours_per_day: Decimal
    travel_rate_per_km: Decimal
    highway_toll_per_travel_day: Decimal
    lift_daily_rate: Decimal
    lift_transport_cost: Decimal
    container_daily_rate: Decimal
    container_transport_cost: Decimal
    hotel_rate_per_person: Decimal
    allowance_per_person: Decimal
    meal_per_person: Decimal
    hotel_nights_multiplier: Decimal
    local_return_distance_limit_km: Decimal
    workdays_per_week: int

    def validate(self) -> None:
        errors: list[str] = []
        nonnegative_fields = (
            "labor_hourly_rate",
            "travel_rate_per_km",
            "highway_toll_per_travel_day",
            "lift_daily_rate",
            "lift_transport_cost",
            "container_daily_rate",
            "container_transport_cost",
            "hotel_rate_per_person",
            "allowance_per_person",
            "meal_per_person",
            "hotel_nights_multiplier",
            "local_return_distance_limit_km",
        )
        for field in nonnegative_fields:
            value = getattr(self, field)
            if value < 0:
                errors.append(f"{field} must be >= 0; got {value}.")
        if not (Decimal("0") < self.hours_per_day <= Decimal("24")):
            errors.append(f"hours_per_day must be in (0, 24]; got {self.hours_per_day}.")
        if not (1 <= int(self.workdays_per_week) <= 7):
            errors.append(f"workdays_per_week must be in [1, 7]; got {self.workdays_per_week}.")
        if errors:
            raise ValueError("Invalid labor rate configuration:\n - " + "\n - ".join(errors))


@dataclass(frozen=True)
class CostBreakdown:
    labor_cost: Decimal
    travel_cost: Decimal
    lift_cost: Decimal
    container_cost: Decimal
    hotel_cost: Decimal
    allowance_cost: Decimal
    regenerative_meal_cost: Decimal
    additional_costs_value: Decimal
    total_cost: Decimal
    travel_mode: str
    travel_round_trips: int
    highway_toll_days: int
    hotel_nights: int

    def to_legacy_dict(self) -> dict:
        return {
            "labor_cost": self.labor_cost,
            "travel_cost": self.travel_cost,
            "lift_cost": self.lift_cost,
            "container_cost": self.container_cost,
            "hotel_cost": self.hotel_cost,
            "allowance_cost": self.allowance_cost,
            "regenerative_meal_cost": self.regenerative_meal_cost,
            "additional_costs_value": self.additional_costs_value,
            "total_cost": self.total_cost,
            "travel_mode": self.travel_mode,
            "travel_round_trips": self.travel_round_trips,
            "highway_toll_days": self.highway_toll_days,
            "hotel_nights": self.hotel_nights,
        }

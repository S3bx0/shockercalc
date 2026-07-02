"""Default rates for the labor cost calculator.

The values mirror the desktop `robocizna` configuration. Editable/custom rate
profiles are intentionally left for a later PRO feature so the first mobile
integration has deterministic defaults.
"""

from __future__ import annotations

from decimal import Decimal

from .models import RateConfig


def default_rate_config() -> RateConfig:
    rates = RateConfig(
        labor_hourly_rate=Decimal("130.0"),
        hours_per_day=Decimal("10"),
        travel_rate_per_km=Decimal("2.1"),
        highway_toll_per_travel_day=Decimal("42.0"),
        lift_daily_rate=Decimal("380.0"),
        lift_transport_cost=Decimal("0"),
        container_daily_rate=Decimal("140.0"),
        container_transport_cost=Decimal("0"),
        hotel_rate_per_person=Decimal("150.0"),
        allowance_per_person=Decimal("45.0"),
        meal_per_person=Decimal("28.0"),
        hotel_nights_multiplier=Decimal("1.0"),
        local_return_distance_limit_km=Decimal("150"),
        workdays_per_week=5,
    )
    rates.validate()
    return rates

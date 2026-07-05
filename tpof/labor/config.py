"""Default and editable rates for the labor cost calculator."""

from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal

from .models import RateConfig

RATE_CONFIG_FIELDS = (
    "labor_hourly_rate",
    "hours_per_day",
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
    "workdays_per_week",
)

DEFAULT_RATE_VALUES: dict[str, Decimal | int] = {
    "labor_hourly_rate": Decimal("130.0"),
    "hours_per_day": Decimal("10"),
    "travel_rate_per_km": Decimal("2.1"),
    "highway_toll_per_travel_day": Decimal("42.0"),
    "lift_daily_rate": Decimal("380.0"),
    "lift_transport_cost": Decimal("0"),
    "container_daily_rate": Decimal("140.0"),
    "container_transport_cost": Decimal("0"),
    "hotel_rate_per_person": Decimal("150.0"),
    "allowance_per_person": Decimal("45.0"),
    "meal_per_person": Decimal("28.0"),
    "hotel_nights_multiplier": Decimal("1.0"),
    "local_return_distance_limit_km": Decimal("150"),
    "workdays_per_week": 5,
}


def _parse_decimal(value: object, field: str) -> Decimal:
    try:
        return Decimal(str(value).replace(",", ".").strip())
    except Exception as exc:
        raise ValueError(f"{field} must be a decimal value; got {value!r}.") from exc


def default_rate_values() -> dict[str, Decimal | int]:
    return dict(DEFAULT_RATE_VALUES)


def rate_config_from_values(values: Mapping[str, object] | None = None) -> RateConfig:
    merged = default_rate_values()
    for key, value in (values or {}).items():
        if key not in merged:
            continue
        if key == "workdays_per_week":
            try:
                merged[key] = int(str(value).strip())
            except Exception as exc:
                raise ValueError(f"{key} must be an integer value; got {value!r}.") from exc
        else:
            merged[key] = _parse_decimal(value, key)
    # Heterogeneous unpack (Decimal fields + int workdays_per_week), validated at runtime.
    rates = RateConfig(**merged)  # type: ignore[arg-type]
    rates.validate()
    return rates


def rate_config_to_dict(rates: RateConfig) -> dict[str, str]:
    return {field: str(getattr(rates, field)) for field in RATE_CONFIG_FIELDS}


def default_rate_config() -> RateConfig:
    return rate_config_from_values()

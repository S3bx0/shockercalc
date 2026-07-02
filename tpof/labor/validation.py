"""Validation helpers for labor calculation inputs."""

from __future__ import annotations

from decimal import Decimal
from typing import Sequence


class ValidationError(ValueError):
    """Validation error carrying all messages for UI display."""

    def __init__(self, errors: Sequence[str]):
        self.errors = list(errors)
        super().__init__("\n".join(self.errors) if self.errors else "ValidationError")


def validate_number_value(value, name: str, min_value=None, allow_zero: bool = True) -> str | None:
    if value is None:
        return f"Pole '{name}' nie może być puste."
    if not isinstance(value, (int, float, Decimal)):
        return f"W polu '{name}' proszę wprowadzić poprawną wartość liczbową."
    if min_value is not None:
        if not allow_zero and value == 0:
            return f"Wartość w polu '{name}' nie może być równa zero."
        if value < min_value:
            return f"Wartość w polu '{name}' nie może być mniejsza niż {min_value}."
    return None


def validate_calculation_inputs(
    number_of_people,
    number_of_days,
    distance,
    number_of_lifts,
    number_of_containers,
    has_additional_costs: bool,
    additional_costs_value,
) -> list[str]:
    errors: list[str] = []
    checks = [
        (number_of_people, "Liczba osób", 1, False),
        (number_of_days, "Liczba dni pracy", 1, False),
        (distance, "Ilość kilometrów", 0, True),
        (number_of_lifts, "Ilość zwyżek", 0, True),
        (number_of_containers, "Ilość kontenerów", 0, True),
    ]
    for value, field_name, min_value, allow_zero in checks:
        error = validate_number_value(
            value, field_name, min_value=min_value, allow_zero=allow_zero
        )
        if error:
            errors.append(error)

    if has_additional_costs:
        error = validate_number_value(
            additional_costs_value,
            "Wartość dodatkowych kosztów",
            min_value=0,
            allow_zero=True,
        )
        if error:
            errors.append(error)
    return errors


def validate_calculation_inputs_or_raise(**kwargs) -> None:
    errors = validate_calculation_inputs(**kwargs)
    if errors:
        raise ValidationError(errors)

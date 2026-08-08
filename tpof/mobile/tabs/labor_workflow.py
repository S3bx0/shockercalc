"""Validation and calculation workflow for the mobile labor-cost tab."""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping
from decimal import Decimal
from typing import Any, Protocol, cast

from tpof.labor import (
    CalculationInput,
    CostBreakdown,
    RateConfig,
    calculate_cost_breakdown,
    default_rate_config,
    rate_config_from_values,
    validate_calculation_inputs,
)
from tpof.mobile.currency import ExchangeRates, convert_display_amount_to_pln
from tpof.mobile.tabs.labor_view import LaborTabView

log = logging.getLogger(__name__)


class _LaborResultsPresenter(Protocol):
    def render_results(self, breakdown: CostBreakdown | None) -> None: ...


class LaborCalculationWorkflowMixin:
    """Own form parsing, validation and orchestration of a labor calculation."""

    _translate: Callable[..., str]
    _get_exchange_rates: Callable[[], ExchangeRates]
    _get_rate_values: Callable[[], Mapping[str, object]]
    _reset_rate_values: Callable[[], None]
    _clear_field_error: Callable[[Any], None]
    _mark_field_error: Callable[[Any, str | None], None]
    _show_message: Callable[[str], None]
    _announce_result: Callable[[str], bool]
    _log_event: Callable[[str, Mapping[str, object] | None], None]
    _get_active_tab: Callable[[], str]
    _dp: Callable[[float], float]

    use_highways: bool
    has_additional: bool
    additional_currency: str
    view: LaborTabView | None

    def clear_validation(self) -> None:
        if self.view is None:
            return
        for field in self.view.input_fields:
            self._clear_field_error(field)

    def _invalid_field_message(self, name_key: str) -> str:
        return self._translate(
            "invalid_field",
            name=self._translate(name_key),
        )

    def _parse_int(
        self,
        field: Any,
        name_key: str,
        *,
        min_value: int,
        allow_zero: bool,
        default_empty: int | None = None,
    ) -> int:
        raw = (getattr(field, "text", "") or "").strip()
        if not raw and default_empty is not None:
            return default_empty
        message = self._invalid_field_message(name_key)
        if not raw:
            self._mark_field_error(field, None)
            raise ValueError(message)
        try:
            value = int(raw)
        except (TypeError, ValueError) as exc:
            self._mark_field_error(field, message)
            raise ValueError(message) from exc
        if value < min_value or (not allow_zero and value == 0):
            self._mark_field_error(field, message)
            raise ValueError(message)
        return value

    def _parse_decimal(self, field: Any, name_key: str) -> Decimal:
        raw = (getattr(field, "text", "") or "").strip()
        message = self._invalid_field_message(name_key)
        if not raw:
            self._mark_field_error(field, None)
            raise ValueError(message)
        try:
            value = Decimal(raw.replace(",", "."))
        except Exception as exc:
            self._mark_field_error(field, message)
            raise ValueError(message) from exc
        if value < 0:
            self._mark_field_error(field, message)
            raise ValueError(message)
        return value

    def _rate_config(self) -> RateConfig:
        try:
            return rate_config_from_values(self._get_rate_values())
        except ValueError:
            self._reset_rate_values()
            return default_rate_config()

    def calculate(self) -> bool:
        """Validate the form, calculate labor costs and render the result."""

        if self.view is None:
            return False
        self.clear_validation()
        try:
            people = self._parse_int(
                self.view.people_input,
                "labor_people",
                min_value=1,
                allow_zero=False,
            )
            days = self._parse_int(
                self.view.days_input,
                "labor_days",
                min_value=1,
                allow_zero=False,
            )
            distance = self._parse_int(
                self.view.distance_input,
                "labor_distance",
                min_value=0,
                allow_zero=True,
            )
            lifts = self._parse_int(
                self.view.lifts_input,
                "labor_lifts",
                min_value=0,
                allow_zero=True,
                default_empty=0,
            )
            containers = self._parse_int(
                self.view.containers_input,
                "labor_containers",
                min_value=0,
                allow_zero=True,
                default_empty=0,
            )
            additional = (
                self._parse_decimal(
                    self.view.additional_input,
                    "labor_additional",
                )
                if self.has_additional
                else Decimal("0")
            )
            if self.has_additional:
                try:
                    additional = convert_display_amount_to_pln(
                        additional,
                        self.additional_currency,
                        self._get_exchange_rates(),
                    )
                except ValueError as exc:
                    message = self._translate(
                        "labor_currency_input_missing",
                        currency=self.additional_currency,
                    )
                    self._mark_field_error(
                        self.view.additional_input,
                        message,
                    )
                    raise ValueError(message) from exc
            errors = validate_calculation_inputs(
                people,
                days,
                distance,
                lifts,
                containers,
                self.has_additional,
                additional,
            )
            if errors:
                raise ValueError(errors[0])
            self._log_event(
                "calculation_started",
                {
                    "calculator": "labor",
                    "screen": self._get_active_tab(),
                },
            )
            breakdown = calculate_cost_breakdown(
                CalculationInput(
                    number_of_people=people,
                    number_of_days=days,
                    distance_km_one_way=distance,
                    use_highways=self.use_highways,
                    number_of_lifts=lifts,
                    number_of_containers=containers,
                    additional_costs_value=additional,
                ),
                self._rate_config(),
            )
            cast(_LaborResultsPresenter, self).render_results(breakdown)
            self._announce_result(self.view.total_label.text)
            self._log_event(
                "calculation_finished",
                {
                    "calculator": "labor",
                    "travel_mode": breakdown.travel_mode,
                    "has_additional": self.has_additional,
                },
            )
            self.view.scroll.scroll_to(
                self.view.result_card,
                padding=self._dp(12),
                animate=True,
            )
            return True
        except ValueError as exc:
            self._show_message(
                self._translate(
                    "labor_validation_error",
                    message=str(exc),
                )
            )
            self._log_event(
                "calculation_error",
                {
                    "calculator": "labor",
                    "error": str(exc)[:120],
                },
            )
            return False
        except Exception as exc:  # pragma: no cover - UI safeguard
            log.exception("Błąd obliczeń robocizny")
            self._show_message(self._translate("calc_error", error=exc))
            return False

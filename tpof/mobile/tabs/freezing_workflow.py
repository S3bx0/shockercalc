"""Validation and calculation workflow for the mobile freezing tab."""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping
from typing import Any

from tpof.core import (
    FreezingInputs,
    FreezingResults,
    Product,
    calculate_freezing,
    find_product,
)
from tpof.mobile.constants import (
    ABSOLUTE_ZERO_C,
    TEMP_HIGH_ERROR_C,
    TEMP_HIGH_STRONG_WARNING_C,
    TEMP_HIGH_WARNING_C,
    TEMP_LOW_STRONG_WARNING_C,
    TEMP_LOW_WARNING_C,
)
from tpof.mobile.tabs.freezing_view import FreezingTabView

log = logging.getLogger(__name__)


class FreezingCalculationWorkflowMixin:
    """Own form validation and orchestration of a freezing calculation."""

    _catalog: dict[str, list[Product]]
    _translate: Callable[..., str]
    _clear_field_error: Callable[[Any], None]
    _mark_field_error: Callable[[Any, str | None], None]
    _show_message: Callable[[str], None]
    _log_event: Callable[[str, Mapping[str, object] | None], None]
    _record_exception: Callable[[BaseException, str], None]
    _ensure_product_access: Callable[[str, str], bool]
    _is_custom_product: Callable[[str, str], bool]

    selected_category: str | None
    selected_product: str | None
    mass_unit: str
    last_results: FreezingResults | None
    view: FreezingTabView | None

    def clear_validation(self) -> None:
        if self.view is None:
            return
        self.view.category_error_line.opacity = 0
        self.view.product_error_line.opacity = 0
        for field in self.view.input_fields:
            self._clear_field_error(field)

    def _parse_required_field(self, field: Any, name_key: str) -> float:
        name = self._translate(name_key)
        raw = (getattr(field, "text", "") or "").strip()
        if not raw:
            self._mark_field_error(field, None)
            raise ValueError(self._translate("invalid_field", name=name))
        try:
            return float(raw.replace(",", "."))
        except (TypeError, ValueError, AttributeError) as exc:
            message = self._translate("invalid_field", name=name)
            self._mark_field_error(field, message)
            raise ValueError(message) from exc

    def temperature_warning(self, field_name: str, value: float) -> str | None:
        if value >= TEMP_HIGH_STRONG_WARNING_C:
            return self._translate(
                "temperature_warning_high_strong",
                field=field_name,
                value=value,
            )
        if value >= TEMP_HIGH_WARNING_C:
            return self._translate(
                "temperature_warning_high",
                field=field_name,
                value=value,
            )
        if value <= TEMP_LOW_STRONG_WARNING_C:
            return (
                self._translate(
                    "temperature_warning_low_strong",
                    field=field_name,
                    value=value,
                )
                + " "
                + self._translate("temperature_warning_co2")
            )
        if value <= TEMP_LOW_WARNING_C:
            return self._translate(
                "temperature_warning_low",
                field=field_name,
                value=value,
            )
        return None

    def validate_temperature(
        self,
        field: Any,
        field_name: str,
        value: float,
    ) -> str | None:
        if value < ABSOLUTE_ZERO_C:
            message = self._translate(
                "temperature_error_absolute",
                field=field_name,
            )
            self._mark_field_error(field, message)
            raise ValueError(message)
        if value > TEMP_HIGH_ERROR_C:
            message = self._translate(
                "temperature_error_high",
                field=field_name,
                limit=TEMP_HIGH_ERROR_C,
            )
            self._mark_field_error(field, message)
            raise ValueError(message)
        return self.temperature_warning(field_name, value)

    def calculate(self) -> bool:
        """Validate the form, calculate freezing demand and render the result."""

        if self.view is None:
            return False
        self.clear_validation()
        self._log_event("calculation_started", {"calculator": "freezing"})
        try:
            if not self.selected_category:
                self.view.category_error_line.opacity = 1
                self.view.product_error_line.opacity = 1
                self.view.scroll.scroll_y = 1
                self._show_message(self._translate("pick_product_error"))
                return False
            if not self.selected_product:
                self.view.product_error_line.opacity = 1
                self.view.scroll.scroll_y = 1
                self._show_message(self._translate("pick_product_error"))
                return False
            product = find_product(
                self._catalog,
                self.selected_category,
                self.selected_product,
            )
            if product is None:
                self.view.product_error_line.opacity = 1
                self._show_message(self._translate("missing_product_error"))
                return False
            if not self._ensure_product_access(
                self.selected_category,
                self.selected_product,
            ):
                return False

            mass = self._parse_required_field(
                self.view.mass_input,
                "field_mass",
            )
            if mass <= 0:
                message = self._translate(
                    "invalid_field",
                    name=self._translate("field_mass"),
                )
                self._mark_field_error(self.view.mass_input, message)
                raise ValueError(message)
            if self.mass_unit == "t":
                mass *= 1000.0

            temp_start = self._parse_required_field(
                self.view.temp_start_input,
                "field_temp_start",
            )
            temp_end = self._parse_required_field(
                self.view.temp_end_input,
                "field_temp_end",
            )
            warnings = [
                warning
                for warning in (
                    self.validate_temperature(
                        self.view.temp_start_input,
                        self._translate("field_temp_start"),
                        temp_start,
                    ),
                    self.validate_temperature(
                        self.view.temp_end_input,
                        self._translate("field_temp_end"),
                        temp_end,
                    ),
                )
                if warning
            ]
            if warnings:
                self._show_message(warnings[0])

            time_h = self._parse_required_field(
                self.view.time_input,
                "field_time",
            )
            if time_h <= 0:
                message = self._translate(
                    "invalid_field",
                    name=self._translate("field_time"),
                )
                self._mark_field_error(self.view.time_input, message)
                raise ValueError(message)

            inputs = FreezingInputs(
                masa_kg=mass,
                T_pocz_C=temp_start,
                T_konc_C=temp_end,
                czas_h=time_h,
            )
            results = calculate_freezing(inputs, product)
            self.last_results = results
            self.render_results(results)
            self._log_event(
                "calculation_finished",
                {
                    "calculator": "freezing",
                    "mass_unit": self.mass_unit,
                    "custom_product": self._is_custom_product(
                        product.kategoria,
                        product.nazwa,
                    ),
                },
            )
            return True
        except ValueError as exc:
            self._show_message(str(exc))
            return False
        except Exception as exc:  # pragma: no cover - UI safety net
            self._record_exception(exc, "calculate_freezing")
            log.exception("Freezing calculation failed")
            self._show_message(self._translate("calc_error", error=exc))
            return False

    def render_results(
        self,
        results: FreezingResults,
        *,
        scroll: bool = True,
    ) -> None:
        """Render a successful calculation in the owning controller."""

        raise NotImplementedError

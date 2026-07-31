"""Validation and calculation workflow for the mobile valves tab."""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping
from typing import Any

from tpof.core import ValveResults, calculate_decompression_valves
from tpof.mobile.tabs.valves_view import ValvesTabView

log = logging.getLogger(__name__)


class ValvesCalculationWorkflowMixin:
    """Own form parsing, validation and orchestration of a valve calculation."""

    _translate: Callable[..., str]
    _clear_field_error: Callable[[Any], None]
    _mark_field_error: Callable[[Any, str | None], None]
    _show_message: Callable[[str], None]
    _log_event: Callable[[str, Mapping[str, object] | None], None]
    _record_exception: Callable[[BaseException, str], None]
    _can_calculate: Callable[[], bool]
    _on_access_denied: Callable[[], None]

    input_mode: str
    valve_type: str
    last_results: ValveResults | None
    last_total_flow: float | None
    view: ValvesTabView | None
    render_results: Callable[[ValveResults | None], None]

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

    def _parse_required_field(self, field: Any, name_key: str) -> float:
        raw = (getattr(field, "text", "") or "").strip()
        message = self._invalid_field_message(name_key)
        if not raw:
            self._mark_field_error(field, None)
            raise ValueError(message)
        try:
            return float(raw.replace(",", "."))
        except (TypeError, ValueError, AttributeError) as exc:
            self._mark_field_error(field, message)
            raise ValueError(message) from exc

    def calculate(self) -> bool:
        """Validate inputs, calculate valve requirements and render the result."""

        if self.view is None:
            return False
        if not self._can_calculate():
            self._on_access_denied()
            return False

        self.clear_validation()
        self._log_event("calculation_started", {"calculator": "valves"})
        try:
            if self.input_mode == "W":
                length = self._parse_required_field(
                    self.view.length_input,
                    "valve_length",
                )
                width = self._parse_required_field(
                    self.view.width_input,
                    "valve_width",
                )
                height = self._parse_required_field(
                    self.view.height_input,
                    "valve_height",
                )
                volume = length * width * height
            else:
                volume = self._parse_required_field(
                    self.view.volume_input,
                    "valve_volume",
                )
            temp_before = self._parse_required_field(
                self.view.temp_before_input,
                "valve_temp_before",
            )
            temp_after = self._parse_required_field(
                self.view.temp_after_input,
                "valve_temp_after",
            )
            coolers_value = self._parse_required_field(
                self.view.coolers_input,
                "valve_coolers",
            )
            if not coolers_value.is_integer():
                message = self._invalid_field_message("valve_coolers")
                self._mark_field_error(self.view.coolers_input, message)
                raise ValueError(message)
            coolers = int(coolers_value)
            if coolers < 1:
                message = self._translate("valve_coolers_min")
                self._mark_field_error(self.view.coolers_input, message)
                raise ValueError(message)
            flow_per_cooler = self._parse_required_field(
                self.view.flow_input,
                "valve_flow_per",
            )
            if flow_per_cooler <= 0:
                message = self._translate("valve_flow_positive")
                self._mark_field_error(self.view.flow_input, message)
                raise ValueError(message)

            total_flow = flow_per_cooler * coolers
            results = calculate_decompression_valves(
                volume,
                temp_before,
                temp_after,
                total_flow,
                self.valve_type,
            )
            self.last_total_flow = total_flow
            self.render_results(results)
            self._log_event(
                "calculation_finished",
                {"calculator": "valves"},
            )
            return True
        except ValueError as exc:
            self._show_message(str(exc))
            return False
        except Exception as exc:  # pragma: no cover - UI safeguard
            self._record_exception(exc, "calculate_valves")
            log.exception("Obliczenia zaworów")
            self._show_message(self._translate("calc_error", error=exc))
            return False

"""Result presentation and reset behavior for the mobile freezing tab."""

from __future__ import annotations

from collections.abc import Callable

from tpof.core import FreezingResults
from tpof.mobile.constants import STAGE_COLORS
from tpof.mobile.tabs.freezing_view import FreezingTabView


class FreezingResultsPresentationMixin:
    """Render and clear freezing results without owning calculations."""

    _translate: Callable[..., str]
    clear_validation: Callable[[], None]

    last_results: FreezingResults | None
    view: FreezingTabView | None

    def total_text(self, total: float | None = None) -> str:
        value = "—" if total is None else f"{total:.2f}"
        return self._translate("total_power", value=value)

    def render_results(
        self,
        results: FreezingResults,
        *,
        scroll: bool = True,
    ) -> None:
        if self.view is None:
            return
        total = results.P_total_kW or 0.0
        self.view.total_label.text = self.total_text(total)
        values = {
            "schladzanie": results.P_schladzanie_kW,
            "zamrozenie": results.P_zamrozenie_kW,
            "domrozenie": results.P_domrozenie_kW,
        }
        for key, value in values.items():
            percent = (value / total * 100.0) if total > 0 else 0.0
            stage = self.view.stages[key]
            stage.bar.color = STAGE_COLORS[key]
            stage.bar.value = percent
            stage.value_label.text = f"{value:.2f} kW ({percent:.0f}%)"
        if scroll:
            try:
                from kivy.metrics import dp

                self.view.scroll.scroll_to(
                    self.view.results_card,
                    padding=dp(12),
                    animate=True,
                )
            except Exception:  # pragma: no cover - cosmetic only
                pass

    def reset_inputs(self) -> None:
        if self.view is None:
            return
        for field in self.view.input_fields:
            field.text = ""
        self.view.total_label.text = self.total_text()
        for key, stage in self.view.stages.items():
            stage.bar.value = 0
            # KivyMD 1.2 can leave the last progress-fill texture visible on
            # Android after assigning an exact zero. Hiding the fill color
            # guarantees an empty bar; render_results restores its stage color.
            stage.bar.color = (*STAGE_COLORS[key][:3], 0)
            stage.value_label.text = "—"
        self.last_results = None
        self.clear_validation()

"""Pure data preparation for lightweight mobile charts."""

from __future__ import annotations

import logging
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

log = logging.getLogger(__name__)

ChartColor = tuple[float, float, float, float]


@dataclass(frozen=True)
class CostChartSegment:
    key: str
    label: str
    value: Decimal
    percent: float
    start_angle: float
    sweep_angle: float
    color: ChartColor


def prepare_cost_segments(
    items: Iterable[Mapping[str, object]],
    *,
    start_angle: float = 90.0,
) -> tuple[list[CostChartSegment], Decimal]:
    """Normalize positive cost items and precompute their donut geometry."""

    normalized: list[tuple[str, str, Decimal, ChartColor]] = []
    for index, item in enumerate(items):
        try:
            value = Decimal(str(item.get("value", "0") or "0"))
        except (InvalidOperation, TypeError, ValueError):
            log.warning("Skipping invalid chart value at index %s", index)
            continue
        if value < 0:
            log.warning("Skipping negative chart value for %s", item.get("label", index))
            continue
        if value == 0:
            continue
        raw_color = item.get("color", (0.10, 0.72, 0.95, 1.0))
        color: ChartColor = (0.10, 0.72, 0.95, 1.0)
        if isinstance(raw_color, (tuple, list)) and len(raw_color) == 4:
            try:
                color = (
                    float(raw_color[0]),
                    float(raw_color[1]),
                    float(raw_color[2]),
                    float(raw_color[3]),
                )
            except (TypeError, ValueError):
                pass
        normalized.append(
            (
                str(item.get("key", index)),
                str(item.get("label", "")).strip(),
                value,
                color,
            )
        )

    total = sum((value for _key, _label, value, _color in normalized), Decimal("0"))
    if total <= 0:
        return [], Decimal("0")

    result: list[CostChartSegment] = []
    angle = float(start_angle)
    for key, label, value, color in normalized:
        percent = float((value / total) * Decimal("100"))
        sweep = float((value / total) * Decimal("360"))
        result.append(
            CostChartSegment(
                key=key,
                label=label,
                value=value,
                percent=percent,
                start_angle=angle,
                sweep_angle=sweep,
                color=color,
            )
        )
        angle += sweep
    return result, total

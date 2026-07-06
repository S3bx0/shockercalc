"""Lightweight chart widgets for the mobile UI."""

from __future__ import annotations

from decimal import Decimal

from kivy.graphics import Color, Line
from kivy.metrics import dp
from kivy.uix.widget import Widget


class LaborPieChart(Widget):
    """Small donut chart showing the labor cost structure."""

    SEGMENT_COLORS = (
        ("labor_cost", (0.10, 0.72, 0.95, 1.0)),
        ("travel_cost", (0.09, 0.84, 0.75, 1.0)),
        ("lift_cost", (0.54, 0.43, 1.0, 1.0)),
        ("container_cost", (0.38, 0.78, 1.0, 1.0)),
        ("hotel_cost", (0.15, 0.65, 0.95, 1.0)),
        ("allowance_cost", (0.74, 0.90, 1.0, 1.0)),
        ("regenerative_meal_cost", (0.22, 0.92, 0.82, 1.0)),
        ("additional_costs_value", (0.82, 0.62, 1.0, 1.0)),
    )
    _SEGMENT_COLORS = SEGMENT_COLORS

    def __init__(self, **kwargs):
        self.on_release = kwargs.pop("on_release", None)
        super().__init__(**kwargs)
        self._segments: list[tuple[float, tuple[float, float, float, float]]] = []
        self._total = 0.0
        self.bind(pos=self._redraw, size=self._redraw)

    def set_breakdown(self, breakdown) -> None:
        segments = []
        if breakdown is not None:
            for attr, color in self._SEGMENT_COLORS:
                raw_value = getattr(breakdown, attr, Decimal("0")) or Decimal("0")
                value = Decimal(str(raw_value))
                if value > 0:
                    segments.append((float(value), color))
        self._segments = segments
        self._total = sum(value for value, _color in segments)
        self._redraw()

    def has_data(self) -> bool:
        return self._total > 0

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos) and self.has_data():
            if self.on_release is not None:
                self.on_release(self)
            return True
        return super().on_touch_down(touch)

    def _redraw(self, *_args):
        self.canvas.clear()
        if self.width <= 0 or self.height <= 0:
            return
        center_x = self.x + self.width / 2
        center_y = self.y + self.height / 2
        radius = min(self.width, self.height) * 0.35
        ring_width = max(dp(10), min(self.width, self.height) * 0.09)
        with self.canvas:
            Color(0.06, 0.14, 0.19, 0.56)
            Line(circle=(center_x, center_y, radius, 0, 360), width=ring_width + dp(2))
            Color(0.79, 0.96, 1.0, 0.16)
            Line(
                circle=(center_x, center_y, radius - ring_width * 0.62, 0, 360),
                width=dp(1),
            )
            total = self._total
            if total <= 0:
                Color(0.79, 0.96, 1.0, 0.22)
                Line(
                    circle=(center_x, center_y, radius + ring_width * 0.65, 0, 360),
                    width=dp(1),
                )
                return
            start_angle = 90.0
            for value, color in self._segments:
                extent = 360.0 * value / total
                Color(*color)
                Line(
                    circle=(
                        center_x,
                        center_y,
                        radius,
                        start_angle,
                        start_angle + extent,
                    ),
                    width=ring_width,
                )
                start_angle += extent
            Color(0.79, 0.96, 1.0, 0.32)
            Line(
                circle=(center_x, center_y, radius + ring_width * 0.65, 0, 360),
                width=dp(1),
            )
            Color(0.79, 0.96, 1.0, 0.18)
            Line(
                circle=(center_x, center_y, radius - ring_width * 0.65, 0, 360),
                width=dp(1),
            )

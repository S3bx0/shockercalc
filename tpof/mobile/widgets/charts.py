"""Lightweight, animated chart widgets for the mobile UI."""

from __future__ import annotations

from decimal import Decimal

from kivy.animation import Animation
from kivy.core.text import Label as CoreLabel
from kivy.graphics import Color, Ellipse, Line, Rectangle
from kivy.metrics import dp
from kivy.properties import BooleanProperty, NumericProperty
from kivy.uix.widget import Widget

from tpof.mobile.chart_data import CostChartSegment, prepare_cost_segments


class LaborPieChart(Widget):
    """Premium donut chart for the labor cost structure."""

    SEGMENT_COLORS = (
        ("labor_cost", (0.08, 0.64, 0.86, 1.0)),
        ("travel_cost", (0.08, 0.78, 0.70, 1.0)),
        ("lift_cost", (0.43, 0.39, 0.82, 1.0)),
        ("container_cost", (0.24, 0.66, 0.88, 1.0)),
        ("hotel_cost", (0.13, 0.53, 0.74, 1.0)),
        ("allowance_cost", (0.48, 0.76, 0.88, 1.0)),
        ("regenerative_meal_cost", (0.14, 0.70, 0.63, 1.0)),
        ("additional_costs_value", (0.58, 0.47, 0.82, 1.0)),
    )
    _SEGMENT_COLORS = SEGMENT_COLORS

    progress = NumericProperty(1.0)
    dark_mode = BooleanProperty(True)

    def __init__(self, **kwargs):
        self.on_release = kwargs.pop("on_release", None)
        super().__init__(**kwargs)
        self._segments: list[CostChartSegment] = []
        self._total = Decimal("0")
        self._center_label = ""
        self._center_value = ""
        self._texture_cache: dict[tuple, object] = {}
        self.bind(
            pos=self._redraw,
            size=self._redraw,
            progress=self._redraw,
            dark_mode=self._theme_changed,
        )

    def set_data(
        self,
        items,
        *,
        center_label: str = "",
        center_value: str = "",
        animate: bool = True,
    ) -> None:
        self._segments, self._total = prepare_cost_segments(items)
        self._center_label = str(center_label or "")
        self._center_value = str(center_value or "")
        self._texture_cache.clear()
        Animation.cancel_all(self, "progress")
        if animate and self._total > 0:
            self.progress = 0.0
            Animation(progress=1.0, duration=0.75, transition="out_cubic").start(self)
        else:
            self.progress = 1.0
            self._redraw()

    def set_breakdown(self, breakdown) -> None:
        """Compatibility adapter retained while the screen controller is refactored."""
        items = []
        if breakdown is not None:
            for attr, color in self._SEGMENT_COLORS:
                items.append(
                    {
                        "key": attr,
                        "label": attr,
                        "value": getattr(breakdown, attr, Decimal("0")),
                        "color": color,
                    }
                )
        self.set_data(items)

    def set_dark(self, enabled: bool) -> None:
        self.dark_mode = bool(enabled)

    def has_data(self) -> bool:
        return self._total > 0

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos) and self.has_data():
            # TODO: Add angle-based segment selection after device-level UX tests.
            if self.on_release is not None:
                self.on_release(self)
            return True
        return super().on_touch_down(touch)

    def _theme_changed(self, *_args) -> None:
        self._texture_cache.clear()
        self._redraw()

    def _label_texture(self, text: str, font_size: float, color, width: float):
        key = (text, round(font_size, 2), tuple(color), round(width, 1))
        cached = self._texture_cache.get(key)
        if cached is not None:
            return cached
        label = CoreLabel(
            text=text,
            font_size=font_size,
            color=color,
            text_size=(max(dp(40), width), None),
            halign="center",
            valign="middle",
        )
        label.refresh()
        self._texture_cache[key] = label.texture
        return label.texture

    @staticmethod
    def _draw_texture(texture, center_x: float, center_y: float) -> None:
        Rectangle(
            texture=texture,
            pos=(center_x - texture.size[0] / 2, center_y - texture.size[1] / 2),
            size=texture.size,
        )

    def _redraw(self, *_args):
        self.canvas.clear()
        if self.width <= 0 or self.height <= 0:
            return
        size = min(self.width, self.height)
        center_x = self.x + self.width / 2
        center_y = self.y + self.height / 2
        radius = size * 0.32
        ring_width = max(dp(16), size * 0.105)
        dark = bool(self.dark_mode)
        track = (0.09, 0.18, 0.24, 0.92) if dark else (0.70, 0.82, 0.87, 0.72)
        center_color = (0.045, 0.095, 0.145, 1.0) if dark else (0.91, 0.97, 0.99, 1.0)
        text_color = (0.90, 0.98, 1.0, 1.0) if dark else (0.035, 0.16, 0.23, 1.0)
        muted_color = (0.62, 0.78, 0.84, 1.0) if dark else (0.23, 0.43, 0.50, 1.0)

        with self.canvas:
            Color(*track)
            Line(circle=(center_x, center_y, radius, 0, 360), width=ring_width)
            Color(*center_color)
            inner_radius = max(dp(24), radius - ring_width * 0.78)
            Ellipse(
                pos=(center_x - inner_radius, center_y - inner_radius),
                size=(inner_radius * 2, inner_radius * 2),
            )

            if self._total > 0 and self.progress > 0:
                progress = max(0.0, min(1.0, float(self.progress)))
                for segment in self._segments:
                    sweep = segment.sweep_angle * progress
                    gap = min(2.2, max(0.35, sweep * 0.08))
                    visible_sweep = max(0.0, sweep - gap)
                    if visible_sweep <= 0:
                        continue
                    start = segment.start_angle
                    end = start + visible_sweep
                    Color(segment.color[0], segment.color[1], segment.color[2], 0.16)
                    Line(
                        circle=(center_x, center_y, radius, start, end),
                        width=ring_width + dp(5),
                    )
                    Color(*segment.color)
                    Line(
                        circle=(center_x, center_y, radius, start, end),
                        width=ring_width,
                    )

            Color(0.64, 0.92, 1.0, 0.22 if dark else 0.30)
            Line(circle=(center_x, center_y, radius + ring_width * 0.62, 0, 360), width=dp(1))

            if self._center_label:
                label_texture = self._label_texture(
                    self._center_label,
                    dp(10.5),
                    muted_color,
                    inner_radius * 1.55,
                )
                self._draw_texture(label_texture, center_x, center_y + dp(10))
            if self._center_value:
                value_font_size = dp(12.5 if len(self._center_value) <= 15 else 10.5)
                value_texture = self._label_texture(
                    self._center_value,
                    value_font_size,
                    text_color,
                    inner_radius * 1.75,
                )
                self._draw_texture(value_texture, center_x, center_y - dp(13))

"""Animated stage icon widgets for mobile result cards."""

import math

from kivy.clock import Clock
from kivy.graphics import Color, Ellipse, Line, RoundedRectangle
from kivy.metrics import dp
from kivy.uix.widget import Widget
from kivymd.uix.boxlayout import MDBoxLayout


class StageIconBadge(MDBoxLayout):
    """Znak etapu wyniku z subtelnym tłem i akcentem koloru."""

    def __init__(self, *, accent, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.size_hint_x = None
        self.size_hint_y = None
        self.accent = accent
        with self.canvas.before:
            Color(1, 1, 1, 0.075)
            self._outer = RoundedRectangle(
                pos=self.pos, size=self.size, radius=[dp(14)] * 4
            )
            Color(accent[0], accent[1], accent[2], 0.18)
            self._inner = RoundedRectangle(
                pos=self.pos, size=self.size, radius=[dp(13)] * 4
            )
        self.bind(pos=self._sync_canvas, size=self._sync_canvas)
        self._sync_canvas()

    def _sync_canvas(self, *_args):
        radius = [min(self.width, self.height) * 0.32] * 4
        self._outer.pos = self.pos
        self._outer.size = self.size
        self._outer.radius = radius
        inset = dp(1.5)
        self._inner.pos = (self.x + inset, self.y + inset)
        self._inner.size = (
            max(0, self.width - inset * 2),
            max(0, self.height - inset * 2),
        )
        self._inner.radius = [max(0, radius[0] - inset)] * 4


class StageMotionIcon(Widget):
    """Lekka animacja etapu wyniku bez dokladania plikow GIF do paczki."""

    def __init__(self, *, mode: str, accent, **kwargs):
        super().__init__(**kwargs)
        self.mode = mode
        self.accent = accent
        self.font_size = "24sp"
        self._elapsed = 0.0
        self._event = None
        self._snow_lines = []
        self._snow_dots = []
        with self.canvas:
            if self.mode == "zamrozenie":
                self._snow_color = Color(*accent[:3], 0.95)
                for _index in range(18):
                    self._snow_lines.append(Line(points=[], width=dp(1.45), cap="round"))
                self._frost_color = Color(0.90, 0.98, 1.0, 0.0)
                for _index in range(7):
                    self._snow_dots.append(Ellipse(pos=(0, 0), size=(0, 0)))
            else:
                self._tube_bg_color = Color(1, 1, 1, 0.16)
                self._tube_bg = RoundedRectangle(pos=(0, 0), size=(0, 0), radius=[dp(4)] * 4)
                self._fill_color = Color(*accent[:3], 0.92)
                self._tube_fill = RoundedRectangle(pos=(0, 0), size=(0, 0), radius=[dp(4)] * 4)
                self._bulb_fill = Ellipse(pos=(0, 0), size=(0, 0))
                self._edge_color = Color(1, 1, 1, 0.34)
                self._tube_edge = Line(points=[], width=dp(1.1), cap="round")
                self._tick = Line(points=[], width=dp(0.9), cap="round")
        self.bind(pos=self._sync_canvas, size=self._sync_canvas)
        self._event = Clock.schedule_interval(self._tick_motion, 1.0 / 24.0)
        self._sync_canvas()

    @staticmethod
    def _mix(left, right, fraction):
        fraction = max(0.0, min(1.0, float(fraction)))
        return tuple(
            left[index] * (1.0 - fraction) + right[index] * fraction
            for index in range(3)
        )

    def on_parent(self, _instance, parent):
        if parent is None and self._event is not None:
            self._event.cancel()
            self._event = None

    def _tick_motion(self, dt):
        self._elapsed += min(float(dt), 0.12)
        self._sync_canvas()

    def _sync_canvas(self, *_args):
        if self.width <= 0 or self.height <= 0:
            return
        if self.mode == "zamrozenie":
            self._sync_snowflake()
        else:
            self._sync_thermometer()

    def _sync_thermometer(self):
        size = min(self.width, self.height)
        cx = self.x + self.width * 0.5
        cy = self.y + self.height * 0.5
        phase = (self._elapsed / 2.6) % 1.0
        phase = phase * phase * (3.0 - 2.0 * phase)
        if self.mode == "domrozenie":
            color = self._mix((0.18, 0.86, 1.0), (0.38, 0.20, 0.92), phase)
            level = 0.78 - 0.46 * phase
        else:
            color = self._mix((0.96, 0.28, 0.20), (0.08, 0.72, 0.92), phase)
            level = 0.86 - 0.60 * phase
        tube_w = max(dp(5), size * 0.14)
        tube_h = size * 0.47
        bulb = size * 0.28
        tube_x = cx - tube_w * 0.5
        tube_y = cy - size * 0.08
        fill_h = max(dp(4), tube_h * level)
        self._fill_color.rgba = (color[0], color[1], color[2], 0.94)
        self._tube_bg.pos = (tube_x, tube_y)
        self._tube_bg.size = (tube_w, tube_h)
        self._tube_bg.radius = [tube_w * 0.5] * 4
        self._tube_fill.pos = (tube_x, tube_y)
        self._tube_fill.size = (tube_w, fill_h)
        self._tube_fill.radius = [tube_w * 0.5] * 4
        self._bulb_fill.pos = (cx - bulb * 0.5, tube_y - bulb * 0.58)
        self._bulb_fill.size = (bulb, bulb)
        self._tube_edge.points = [
            cx,
            tube_y,
            cx,
            tube_y + tube_h,
        ]
        self._tick.points = [
            cx + tube_w * 0.9,
            tube_y + tube_h * (0.75 - 0.5 * phase),
            cx + tube_w * 1.9,
            tube_y + tube_h * (0.75 - 0.5 * phase),
        ]

    def _sync_snowflake(self):
        size = min(self.width, self.height)
        cx = self.x + self.width * 0.5
        cy = self.y + self.height * 0.5
        phase = (math.sin(self._elapsed * 1.45) + 1.0) * 0.5
        color = self._mix((0.18, 0.84, 0.95), self.accent[:3], phase)
        self._snow_color.rgba = (color[0], color[1], color[2], 0.84 + 0.14 * phase)
        radius = size * (0.26 + 0.05 * phase)
        branch = radius * 0.34
        lines = []
        for arm in range(6):
            angle = math.tau * arm / 6.0 - math.pi / 2.0
            end_x = cx + math.cos(angle) * radius
            end_y = cy + math.sin(angle) * radius
            lines.append((cx, cy, end_x, end_y))
            for side in (-1, 1):
                side_angle = angle + side * math.radians(42)
                base_x = cx + math.cos(angle) * radius * 0.58
                base_y = cy + math.sin(angle) * radius * 0.58
                lines.append(
                    (
                        base_x,
                        base_y,
                        base_x - math.cos(side_angle) * branch,
                        base_y - math.sin(side_angle) * branch,
                    )
                )
        for line, points in zip(self._snow_lines, lines):
            line.points = points
        self._frost_color.rgba = (0.90, 0.98, 1.0, 0.16 + 0.34 * phase)
        for index, dot in enumerate(self._snow_dots):
            orbit = radius * (0.35 + (index % 3) * 0.22)
            angle = self._elapsed * (0.8 + index * 0.08) + index * 1.37
            dot_size = dp(1.4 + (index % 3) * 0.45)
            dot.pos = (
                cx + math.cos(angle) * orbit - dot_size * 0.5,
                cy + math.sin(angle) * orbit - dot_size * 0.5,
            )
            dot.size = (dot_size, dot_size)

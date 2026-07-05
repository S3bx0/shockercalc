"""Animated bottom navigation widgets for the mobile UI."""

import math

from kivy.clock import Clock
from kivy.graphics import Color, Line, RoundedRectangle
from kivy.metrics import dp
from kivy.uix.widget import Widget
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel

from tpof.mobile.constants import BRAND_CYAN, BRAND_ICE


class BottomNavMotionIcon(Widget):
    """Wlasna lekka ikona dolnej zakladki z kontrolowana animacja."""

    def __init__(self, *, mode: str, **kwargs):
        super().__init__(**kwargs)
        self.mode = mode
        self.active = False
        self._motion = 0.0
        self._rotation = 0.0
        self._valve_phase = 0.0
        self._calc_phase = 0.0
        self._event = None
        self._light_mode = False
        self._lines = []
        with self.canvas.before:
            self._chip_color = Color(1, 1, 1, 0.0)
            self._chip = RoundedRectangle(
                pos=self.pos, size=self.size, radius=[dp(14)] * 4
            )
        with self.canvas:
            self._icon_color = Color(*BRAND_ICE[:3], 0.72)
            line_count = 18 if self.mode == "snowflake" else 11 if self.mode == "calculator" else 5
            for _index in range(line_count):
                self._lines.append(Line(points=[], width=dp(1.15), cap="round"))
        self.bind(pos=self._sync_canvas, size=self._sync_canvas)
        self._sync_canvas()

    def on_parent(self, _instance, parent):
        if parent is None and self._event is not None:
            self._event.cancel()
            self._event = None

    def set_active(self, active: bool):
        self.active = bool(active)
        if self._light_mode:
            self._chip_color.rgba = (
                (*BRAND_CYAN[:3], 0.18) if self.active else (1, 1, 1, 0.0)
            )
            self._icon_color.rgba = (
                (0.02, 0.42, 0.58, 0.98)
                if self.active
                else (0.21, 0.33, 0.40, 0.66)
            )
        else:
            self._chip_color.rgba = (1, 1, 1, 0.24 if self.active else 0.0)
            self._icon_color.rgba = (
                (*BRAND_ICE[:3], 0.98)
                if self.active
                else (0.78, 0.84, 0.88, 0.78)
            )
        self._sync_canvas()

    def set_theme_light(self, light: bool):
        self._light_mode = bool(light)
        self.set_active(self.active)

    def play(self):
        self._motion = 0.0
        if self._event is None:
            self._event = Clock.schedule_interval(self._tick_motion, 1.0 / 30.0)

    def _tick_motion(self, dt):
        self._motion += min(float(dt), 0.12) / 0.48
        fraction = min(self._motion, 1.0)
        eased = fraction * fraction * (3.0 - 2.0 * fraction)
        if self.mode == "snowflake":
            self._rotation = math.tau * eased
        elif self.mode == "valve":
            self._valve_phase = math.sin(math.pi * eased)
        else:
            self._calc_phase = math.sin(math.pi * eased)
        self._sync_canvas()
        if fraction >= 1.0 and self._event is not None:
            self._event.cancel()
            self._event = None
            self._motion = 0.0
            self._rotation = 0.0
            self._valve_phase = 0.0
            self._calc_phase = 0.0
            self._sync_canvas()

    def _sync_canvas(self, *_args):
        if self.width <= 0 or self.height <= 0:
            return
        self._chip.pos = self.pos
        self._chip.size = self.size
        self._chip.radius = [min(self.width, self.height) * 0.30] * 4
        if self.mode == "snowflake":
            self._sync_snowflake()
        elif self.mode == "valve":
            self._sync_valve()
        else:
            self._sync_calculator()

    def _sync_snowflake(self):
        cx = self.center_x
        cy = self.center_y
        radius = min(self.width, self.height) * 0.30
        inner = radius * 0.16
        branch = radius * 0.34
        line_index = 0
        for arm in range(6):
            angle = self._rotation + arm * math.tau / 6.0
            outer_x = cx + math.cos(angle) * radius
            outer_y = cy + math.sin(angle) * radius
            inner_x = cx + math.cos(angle) * inner
            inner_y = cy + math.sin(angle) * inner
            self._lines[line_index].points = [inner_x, inner_y, outer_x, outer_y]
            line_index += 1
            bx = cx + math.cos(angle) * radius * 0.62
            by = cy + math.sin(angle) * radius * 0.62
            for side in (-1, 1):
                branch_angle = angle + side * 2.45
                self._lines[line_index].points = [
                    bx,
                    by,
                    bx + math.cos(branch_angle) * branch,
                    by + math.sin(branch_angle) * branch,
                ]
                line_index += 1

    def _sync_valve(self):
        cx = self.center_x
        cy = self.center_y
        width = self.width * 0.62
        height = self.height * 0.50
        left = cx - width * 0.5
        right = cx + width * 0.5
        top = cy + height * 0.5
        bottom = cy - height * 0.5
        blade_shift = self._valve_phase * height * 0.32
        self._lines[0].points = [left, cy, right, cy]
        self._lines[1].points = [left, bottom, left, top]
        self._lines[2].points = [right, bottom, right, top]
        self._lines[3].points = [
            cx - width * 0.24,
            bottom,
            cx + width * 0.24,
            top - blade_shift,
        ]
        self._lines[4].points = [
            cx - width * 0.24,
            top,
            cx + width * 0.24,
            bottom + blade_shift,
        ]

    def _sync_calculator(self):
        cx = self.center_x
        cy = self.center_y
        width = self.width * 0.46
        height = self.height * 0.58
        left = cx - width * 0.5
        right = cx + width * 0.5
        top = cy + height * 0.5
        bottom = cy - height * 0.5
        pulse = self._calc_phase * height * 0.05
        self._lines[0].points = [left, bottom, left, top, right, top, right, bottom, left, bottom]
        self._lines[1].points = [
            left + width * 0.18,
            top - height * 0.25 + pulse,
            right - width * 0.18,
            top - height * 0.25 + pulse,
        ]
        line_index = 2
        key_radius = min(width, height) * 0.06
        for row in range(3):
            for col in range(3):
                kx = left + width * (0.24 + col * 0.26)
                ky = bottom + height * (0.20 + row * 0.18)
                scale = 1.0 + self._calc_phase * (0.18 if row == col else 0.08)
                self._lines[line_index].points = [
                    kx - key_radius * scale,
                    ky,
                    kx + key_radius * scale,
                    ky,
                ]
                line_index += 1


class BottomNavTab(MDBoxLayout):
    """Dotykalny przycisk dolnego menu z wlasna animowana ikona."""

    def __init__(self, *, name: str, text: str, mode: str, on_select, **kwargs):
        super().__init__(**kwargs)
        self.name = name
        self.orientation = "vertical"
        self.size_hint_x = 1
        self.spacing = dp(1)
        self.padding = [0, dp(5), 0, dp(4)]
        self._on_select = on_select
        self._light_mode = False
        self.icon_widget = BottomNavMotionIcon(
            mode=mode,
            size_hint=(None, None),
            size=(dp(56), dp(34)),
            pos_hint={"center_x": 0.5},
        )
        self.label = MDLabel(
            text=text,
            halign="center",
            theme_text_color="Custom",
            text_color=(0.78, 0.84, 0.88, 0.82),
            font_size="12sp",
            size_hint_y=None,
            height=dp(20),
        )
        self.add_widget(self.icon_widget)
        self.add_widget(self.label)

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self._on_select(self.name)
            return True
        return super().on_touch_down(touch)

    def set_active(self, active: bool):
        self.icon_widget.set_active(active)
        if self._light_mode:
            self.label.text_color = (
                (0.02, 0.42, 0.58, 1) if active else (0.23, 0.33, 0.40, 0.72)
            )
        else:
            self.label.text_color = (
                BRAND_ICE if active else (0.78, 0.84, 0.88, 0.82)
            )

    def set_theme_light(self, light: bool):
        self._light_mode = bool(light)
        self.icon_widget.set_theme_light(light)
        self.set_active(self.icon_widget.active)

    def play(self):
        self.icon_widget.play()

    def set_text(self, text: str):
        self.label.text = text

    def set_metrics(self, *, icon_size, label_sp: int):
        self.icon_widget.size = (icon_size, max(dp(30), icon_size * 0.62))
        self.label.font_size = f"{label_sp}sp"

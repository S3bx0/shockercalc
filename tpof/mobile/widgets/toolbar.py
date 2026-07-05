"""Toolbar and chip widgets for the mobile UI."""

from kivy.graphics import Color, Line, Rectangle, RoundedRectangle
from kivy.graphics.texture import Texture
from kivy.metrics import dp
from kivymd.uix.boxlayout import MDBoxLayout

from tpof.mobile.constants import BRAND_ICE


class BrandToolbar(MDBoxLayout):
    """Gradientowy pasek naglowka nawiazujacy do nowego logo."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.md_bg_color = (0, 0, 0, 0)
        self._gradient_texture = self._make_gradient_texture()
        with self.canvas.before:
            Color(1, 1, 1, 1)
            self._background = Rectangle(pos=self.pos, size=self.size)
            Color(1, 1, 1, 0.10)
            self._shine_left = Line(points=[], width=dp(16))
            Color(1, 1, 1, 0.06)
            self._shine_right = Line(points=[], width=dp(22))
            Color(0, 0, 0, 0.28)
            self._bottom_shadow = Rectangle(pos=self.pos, size=(0, 0))
            Color(*BRAND_ICE[:3], 0.72)
            self._bottom_accent = Rectangle(pos=self.pos, size=(0, 0))
        self._background.texture = self._gradient_texture
        self.bind(pos=self._sync_canvas, size=self._sync_canvas)
        self._sync_canvas()

    @staticmethod
    def _make_gradient_texture():
        stops = [
            (0.0, (3, 17, 36, 255)),
            (0.42, (6, 78, 126, 255)),
            (0.74, (11, 142, 182, 255)),
            (1.0, (16, 179, 196, 255)),
        ]
        texture = Texture.create(size=(192, 1), colorfmt="rgba")
        pixels = bytearray()
        for col in range(192):
            fraction = col / 191.0
            color = stops[-1][1]
            for index in range(len(stops) - 1):
                left_stop, left_color = stops[index]
                right_stop, right_color = stops[index + 1]
                if left_stop <= fraction <= right_stop:
                    local = (fraction - left_stop) / (right_stop - left_stop)
                    local = local * local * (3.0 - 2.0 * local)
                    color = tuple(
                        int(left_color[channel] * (1.0 - local) + right_color[channel] * local)
                        for channel in range(4)
                    )
                    break
            pixels.extend(color)
        texture.blit_buffer(bytes(pixels), colorfmt="rgba", bufferfmt="ubyte")
        texture.mag_filter = "linear"
        texture.min_filter = "linear"
        return texture

    def _sync_canvas(self, *_args):
        self._background.pos = self.pos
        self._background.size = self.size
        self._bottom_shadow.pos = (self.x, self.y)
        self._bottom_shadow.size = (self.width, dp(8))
        self._bottom_accent.pos = (self.x, self.y)
        self._bottom_accent.size = (self.width, dp(2))
        self._shine_left.points = [
            self.x + self.width * 0.16,
            self.top + dp(8),
            self.x + self.width * 0.02,
            self.y - dp(8),
        ]
        self._shine_right.points = [
            self.x + self.width * 0.78,
            self.top + dp(12),
            self.x + self.width * 0.57,
            self.y - dp(12),
        ]


class FrostChip(MDBoxLayout):
    """Mała półprzezroczysta kapsuła pod ikonę."""

    def __init__(self, *, active: bool = False, accent=BRAND_ICE, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.size_hint_x = None
        self.size_hint_y = None
        self.pos_hint = {"center_y": 0.5}
        self.active = active
        self.accent = accent
        with self.canvas.before:
            self._outer_color = Color(1, 1, 1, 0.16)
            self._outer = RoundedRectangle(
                pos=self.pos, size=self.size, radius=[dp(18)] * 4
            )
            self._inner_color = Color(1, 1, 1, 0.08)
            self._inner = RoundedRectangle(
                pos=self.pos, size=self.size, radius=[dp(17)] * 4
            )
        self.bind(pos=self._sync_canvas, size=self._sync_canvas)
        self.set_active(active)

    def set_active(self, active: bool):
        self.active = bool(active)
        accent = self.accent
        self._outer_color.rgba = (
            (accent[0], accent[1], accent[2], 0.42)
            if self.active
            else (1, 1, 1, 0.13)
        )
        self._inner_color.rgba = (
            (1, 1, 1, 0.17)
            if self.active
            else (1, 1, 1, 0.075)
        )

    def _sync_canvas(self, *_args):
        radius = [min(self.width, self.height) * 0.36] * 4
        self._outer.pos = self.pos
        self._outer.size = self.size
        self._outer.radius = radius
        inset = dp(1.15)
        self._inner.pos = (self.x + inset, self.y + inset)
        self._inner.size = (
            max(0, self.width - inset * 2),
            max(0, self.height - inset * 2),
        )
        self._inner.radius = [max(0, radius[0] - inset)] * 4

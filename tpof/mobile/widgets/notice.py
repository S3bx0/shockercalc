"""Centered notice widget for mobile validation messages."""

from kivy.clock import Clock
from kivy.graphics import Color, Line, RoundedRectangle
from kivy.metrics import dp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel

from tpof.mobile.constants import BRAND_CYAN

class CenterNotice(MDBoxLayout):
    """Centralny komunikat walidacji, czytelniejszy niz dolny snackbar."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.padding = [dp(18), dp(13), dp(18), dp(13)]
        self._visible_size_hint = (0.88, None)
        self.size_hint = (None, None)
        self.size = (0, 0)
        self.opacity = 0
        self.disabled = True
        self.pos_hint = {"center_x": 0.5, "center_y": 0.54}
        with self.canvas.before:
            self._shadow_color = Color(0, 0, 0, 0)
            self._shadow = RoundedRectangle(
                pos=self.pos, size=self.size, radius=[dp(18)] * 4
            )
            self._bg_color = Color(0.02, 0.10, 0.17, 0)
            self._bg = RoundedRectangle(
                pos=self.pos, size=self.size, radius=[dp(18)] * 4
            )
            self._border_color = Color(*BRAND_CYAN[:3], 0)
            self._border = Line(width=dp(1.15))
        self.label = MDLabel(
            text="",
            halign="center",
            valign="middle",
            theme_text_color="Custom",
            text_color=(0.94, 1.0, 1.0, 1),
            font_style="Body1",
        )
        self.add_widget(self.label)
        self.bind(pos=self._sync_canvas, size=self._sync_canvas, opacity=self._sync_alpha)
        self.label.bind(texture_size=lambda *_: self._fit_height())

    def show(self, message: str):
        from kivy.animation import Animation

        Animation.cancel_all(self, "opacity")
        self.label.text = str(message)
        self.size_hint = self._visible_size_hint
        self.height = dp(92)
        self.disabled = False
        self.opacity = 1
        Clock.schedule_once(lambda *_: self._fit_height(), 0)
        fade = Animation(opacity=1, d=1.5) + Animation(opacity=0, d=0.5)
        fade.bind(on_complete=self._hide_after_fade)
        fade.start(self)

    def _hide_after_fade(self, *_args):
        self.opacity = 0
        self.disabled = True
        self.size_hint = (None, None)
        self.size = (0, 0)

    def on_touch_down(self, touch):
        if self.disabled or self.opacity <= 0.05:
            return False
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if self.disabled or self.opacity <= 0.05:
            return False
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        if self.disabled or self.opacity <= 0.05:
            return False
        return super().on_touch_up(touch)

    def _fit_height(self):
        text_width = max(self.width - dp(36), dp(120))
        self.label.text_size = (text_width, None)
        self.height = max(dp(78), min(dp(132), self.label.texture_size[1] + dp(34)))
        self._sync_canvas()

    def _sync_alpha(self, *_args):
        alpha = max(0.0, min(1.0, float(self.opacity)))
        self._shadow_color.rgba = (0, 0, 0, 0.30 * alpha)
        self._bg_color.rgba = (0.02, 0.10, 0.17, 0.94 * alpha)
        self._border_color.rgba = (*BRAND_CYAN[:3], 0.82 * alpha)

    def _sync_canvas(self, *_args):
        self._shadow.pos = (self.x + dp(2), self.y - dp(3))
        self._shadow.size = self.size
        self._bg.pos = self.pos
        self._bg.size = self.size
        radius = min(dp(18), self.height * 0.22)
        self._shadow.radius = [radius] * 4
        self._bg.radius = [radius] * 4
        self._border.rounded_rectangle = (
            self.x,
            self.y,
            self.width,
            self.height,
            radius,
        )
        self._sync_alpha()

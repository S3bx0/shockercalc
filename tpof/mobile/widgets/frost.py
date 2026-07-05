"""Frost background widget for the mobile UI."""

import math

from kivy.clock import Clock
from kivy.graphics import Color, Line, Rectangle
from kivy.graphics.texture import Texture
from kivy.metrics import dp
from kivy.uix.widget import Widget


class FrostBackground(Widget):
    """Subtelne, wolno poruszajace sie lodowe refleksy pod interfejsem."""

    PARTICLE_COUNT = 18

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._elapsed = 0.0
        self._dark = True
        self._particles = [
            {
                "x": ((index * 47) % 101) / 100.0,
                "y": ((index * 71 + 13) % 103) / 102.0,
                "speed": 0.0018 + (index % 5) * 0.00035,
                "phase": index * 1.73,
                "size": dp(1.6 + (index % 4) * 0.45),
            }
            for index in range(self.PARTICLE_COUNT)
        ]

        with self.canvas.before:
            Color(1, 1, 1, 1)
            self._background = Rectangle(pos=self.pos, size=self.size)
            self._band_colors = []
            self._bands = []
            for _index in range(4):
                color = Color(1, 1, 1, 0.04)
                band = Line(points=[], width=dp(30), cap="none")
                self._band_colors.append(color)
                self._bands.append(band)

        self._particle_graphics = []
        with self.canvas:
            for _particle in self._particles:
                color = Color(0.48, 0.86, 1.0, 0.14)
                horizontal = Line(width=0.65)
                vertical = Line(width=0.65)
                diagonal = Line(width=0.45)
                self._particle_graphics.append(
                    (color, horizontal, vertical, diagonal)
                )

        self.bind(pos=self._sync_background, size=self._sync_background)
        self.set_dark(True)
        self._animation_event = Clock.schedule_interval(
            self._animate_particles, 1.0 / 15.0
        )

    def set_dark(self, dark: bool):
        self._dark = bool(dark)
        top = (5, 20, 38) if self._dark else (226, 244, 252)
        bottom = (8, 52, 84) if self._dark else (184, 222, 241)
        texture = Texture.create(size=(1, 96), colorfmt="rgba")
        pixels = bytearray()
        for row in range(96):
            fraction = row / 95.0
            eased = fraction * fraction * (3.0 - 2.0 * fraction)
            pixels.extend(
                int(bottom[channel] * (1.0 - eased) + top[channel] * eased)
                for channel in range(3)
            )
            pixels.append(255)
        texture.blit_buffer(bytes(pixels), colorfmt="rgba", bufferfmt="ubyte")
        texture.mag_filter = "linear"
        texture.min_filter = "linear"
        self._background.texture = texture
        self._gradient_texture = texture
        for color, *_lines in self._particle_graphics:
            color.rgba = (
                (0.48, 0.86, 1.0, 0.14)
                if self._dark
                else (0.12, 0.48, 0.68, 0.12)
            )
        band_palette = (
            [
                (0.12, 0.58, 0.82, 0.06),
                (0.04, 0.74, 0.80, 0.04),
                (1.00, 1.00, 1.00, 0.03),
                (0.25, 0.72, 1.00, 0.028),
            ]
            if self._dark
            else [
                (0.11, 0.59, 0.82, 0.06),
                (0.03, 0.70, 0.78, 0.045),
                (1.00, 1.00, 1.00, 0.10),
                (0.16, 0.58, 0.94, 0.04),
            ]
        )
        for color, rgba in zip(self._band_colors, band_palette):
            color.rgba = rgba
        self._sync_background()

    def _sync_background(self, *_args):
        self._background.pos = self.pos
        self._background.size = self.size
        self._position_bands()
        self._position_particles()

    def _position_bands(self):
        if self.width <= 0 or self.height <= 0:
            return
        x, y, width, height = self.x, self.y, self.width, self.height
        specs = [
            (-0.22, 0.94, 0.26, 1.13),
            (0.74, 1.02, 1.14, 0.78),
            (-0.16, 0.16, 0.22, -0.04),
            (0.64, 0.18, 1.10, -0.04),
        ]
        for band, (x1, y1, x2, y2) in zip(self._bands, specs):
            band.points = [
                x + width * x1,
                y + height * y1,
                x + width * x2,
                y + height * y2,
            ]

    def _animate_particles(self, dt):
        self._elapsed += min(float(dt), 0.2)
        for particle in self._particles:
            particle["y"] += particle["speed"] * min(float(dt), 0.2) * 15.0
            if particle["y"] > 1.04:
                particle["y"] = -0.04
        self._position_particles()

    def _position_particles(self):
        if self.width <= 0 or self.height <= 0:
            return
        for particle, graphics in zip(
            self._particles, self._particle_graphics
        ):
            _color, horizontal, vertical, diagonal = graphics
            drift = math.sin(self._elapsed * 0.32 + particle["phase"]) * dp(5)
            x = self.x + particle["x"] * self.width + drift
            y = self.y + particle["y"] * self.height
            size = particle["size"]
            horizontal.points = [x - size, y, x + size, y]
            vertical.points = [x, y - size, x, y + size]
            diagonal.points = [
                x - size * 0.55,
                y - size * 0.55,
                x + size * 0.55,
                y + size * 0.55,
            ]

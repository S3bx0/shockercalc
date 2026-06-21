"""Render a GIF preview of the native Refrigeration Calc intro motion."""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "assets" / "brand" / "approved-emblem-reference.png"
OUTPUT = ROOT / "assets" / "brand" / "previews" / "intro-motion-preview.gif"

SIZE = 720
FPS = 20
FRAME_COUNT = 92
POLYGON_SIDES = 8

ORBIT_COLORS = ((180, 229, 250), (22, 169, 181), (39, 137, 232))
ORBIT_ROTATIONS = (-12.0, 3.0, 18.0)
ORBIT_OFFSET_X = (-0.08, 0.065, 0.06)
ORBIT_OFFSET_Y = (-0.08, -0.02, 0.08)
RADIAL_ANGLES = (
    -73, -55, -41, -26, -12, 4, 19, 33, 49, 68, 86,
    107, 126, 145, 161, 177, 195, 214, 233, 252, 278, 315,
)
RADIAL_SPEEDS = (
    0.82, 1.04, 0.91, 1.22, 0.76, 1.14, 0.88, 1.29, 0.97, 1.08, 0.79,
    1.18, 0.93, 1.25, 0.85, 1.12, 0.74, 1.31, 1.01, 0.89, 1.16, 0.95,
)
RADIAL_PHASES = (
    0.03, 0.47, 0.81, 0.24, 0.66, 0.12, 0.91, 0.36, 0.58, 0.75, 0.18,
    0.69, 0.42, 0.87, 0.07, 0.53, 0.96, 0.30, 0.63, 0.15, 0.78, 0.40,
)
RADIAL_SIZE_FACTORS = (
    0.86, 1.12, 0.94, 1.24, 0.82, 1.04, 0.91, 1.18, 0.88, 1.09, 0.79,
    1.20, 0.97, 1.15, 0.84, 1.06, 0.76, 1.22, 1.01, 0.90, 1.17, 0.95,
)
ORBIT_SPEEDS = (1.93, 2.21, 2.49)


def clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def ease_out_cubic(value: float) -> float:
    inverse = 1.0 - clamp(value)
    return 1.0 - inverse**3


def ease_in_out(value: float) -> float:
    value = clamp(value)
    return value * value * (3.0 - 2.0 * value)


def fractional(value: float) -> float:
    return value - math.floor(value)


def polygon_vertices(
    cx: float, cy: float, radius: float, rotation: float
) -> list[tuple[float, float]]:
    return [
        (
            cx + math.cos(math.radians(rotation + side * 45 - 90)) * radius,
            cy + math.sin(math.radians(rotation + side * 45 - 90)) * radius,
        )
        for side in range(POLYGON_SIDES)
    ]


def point_on_polygon(
    cx: float, cy: float, radius: float, rotation: float, phase: float
) -> tuple[float, float]:
    position = fractional(phase) * POLYGON_SIDES
    side = min(POLYGON_SIDES - 1, int(position))
    local = position - side
    vertices = polygon_vertices(cx, cy, radius, rotation)
    start = vertices[side]
    end = vertices[(side + 1) % POLYGON_SIDES]
    return (
        start[0] + (end[0] - start[0]) * local,
        start[1] + (end[1] - start[1]) * local,
    )


def draw_tiny_snowflake(
    draw: ImageDraw.ImageDraw,
    x: float,
    y: float,
    radius: float,
    color: tuple[int, int, int, int],
) -> None:
    width = max(1, round(radius * 0.23))
    for arm in range(3):
        angle = math.radians(arm * 60)
        dx = math.cos(angle) * radius
        dy = math.sin(angle) * radius
        draw.line((x - dx, y - dy, x + dx, y + dy), fill=color, width=width)


def render_frame(reference: Image.Image, t: float) -> Image.Image:
    reveal = ease_out_cubic(t / 0.18)
    base = reference.copy()
    scale = 0.80 + 0.20 * reveal
    scaled_size = max(1, round(SIZE * scale))
    base = base.resize((scaled_size, scaled_size), Image.Resampling.LANCZOS)

    frame = Image.new("RGBA", (SIZE, SIZE), (255, 255, 255, 255))
    offset = ((SIZE - scaled_size) // 2, (SIZE - scaled_size) // 2)
    frame.alpha_composite(base, offset)

    overlay = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    cx = cy = SIZE / 2
    badge_radius = SIZE * 0.335 * scale
    inner_radius = badge_radius * 0.42
    orbit_radius = badge_radius * 1.25

    for index, angle in enumerate(RADIAL_ANGLES):
        local = fractional(t * RADIAL_SPEEDS[index] + RADIAL_PHASES[index])
        depth = local**3
        radians = math.radians(angle)
        distance = inner_radius * 1.12 + (badge_radius * 0.91 - inner_radius * 1.12) * depth
        x = cx + math.cos(radians) * distance
        y = cy + math.sin(radians) * distance
        radius = (
            badge_radius
            * (0.010 + 0.030 * depth)
            * RADIAL_SIZE_FACTORS[index]
        )
        particle_reveal = ease_out_cubic((t - 0.10) / 0.16)
        visibility = math.sin(math.pi * local) * particle_reveal
        tail_length = badge_radius * (0.025 + 0.15 * depth)
        for point in range(1, 6):
            fraction = point / 5
            alpha = round(145 * visibility * (1 - fraction))
            tail_x = x - math.cos(radians) * tail_length * fraction
            tail_y = y - math.sin(radians) * tail_length * fraction
            dot = max(1, round(radius * 0.18))
            draw.ellipse(
                (tail_x - dot, tail_y - dot, tail_x + dot, tail_y + dot),
                fill=(76, 199, 244, alpha),
            )
        draw_tiny_snowflake(
            draw,
            x,
            y,
            radius,
            (210, 246, 255, round(255 * visibility)),
        )

    comet_reveal = ease_out_cubic((t - 0.14) / 0.18)
    for orbit in range(3):
        polygon_x = cx + ORBIT_OFFSET_X[orbit] * badge_radius
        polygon_y = cy + ORBIT_OFFSET_Y[orbit] * badge_radius
        phase = fractional(t * ORBIT_SPEEDS[orbit] + orbit * 0.31)
        for trail in range(7, 0, -1):
            x, y = point_on_polygon(
                polygon_x,
                polygon_y,
                orbit_radius,
                ORBIT_ROTATIONS[orbit],
                phase - trail * 0.012,
            )
            alpha = round(115 * comet_reveal * (1 - trail / 8))
            dot = max(1, round(badge_radius * 0.010))
            draw.ellipse((x - dot, y - dot, x + dot, y + dot), fill=(199, 245, 255, alpha))
        x, y = point_on_polygon(
            polygon_x,
            polygon_y,
            orbit_radius,
            ORBIT_ROTATIONS[orbit],
            phase,
        )
        draw_tiny_snowflake(
            draw,
            x,
            y,
            badge_radius * 0.040,
            (255, 255, 255, round(255 * comet_reveal)),
        )

    frame.alpha_composite(overlay)
    return frame.convert("P", palette=Image.Palette.ADAPTIVE, colors=255)


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    reference = Image.open(REFERENCE).convert("RGBA").resize(
        (SIZE, SIZE), Image.Resampling.LANCZOS
    )
    frames = [
        render_frame(reference, index / (FRAME_COUNT - 1))
        for index in range(FRAME_COUNT)
    ]
    frames.extend([frames[-1].copy() for _ in range(6)])
    frames[0].save(
        OUTPUT,
        save_all=True,
        append_images=frames[1:],
        duration=round(1000 / FPS),
        loop=0,
        disposal=2,
        optimize=True,
    )


if __name__ == "__main__":
    main()

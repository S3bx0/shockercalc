"""Generate deterministic PNG assets from the approved brand reference."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
BRAND = ASSETS / "brand"
PREVIEWS = BRAND / "previews"
APPROVED = BRAND / "approved-emblem-reference.png"
FONT = ASSETS / "fonts" / "DejaVuSans.ttf"
CANVAS = 1024


def masked_preview(icon: Image.Image) -> Image.Image:
    tile = 250
    gap = 34
    labels = ("Circle", "Squircle", "Rounded", "Teardrop")
    preview = Image.new("RGB", (gap + 4 * (tile + gap), 330), "#E7EEF4")
    font = ImageFont.truetype(str(FONT), 24)
    draw = ImageDraw.Draw(preview)
    sample = icon.resize((tile, tile), Image.Resampling.LANCZOS)

    for index, label in enumerate(labels):
        mask = Image.new("L", (tile, tile), 0)
        mask_draw = ImageDraw.Draw(mask)
        if label == "Circle":
            mask_draw.ellipse((0, 0, tile - 1, tile - 1), fill=255)
        elif label == "Squircle":
            mask_draw.rounded_rectangle((0, 0, tile - 1, tile - 1), radius=72, fill=255)
        elif label == "Rounded":
            mask_draw.rounded_rectangle((0, 0, tile - 1, tile - 1), radius=42, fill=255)
        else:
            mask_draw.polygon(
                ((125, 0), (245, 74), (210, 226), (65, 249), (0, 116)),
                fill=255,
            )
        x = gap + index * (tile + gap)
        preview.paste(sample, (x, 18), mask)
        box = draw.textbbox((0, 0), label, font=font)
        draw.text(
            (x + (tile - (box[2] - box[0])) / 2, 282),
            label,
            font=font,
            fill="#17334D",
        )
    return preview


def size_preview(icon: Image.Image) -> Image.Image:
    sizes = (512, 192, 48, 32)
    preview = Image.new("RGB", (980, 590), "#E7EEF4")
    font = ImageFont.truetype(str(FONT), 22)
    draw = ImageDraw.Draw(preview)
    x = 24
    for size in sizes:
        sample = icon.resize((size, size), Image.Resampling.LANCZOS)
        preview.paste(sample.convert("RGB"), (x, 24))
        draw.text((x, 548), f"{size} px", font=font, fill="#17334D")
        x += size + 38
    return preview


def save_resized(source: Image.Image, destination: Path, size: int) -> None:
    source.resize((size, size), Image.Resampling.LANCZOS).save(
        destination,
        optimize=True,
    )


def main() -> None:
    BRAND.mkdir(parents=True, exist_ok=True)
    PREVIEWS.mkdir(parents=True, exist_ok=True)
    (ASSETS / "store").mkdir(parents=True, exist_ok=True)

    if not APPROVED.exists():
        raise FileNotFoundError(f"Approved emblem reference is missing: {APPROVED}")

    emblem = Image.open(APPROVED).convert("RGBA").resize(
        (CANVAS, CANVAS),
        Image.Resampling.LANCZOS,
    )
    outputs = (
        BRAND / "refrigeration-calc-emblem.png",
        BRAND / "refrigeration-calc-launcher.png",
        ASSETS / "icon.png",
        ASSETS / "presplash.png",
    )
    for destination in outputs:
        emblem.save(destination, optimize=True)

    save_resized(emblem, ASSETS / "icon-192.png", 192)
    save_resized(emblem, ASSETS / "icon-48.png", 48)
    save_resized(emblem, ASSETS / "store" / "play-icon-512.png", 512)
    masked_preview(emblem).save(
        PREVIEWS / "adaptive-mask-preview.png",
        optimize=True,
    )
    size_preview(emblem).save(PREVIEWS / "size-preview.png", optimize=True)


if __name__ == "__main__":
    main()

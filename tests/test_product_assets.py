"""Regression guards for mobile product assets."""
from __future__ import annotations

from PIL import Image, ImageDraw

from tools.audit_product_assets import IMAGES_DIR, _catalog_coverage

MAX_PRODUCT_IMAGES_SIZE = 9 * 1024 * 1024
MAX_SINGLE_PRODUCT_IMAGE_SIZE = 150 * 1024

EXPECTED_MISSING_MOBILE_IMAGES: set[str] = set()
EXPECTED_ORPHAN_IMAGES = {
    "Cukinia",
    "Rzepa2",
    "Seler",
    "Winogrono amerykańskie",
}
EXPECTED_HIDDEN_MOBILE_IMAGES = {
    "chleb_CTP ALDI",
    "lody_CTP ALDI",
    "mieso i kielbasa_CTP ALDI",
    "nabial_CTP ALDI",
    "pizza_CTP ALDI",
    "ryby_CTP ALDI",
    "zerowka_CTP ALDI",
}

# Zamknięte prześwity większe niż ten limit wymagają ręcznego przeglądu.
# W wiśniach tło jest celowo zamknięte pomiędzy owocami i ogonkami.
MAX_UNREVIEWED_ALPHA_HOLE_PIXELS = 1_000
EXPECTED_LARGE_ALPHA_HOLES = {
    "Wiśnie kwaśne.webp",
    "Wiśnie słodkie.webp",
}


def _enclosed_transparent_pixels(path) -> int:
    """Count fully transparent pixels that cannot reach an image edge."""
    with Image.open(path) as opened:
        alpha = opened.convert("RGBA").getchannel("A")
        transparent = alpha.point(lambda value: 255 if value <= 8 else 0)

    width, height = transparent.size
    for x in range(width):
        for y in (0, height - 1):
            if transparent.getpixel((x, y)):
                ImageDraw.floodfill(transparent, (x, y), 0)
    for y in range(height):
        for x in (0, width - 1):
            if transparent.getpixel((x, y)):
                ImageDraw.floodfill(transparent, (x, y), 0)

    return transparent.histogram()[255]


def test_mobile_product_asset_coverage_is_controlled():
    images = sorted(IMAGES_DIR.glob("*.webp"))
    coverage = _catalog_coverage(images)

    assert coverage.visible_product_count >= 200
    assert set(coverage.missing_visible_images) == EXPECTED_MISSING_MOBILE_IMAGES
    assert set(coverage.images_without_catalog_product) <= EXPECTED_ORPHAN_IMAGES
    assert set(coverage.hidden_mobile_images) == EXPECTED_HIDDEN_MOBILE_IMAGES


def test_product_image_size_budget_is_enforced():
    images = sorted(IMAGES_DIR.glob("*.webp"))

    assert sum(path.stat().st_size for path in images) < MAX_PRODUCT_IMAGES_SIZE
    for path in images:
        assert path.stat().st_size <= MAX_SINGLE_PRODUCT_IMAGE_SIZE, path.name
        with Image.open(path) as image:
            assert image.width <= 512, path.name
            assert image.height <= 512, path.name
            assert image.format == "WEBP", path.name


def test_product_images_do_not_gain_large_unreviewed_alpha_holes():
    images = sorted(IMAGES_DIR.glob("*.webp"))
    suspicious = {
        path.name
        for path in images
        if _enclosed_transparent_pixels(path)
        > MAX_UNREVIEWED_ALPHA_HOLE_PIXELS
    }

    assert suspicious == EXPECTED_LARGE_ALPHA_HOLES

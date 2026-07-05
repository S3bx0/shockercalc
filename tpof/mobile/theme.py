"""Mobile theme colors and button styling.

Pure helpers: each color function takes ``dark: bool`` (Dark vs Light theme) and
returns an RGBA tuple. No Kivy imports and no application state, so the module is
unit-testable in isolation and stays independent from ``tpof.mobile.main``.
"""
from __future__ import annotations

from tpof.mobile.constants import (
    AD_SLOT_BG_DARK,
    AD_SLOT_BG_LIGHT,
    BOTTOM_NAV_BG_DARK,
    BOTTOM_NAV_BG_LIGHT,
    CARD_BG_DARK,
    CARD_BG_LIGHT,
    FOOTER_BG_DARK,
    FOOTER_BG_LIGHT,
    SURFACE_DARK,
    SURFACE_LIGHT,
)


def card_bg(dark: bool):
    return CARD_BG_DARK if dark else CARD_BG_LIGHT


def surface_bg(dark: bool):
    return SURFACE_DARK if dark else SURFACE_LIGHT


def bottom_nav_bg(dark: bool):
    return BOTTOM_NAV_BG_DARK if dark else BOTTOM_NAV_BG_LIGHT


def footer_bg(dark: bool):
    return FOOTER_BG_DARK if dark else FOOTER_BG_LIGHT


def ad_slot_bg(dark: bool):
    return AD_SLOT_BG_DARK if dark else AD_SLOT_BG_LIGHT


def menu_bg_color(dark: bool):
    return (0.10, 0.14, 0.18, 1) if dark else (0.91, 0.96, 1.0, 1)


def menu_text_color(dark: bool):
    return (0.94, 0.97, 1.0, 1) if dark else (0.12, 0.14, 0.16, 1)


_BUTTON_PALETTES = {
    "primary": ((0.04, 0.42, 0.68, 1), (1, 1, 1, 1)),
    "ice": ((0.04, 0.56, 0.72, 1), (0.94, 1.0, 1.0, 1)),
    "dark": ((0.08, 0.12, 0.18, 1), (1.0, 0.58, 0.58, 1)),
    "muted": ((0.10, 0.18, 0.24, 1), (0.72, 0.86, 0.90, 1)),
    "pro": ((0.05, 0.48, 0.72, 1), (1, 1, 1, 1)),
}


def style_app_button(button, variant: str = "primary") -> None:
    """Apply the branded button palette to a KivyMD button in place."""
    bg, fg = _BUTTON_PALETTES.get(variant, _BUTTON_PALETTES["primary"])
    button.md_bg_color = bg
    button.theme_text_color = "Custom"
    button.text_color = fg
    try:
        button.elevation = 4
    except Exception:
        pass

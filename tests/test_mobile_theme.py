"""Behavior tests for the mobile theme color helpers."""
from __future__ import annotations

from tpof.mobile import theme
from tpof.mobile.constants import (
    AD_SLOT_BG_DARK,
    AD_SLOT_BG_LIGHT,
    CARD_BG_DARK,
    CARD_BG_LIGHT,
    SURFACE_DARK,
    SURFACE_LIGHT,
)


def test_color_helpers_switch_on_dark_flag():
    assert theme.card_bg(True) == CARD_BG_DARK
    assert theme.card_bg(False) == CARD_BG_LIGHT
    assert theme.surface_bg(True) == SURFACE_DARK
    assert theme.surface_bg(False) == SURFACE_LIGHT
    assert theme.ad_slot_bg(True) == AD_SLOT_BG_DARK
    assert theme.ad_slot_bg(False) == AD_SLOT_BG_LIGHT


def test_menu_colors_differ_between_themes():
    assert theme.menu_bg_color(True) != theme.menu_bg_color(False)
    assert theme.menu_text_color(True) != theme.menu_text_color(False)


def test_style_app_button_applies_pro_palette():
    class FakeButton:
        pass

    button = FakeButton()
    theme.style_app_button(button, "pro")
    assert button.md_bg_color == (0.05, 0.48, 0.72, 1)
    assert button.text_color == (1, 1, 1, 1)
    assert button.theme_text_color == "Custom"
    assert button.elevation == 4


def test_style_app_button_unknown_variant_falls_back_to_primary():
    class FakeButton:
        pass

    button = FakeButton()
    theme.style_app_button(button, "nonexistent")
    assert button.md_bg_color == (0.04, 0.42, 0.68, 1)

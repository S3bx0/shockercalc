"""Behavior tests for the mobile theme color helpers."""
from __future__ import annotations

from tpof.mobile import theme
from tpof.mobile.constants import (
    AD_SLOT_BG_DARK,
    AD_SLOT_BG_LIGHT,
    BOTTOM_NAV_BG_DARK,
    BRAND_ICE,
    CARD_BG_DARK,
    CARD_BG_LIGHT,
    FOOTER_BG_DARK,
    SURFACE_DARK,
    SURFACE_LIGHT,
)
from tpof.mobile.theme import ThemeSyncController, ThemeSyncView


class _Surface:
    md_bg_color = None


class _Color:
    rgba = None


class _Frost:
    def __init__(self):
        self.dark = None

    def set_dark(self, dark):
        self.dark = dark


class _Tab:
    def __init__(self):
        self.light = None
        self.active = None

    def set_theme_light(self, light):
        self.light = light

    def set_active(self, active):
        self.active = active


class _Button:
    icon = ""
    text = "label"
    theme_text_color = None
    text_color = None


class _Chip:
    active = True


def _controller_state(*, dark=True, active_tab="valves"):
    theme_state = {"dark": dark}
    window_colors = []
    tab_theme_calls = []
    closed = []
    scheduled = []
    cards = [_Surface(), _Surface()]
    tabs = {
        "freezing": _Tab(),
        "valves": _Tab(),
        "labor": _Tab(),
    }
    view = ThemeSyncView(
        set_window_clearcolor=window_colors.append,
        root_bg_color=_Color(),
        root_layout=_Surface(),
        frost_background=_Frost(),
        tab_frost_background=_Frost(),
        bottom_nav=_Surface(),
        nav_tabs=tabs,
        ad_slot=_Surface(),
        footer_bar=_Surface(),
        footer_label=_Button(),
        pro_button=_Button(),
        toolbar_title=_Button(),
        toolbar_snowflake=_Button(),
        hints_chip=_Chip(),
        hints_button=_Button(),
        language_button=_Button(),
        theme_button=_Button(),
        privacy_button=_Button(),
    )

    def set_dark(value):
        theme_state["dark"] = value

    controller = ThemeSyncController(
        is_dark=lambda: theme_state["dark"],
        set_dark=set_dark,
        get_active_tab=lambda: active_tab,
        get_themed_cards=lambda: cards,
        apply_tab_themes=(
            lambda: tab_theme_calls.append("freezing"),
            lambda: tab_theme_calls.append("labor"),
            lambda: tab_theme_calls.append("valves"),
        ),
        close_product_dialog=lambda: closed.append(True),
        schedule_once=lambda callback, delay: scheduled.append((callback, delay)),
    )
    return {
        "controller": controller,
        "theme_state": theme_state,
        "view": view,
        "tabs": tabs,
        "cards": cards,
        "window_colors": window_colors,
        "tab_theme_calls": tab_theme_calls,
        "closed": closed,
        "scheduled": scheduled,
    }


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


def test_style_app_button_applies_muted_palette_for_inactive_actions():
    class FakeButton:
        pass

    button = FakeButton()
    theme.style_app_button(button, "muted")
    assert button.md_bg_color == (0.10, 0.18, 0.24, 1)
    assert button.text_color == (0.72, 0.86, 0.90, 1)
    assert button.theme_text_color == "Custom"


def test_button_palettes_meet_wcag_normal_text_contrast():
    for variant, (background, foreground) in theme._BUTTON_PALETTES.items():
        assert theme.contrast_ratio(foreground, background) >= 4.5, variant


def test_result_colors_meet_wcag_contrast_in_both_themes():
    assert theme.contrast_ratio(theme.result_text_color(True), CARD_BG_DARK) >= 4.5
    assert theme.contrast_ratio(theme.result_text_color(False), CARD_BG_LIGHT) >= 4.5


def test_theme_controller_requires_attached_shell_view():
    state = _controller_state()

    assert state["controller"].is_attached is False
    assert state["controller"].apply() is False
    assert state["tab_theme_calls"] == []


def test_theme_controller_applies_dark_surfaces_tabs_and_cards():
    state = _controller_state(dark=True, active_tab="valves")
    controller = state["controller"]
    view = state["view"]
    controller.attach(view)

    assert controller.apply() is True

    assert controller.is_attached is True
    assert state["window_colors"] == [SURFACE_DARK]
    assert view.root_bg_color.rgba == SURFACE_DARK
    assert view.root_layout.md_bg_color == (0, 0, 0, 0)
    assert view.frost_background.dark is True
    assert view.tab_frost_background.dark is True
    assert view.bottom_nav.md_bg_color == BOTTOM_NAV_BG_DARK
    assert state["tabs"]["freezing"].active is False
    assert state["tabs"]["valves"].active is True
    assert all(tab.light is False for tab in state["tabs"].values())
    assert all(card.md_bg_color == CARD_BG_DARK for card in state["cards"])
    assert state["tab_theme_calls"] == ["freezing", "labor", "valves"]
    assert view.ad_slot.md_bg_color == AD_SLOT_BG_DARK
    assert view.footer_bar.md_bg_color == FOOTER_BG_DARK
    assert view.toolbar_title.text_color == (1, 1, 1, 1)
    assert view.toolbar_snowflake.text_color == BRAND_ICE
    assert view.hints_button.text_color == BRAND_ICE
    assert view.language_button.text_color == (0.93, 0.98, 1.0, 0.94)
    assert view.privacy_button.text_color == (0.93, 0.98, 1.0, 0.94)
    assert view.footer_label.text_color == (0.72, 0.78, 0.82, 1)
    assert view.pro_button.md_bg_color == (0.05, 0.48, 0.72, 1)
    assert view.theme_button.icon == "weather-night"


def test_theme_controller_toggle_switches_to_light_and_schedules_refresh():
    state = _controller_state(dark=True)
    controller = state["controller"]
    view = state["view"]
    controller.attach(view)

    assert controller.toggle() is False

    assert state["theme_state"]["dark"] is False
    assert state["closed"] == [True]
    assert state["window_colors"] == [SURFACE_LIGHT]
    assert view.root_bg_color.rgba == SURFACE_LIGHT
    assert view.theme_button.icon == "weather-sunny"
    assert len(state["scheduled"]) == 2
    immediate_callback, immediate_delay = state["scheduled"][0]
    refresh_callback, refresh_delay = state["scheduled"][1]
    assert immediate_delay == 0
    assert refresh_delay == 0.2
    immediate_callback()
    refresh_callback()
    assert state["window_colors"] == [
        SURFACE_LIGHT,
        SURFACE_LIGHT,
        SURFACE_LIGHT,
    ]
    assert view.toolbar_title.text == "label"
    assert view.pro_button.text == "label"

"""Mobile theme colors and button styling.

Pure helpers: each color function takes ``dark: bool`` (Dark vs Light theme) and
returns an RGBA tuple. No Kivy imports and no application state, so the module is
unit-testable in isolation and stays independent from ``tpof.mobile.main``.
"""
from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any

from tpof.mobile.constants import (
    AD_SLOT_BG_DARK,
    AD_SLOT_BG_LIGHT,
    BOTTOM_NAV_BG_DARK,
    BOTTOM_NAV_BG_LIGHT,
    BRAND_ICE,
    CARD_BG_DARK,
    CARD_BG_LIGHT,
    FOOTER_BG_DARK,
    FOOTER_BG_LIGHT,
    SURFACE_DARK,
    SURFACE_LIGHT,
)

_TOOLBAR_TEXT_COLOR = (0.93, 0.98, 1.0, 0.94)


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


def result_text_color(dark: bool):
    """High-contrast green for result totals on dark and light cards."""

    return (0.24, 0.86, 0.64, 1) if dark else (0.0, 0.34, 0.20, 1)


def relative_luminance(color: tuple[float, ...]) -> float:
    """Return WCAG relative luminance for an RGB/RGBA color."""

    def linear(channel: float) -> float:
        return channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4

    red, green, blue = color[:3]
    return 0.2126 * linear(red) + 0.7152 * linear(green) + 0.0722 * linear(blue)


def contrast_ratio(foreground: tuple[float, ...], background: tuple[float, ...]) -> float:
    """Return the WCAG contrast ratio between two opaque colors."""

    lighter, darker = sorted(
        (relative_luminance(foreground), relative_luminance(background)),
        reverse=True,
    )
    return (lighter + 0.05) / (darker + 0.05)


_BUTTON_PALETTES = {
    "primary": ((0.04, 0.42, 0.68, 1), (1, 1, 1, 1)),
    "ice": ((0.03, 0.42, 0.56, 1), (0.94, 1.0, 1.0, 1)),
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


@dataclass(frozen=True)
class ThemeSyncView:
    """Widgets whose colors and active state follow the application theme."""

    set_window_clearcolor: Callable[[Any], None]
    root_bg_color: Any
    root_layout: Any
    frost_background: Any
    tab_frost_background: Any
    bottom_nav: Any
    nav_tabs: dict[str, Any]
    ad_slot: Any
    footer_bar: Any
    footer_label: Any
    pro_button: Any
    toolbar_title: Any
    toolbar_snowflake: Any
    hints_chip: Any
    hints_button: Any
    language_button: Any
    theme_button: Any
    privacy_button: Any

    @classmethod
    def from_shell(
        cls,
        shell: Any,
        *,
        set_window_clearcolor: Callable[[Any], None],
    ) -> ThemeSyncView:
        """Capture the theme-aware widgets exposed by the built app shell."""

        return cls(
            set_window_clearcolor=set_window_clearcolor,
            root_bg_color=shell._root_bg_color,
            root_layout=shell.root_layout,
            frost_background=shell.frost_background,
            tab_frost_background=shell.tab_frost_background,
            bottom_nav=shell.bottom_nav,
            nav_tabs={
                "freezing": shell.bottom_freezing_tab,
                "valves": shell.bottom_valves_tab,
                "labor": shell.bottom_labor_tab,
            },
            ad_slot=shell.ad_slot,
            footer_bar=shell.footer_bar,
            footer_label=shell.footer_label,
            pro_button=shell.btn_pro,
            toolbar_title=shell.lbl_toolbar_title,
            toolbar_snowflake=shell.toolbar_snowflake,
            hints_chip=shell.btn_hints_chip,
            hints_button=shell.btn_hints,
            language_button=shell.btn_lang,
            theme_button=shell.btn_theme,
            privacy_button=shell.btn_privacy,
        )


class ThemeSyncController:
    """Coordinates theme colors without owning the Kivy application shell."""

    def __init__(
        self,
        *,
        is_dark: Callable[[], bool],
        set_dark: Callable[[bool], None],
        get_active_tab: Callable[[], str],
        get_themed_cards: Callable[[], Iterable[Any]],
        apply_tab_themes: tuple[Callable[[], None], ...],
        close_product_dialog: Callable[[], None],
        schedule_once: Callable[[Callable[..., Any], float], Any],
    ) -> None:
        self._is_dark = is_dark
        self._set_dark = set_dark
        self._get_active_tab = get_active_tab
        self._get_themed_cards = get_themed_cards
        self._apply_tab_themes = apply_tab_themes
        self._close_product_dialog = close_product_dialog
        self._schedule_once = schedule_once
        self._view: ThemeSyncView | None = None

    @property
    def is_attached(self) -> bool:
        return self._view is not None

    def attach(self, view: ThemeSyncView) -> None:
        self._view = view

    def card_bg(self):
        return card_bg(self._is_dark())

    def surface_bg(self):
        return surface_bg(self._is_dark())

    def bottom_nav_bg(self):
        return bottom_nav_bg(self._is_dark())

    def footer_bg(self):
        return footer_bg(self._is_dark())

    def ad_slot_bg(self):
        return ad_slot_bg(self._is_dark())

    def menu_bg_color(self):
        return menu_bg_color(self._is_dark())

    def menu_text_color(self):
        return menu_text_color(self._is_dark())

    def result_text_color(self):
        return result_text_color(self._is_dark())

    def style_button(self, button: Any, variant: str = "primary") -> None:
        style_app_button(button, variant)

    @staticmethod
    def _set_custom_color(widget: Any, color: Any) -> None:
        widget.theme_text_color = "Custom"
        widget.text_color = color

    @staticmethod
    def _redispatch(widget: Any, property_name: str) -> None:
        """Force Kivy to rebuild icon/text textures after a theme transition."""

        try:
            widget.property(property_name).dispatch(widget)
        except Exception:
            value = getattr(widget, property_name, "")
            setattr(widget, property_name, "")
            setattr(widget, property_name, value)

    def _refresh_shell_content(self) -> bool:
        view = self._view
        if view is None:
            return False
        self.apply()
        for widget, property_name in (
            (view.toolbar_title, "text"),
            (view.toolbar_snowflake, "icon"),
            (view.hints_button, "icon"),
            (view.language_button, "icon"),
            (view.theme_button, "icon"),
            (view.privacy_button, "icon"),
            (view.footer_label, "text"),
            (view.pro_button, "text"),
        ):
            self._redispatch(widget, property_name)
        return True

    def apply(self) -> bool:
        """Apply the current theme to every attached shell surface."""

        view = self._view
        if view is None:
            return False

        dark = self._is_dark()
        surface = surface_bg(dark)
        view.set_window_clearcolor(surface)
        view.root_bg_color.rgba = surface
        view.root_layout.md_bg_color = (0, 0, 0, 0)
        view.frost_background.set_dark(dark)
        view.tab_frost_background.set_dark(dark)
        view.bottom_nav.md_bg_color = bottom_nav_bg(dark)

        active_tab = self._get_active_tab()
        for name, tab in view.nav_tabs.items():
            tab.set_theme_light(not dark)
            tab.set_active(active_tab == name)

        for card in self._get_themed_cards():
            card.md_bg_color = card_bg(dark)
        for apply_theme in self._apply_tab_themes:
            apply_theme()

        view.ad_slot.md_bg_color = ad_slot_bg(dark)
        view.footer_bar.md_bg_color = footer_bg(dark)
        self._set_custom_color(view.toolbar_title, (1, 1, 1, 1))
        self._set_custom_color(view.toolbar_snowflake, BRAND_ICE)
        self._set_custom_color(
            view.hints_button,
            BRAND_ICE if getattr(view.hints_chip, "active", False)
            else _TOOLBAR_TEXT_COLOR,
        )
        for button in (
            view.language_button,
            view.theme_button,
            view.privacy_button,
        ):
            self._set_custom_color(button, _TOOLBAR_TEXT_COLOR)
        self._set_custom_color(
            view.footer_label,
            (0.72, 0.78, 0.82, 1) if dark else (0.34, 0.44, 0.48, 1),
        )
        style_app_button(view.pro_button, "pro")
        view.theme_button.icon = "weather-night" if dark else "weather-sunny"
        return True

    def toggle(self) -> bool:
        """Toggle Dark/Light and immediately refresh all attached surfaces."""

        self._close_product_dialog()
        dark = not self._is_dark()
        self._set_dark(dark)
        self.apply()
        self._schedule_once(lambda *_args: self.apply(), 0)
        self._schedule_once(lambda *_args: self._refresh_shell_content(), 0.2)
        return dark

"""Framework-independent builder for the persistent mobile application chrome."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, fields
from typing import Any

from tpof.mobile.constants import BRAND_ICE


@dataclass(frozen=True)
class MobileShellFactories:
    """Widget factories supplied by the Kivy composition root."""

    box_layout: Callable[..., Any]
    icon: Callable[..., Any]
    icon_button: Callable[..., Any]
    label: Callable[..., Any]
    raised_button: Callable[..., Any]
    brand_toolbar: Callable[..., Any]
    frost_chip: Callable[..., Any]
    bottom_nav_tab: Callable[..., Any]
    center_notice: Callable[..., Any]


@dataclass(frozen=True)
class MobileShellCallbacks:
    """Application state and actions consumed by the shell widgets."""

    translate: Callable[[str], str]
    hints_enabled: Callable[[], bool]
    on_toggle_hints: Callable[[], None]
    on_toggle_language: Callable[[], None]
    on_toggle_theme: Callable[[], None]
    on_open_privacy: Callable[[], None]
    on_open_settings: Callable[[], None]
    on_select_tab: Callable[[str], None]
    bottom_nav_bg: Callable[[], Any]
    footer_bg: Callable[[], Any]
    ad_slot_bg: Callable[[], Any]
    footer_text: Callable[[], str]
    pro_button_text: Callable[[], str]
    on_buy_pro: Callable[[], None]
    ad_label_text: Callable[[], str]


@dataclass(frozen=True)
class MobileShellView:
    """Persistent widget references shared with application controllers."""

    toolbar: Any
    toolbar_brand_chip: Any
    toolbar_snowflake: Any
    lbl_toolbar_title: Any
    btn_hints_chip: Any
    btn_hints: Any
    btn_lang_chip: Any
    btn_lang: Any
    btn_theme_chip: Any
    btn_theme: Any
    btn_privacy_chip: Any
    btn_privacy: Any
    bottom_nav: Any
    bottom_freezing_tab: Any
    bottom_valves_tab: Any
    bottom_labor_tab: Any
    footer_bar: Any
    footer_label: Any
    btn_pro: Any
    ad_slot: Any
    ad_label: Any
    center_notice: Any

    def install_on(self, shell: Any) -> None:
        """Expose the view through the legacy app attributes during migration."""

        for field in fields(self):
            setattr(shell, field.name, getattr(self, field.name))


class MobileShellBuilder:
    """Builds the toolbar, navigation, footer, ad slot, and central notice."""

    def __init__(
        self,
        *,
        dp: Callable[[float], float],
        factories: MobileShellFactories,
        callbacks: MobileShellCallbacks,
    ) -> None:
        self._dp = dp
        self._factories = factories
        self._callbacks = callbacks

    def _toolbar_chip_button(
        self,
        *,
        icon: str,
        icon_size: str,
        on_release: Callable[[], None],
        active: bool = False,
        size_dp: int = 48,
    ) -> tuple[Any, Any]:
        dp = self._dp
        chip = self._factories.frost_chip(
            active=active,
            size_hint_x=None,
            size_hint_y=None,
            width=dp(size_dp),
            height=dp(size_dp),
        )
        button = self._factories.icon_button(
            icon=icon,
            size_hint=(1, 1),
            width=dp(size_dp),
            icon_size=icon_size,
            theme_text_color="Custom",
            text_color=BRAND_ICE if active else (0.93, 0.98, 1.0, 0.94),
            on_release=lambda *_args: on_release(),
        )
        chip.add_widget(button)
        return chip, button

    def _build_toolbar(self) -> dict[str, Any]:
        dp = self._dp
        factories = self._factories
        callbacks = self._callbacks
        toolbar = factories.brand_toolbar(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(72),
            padding=[dp(14), 0, dp(8), 0],
            spacing=dp(5),
        )
        toolbar_brand_chip = factories.frost_chip(
            active=True,
            size_hint_x=None,
            size_hint_y=None,
            width=dp(48),
            height=dp(48),
        )
        toolbar_snowflake = factories.icon_button(
            icon="snowflake",
            size_hint=(1, 1),
            width=dp(48),
            icon_size="28sp",
            theme_text_color="Custom",
            text_color=BRAND_ICE,
            on_release=lambda *_args: callbacks.on_open_settings(),
        )
        toolbar_brand_chip.add_widget(toolbar_snowflake)
        toolbar.add_widget(toolbar_brand_chip)
        toolbar_title = factories.label(
            text="Refrigeration\nCalc",
            halign="center",
            valign="middle",
            font_style="Subtitle1",
            font_size="16sp",
            line_height=0.88,
            shorten=False,
            theme_text_color="Custom",
            text_color=(1, 1, 1, 1),
        )
        toolbar.add_widget(toolbar_title)

        hints_enabled = callbacks.hints_enabled()
        hints_chip, hints_button = self._toolbar_chip_button(
            icon=(
                "lightbulb-on-outline"
                if hints_enabled
                else "lightbulb-off-outline"
            ),
            icon_size="26sp",
            active=hints_enabled,
            on_release=callbacks.on_toggle_hints,
        )
        lang_chip, lang_button = self._toolbar_chip_button(
            icon="translate",
            icon_size="28sp",
            on_release=callbacks.on_toggle_language,
        )
        theme_chip, theme_button = self._toolbar_chip_button(
            icon="weather-night",
            icon_size="28sp",
            on_release=callbacks.on_toggle_theme,
        )
        privacy_chip, privacy_button = self._toolbar_chip_button(
            icon="shield-account",
            icon_size="26sp",
            on_release=callbacks.on_open_privacy,
        )
        for chip in (hints_chip, lang_chip, theme_chip, privacy_chip):
            toolbar.add_widget(chip)

        return {
            "toolbar": toolbar,
            "toolbar_brand_chip": toolbar_brand_chip,
            "toolbar_snowflake": toolbar_snowflake,
            "lbl_toolbar_title": toolbar_title,
            "btn_hints_chip": hints_chip,
            "btn_hints": hints_button,
            "btn_lang_chip": lang_chip,
            "btn_lang": lang_button,
            "btn_theme_chip": theme_chip,
            "btn_theme": theme_button,
            "btn_privacy_chip": privacy_chip,
            "btn_privacy": privacy_button,
        }

    def _build_bottom_nav(self) -> dict[str, Any]:
        dp = self._dp
        factories = self._factories
        callbacks = self._callbacks
        bottom_nav = factories.box_layout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(70),
            padding=[dp(16), dp(3), dp(16), dp(3)],
            spacing=dp(8),
            md_bg_color=callbacks.bottom_nav_bg(),
        )
        tabs = {
            "bottom_freezing_tab": factories.bottom_nav_tab(
                name="freezing",
                text=callbacks.translate("nav_freezing"),
                mode="snowflake",
                on_select=callbacks.on_select_tab,
            ),
            "bottom_valves_tab": factories.bottom_nav_tab(
                name="valves",
                text=callbacks.translate("nav_valves"),
                mode="valve",
                on_select=callbacks.on_select_tab,
            ),
            "bottom_labor_tab": factories.bottom_nav_tab(
                name="labor",
                text=callbacks.translate("nav_labor"),
                mode="calculator",
                on_select=callbacks.on_select_tab,
            ),
        }
        for tab in tabs.values():
            bottom_nav.add_widget(tab)
        return {"bottom_nav": bottom_nav, **tabs}

    def _build_footer(self) -> dict[str, Any]:
        dp = self._dp
        factories = self._factories
        callbacks = self._callbacks
        footer_bar = factories.box_layout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(56),
            padding=[dp(12), dp(4), dp(12), dp(4)],
            spacing=dp(8),
            md_bg_color=callbacks.footer_bg(),
        )
        footer_label = factories.label(
            text=callbacks.footer_text(),
            halign="center",
            valign="middle",
            theme_text_color="Hint",
            font_style="Caption",
        )
        pro_button = factories.raised_button(
            text=callbacks.pro_button_text(),
            size_hint_x=None,
            width=dp(128),
            size_hint_y=None,
            height=dp(48),
            font_size="11sp",
            pos_hint={"center_y": 0.5},
            on_release=lambda *_args: callbacks.on_buy_pro(),
        )
        footer_bar.add_widget(pro_button)
        footer_bar.add_widget(footer_label)
        return {
            "footer_bar": footer_bar,
            "footer_label": footer_label,
            "btn_pro": pro_button,
        }

    def _build_ad_slot(self) -> dict[str, Any]:
        dp = self._dp
        factories = self._factories
        callbacks = self._callbacks
        ad_slot = factories.box_layout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(96),
            padding=[dp(16), dp(6), dp(16), dp(6)],
            spacing=dp(8),
            md_bg_color=callbacks.ad_slot_bg(),
        )
        ad_slot.add_widget(
            factories.icon(
                icon="bullhorn",
                size_hint_x=None,
                width=dp(28),
                halign="center",
                theme_text_color="Hint",
            )
        )
        ad_label = factories.label(
            text=callbacks.ad_label_text(),
            halign="center",
            font_style="Caption",
            theme_text_color="Hint",
        )
        ad_slot.add_widget(ad_label)
        return {"ad_slot": ad_slot, "ad_label": ad_label}

    def build(self) -> MobileShellView:
        toolbar = self._build_toolbar()
        bottom_nav = self._build_bottom_nav()
        footer = self._build_footer()
        ad_slot = self._build_ad_slot()
        return MobileShellView(
            **toolbar,
            **bottom_nav,
            **footer,
            **ad_slot,
            center_notice=self._factories.center_notice(),
        )

"""Responsive layout metrics for the mobile UI.

Pure computation: compute_metrics takes the Kivy dp callable plus screen
dimensions and UI flags and returns the metrics dict. No Kivy imports and no
application state, so it is unit-testable with dp=lambda value: value and
stays decoupled from the Kivy application module.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from math import sqrt
from typing import Any


def clamp(value: float, min_value: float, max_value: float) -> float:
    return max(min_value, min(max_value, value))


def compute_metrics(
    dp: Callable[[float], float],
    width_dp: float,
    height_dp: float,
    *,
    hints_enabled: bool,
    native_ad_height_dp: float = 0,
    font_scale: float = 1.0,
) -> dict:
    narrow = width_dp < 360
    compact = width_dp < 400
    short = height_dp < 720
    landscape = width_dp > height_dp
    font_scale = clamp(float(font_scale), 1.0, 2.0)
    large_text = font_scale >= 1.5
    content_height_scale = font_scale
    chrome_height_scale = 1.0 + (font_scale - 1.0) * 0.15

    def content_h(value: float, minimum: float = 0) -> float:
        return max(minimum, round(value * content_height_scale, 2))

    def chrome_h(value: float, minimum: float = 0) -> float:
        return max(minimum, round(value * chrome_height_scale, 2))

    def fixed_visual_sp(value: float) -> float:
        """Counter Android's font scale for icon glyphs that are not text."""

        return round(value / font_scale, 2)

    def chrome_sp(value: float) -> float:
        """Scale compact chrome text without letting it double in size."""

        return round(value / sqrt(font_scale), 2)

    text_scale = clamp(width_dp / 412.0, 0.88, 1.06)
    product_horizontal = width_dp >= 370 and not large_text
    product_hint_h = content_h(36 if large_text else 30) if hints_enabled else 0

    card_pad = 10 if narrow else 12 if compact else 14
    card_pad_x = card_pad
    card_pad_top = card_pad + (8 if compact else 10)
    card_pad_bottom = card_pad + (5 if compact else 6)
    content_pad = 10 if narrow else 14 if compact else 16
    stage_row_h = content_h(66 if compact or short else 74)
    action_vertical = large_text
    action_button_h = content_h(48, 48)
    action_h = (
        (action_button_h * 3) + 32
        if action_vertical
        else content_h(64 if compact else 68)
    )
    title_h = content_h(42 if compact else 46)
    total_h = content_h(44 if compact else 50)
    result_space = 8 if compact or short else 10
    field_h = content_h(54 if compact or short else 60, 48)
    card_spacing = 10 if compact else 12
    native_ad_h = native_ad_height_dp
    reserved_ad_h = max(
        56 if landscape else 64 if compact else 70,
        native_ad_h + (4 if landscape else 8) if native_ad_h else 0,
    )
    result_h = (
        card_pad_top
        + card_pad_bottom
        + title_h
        + action_h
        + total_h
        + (stage_row_h * 3)
        + (result_space * 5)
    )
    params_h = (
        card_pad_top
        + card_pad_bottom
        + title_h
        + (field_h + 8)
        + (field_h * 3)
        + (card_spacing * 4)
    )

    if product_horizontal:
        product_body_h = content_h(180 if compact else 202)
        product_card_h = (
            product_body_h + title_h + product_hint_h
            + card_pad_top + card_pad_bottom + 12
        )
        product_controls_h = product_body_h
        product_image_h = product_body_h
    else:
        product_controls_h = content_h(130)
        product_image_h = content_h(162)
        product_body_h = product_controls_h + product_image_h + 12
        product_card_h = (
            product_body_h + title_h + product_hint_h
            + card_pad_top + card_pad_bottom + 12
        )

    return {
        "width_dp": width_dp,
        "height_dp": height_dp,
        "narrow": narrow,
        "compact": compact,
        "short": short,
        "landscape": landscape,
        "font_scale": font_scale,
        "large_text": large_text,
        "text_scale": text_scale,
        "product_horizontal": product_horizontal,
        "action_vertical": action_vertical,
        "toolbar_title_visible": not large_text,
        "footer_visible": not landscape,
        "footer_label_visible": not large_text,
        "content_pad": dp(content_pad),
        "content_top": dp(12 if landscape else 18 if compact else 20),
        "content_bottom": dp(18 if landscape else 26 if compact else 30),
        "content_spacing": dp(10 if landscape else 14 if compact or short else 16),
        "card_pad": dp(card_pad),
        "card_pad_x": dp(card_pad_x),
        "card_pad_top": dp(card_pad_top),
        "card_pad_bottom": dp(card_pad_bottom),
        "card_spacing": dp(card_spacing),
        "toolbar_h": dp(
            56
            if landscape
            else chrome_h(62 if narrow else 66 if compact else 72, 56)
        ),
        "toolbar_icon_w": dp(38 if narrow else 42 if compact else 44),
        "toolbar_btn_w": dp(48),
        "toolbar_icon_sp": fixed_visual_sp(24 if narrow else 26 if compact else 28),
        "toolbar_btn_sp": fixed_visual_sp(23 if narrow else 24 if compact else 26),
        "toolbar_title_sp": chrome_sp(
            int(14 * text_scale)
            if narrow
            else int(15 * text_scale)
            if compact
            else 16
        ),
        "bottom_nav_h": dp(
            64
            if landscape
            else max(64, chrome_h(64 if compact else 70, 64))
        ),
        "bottom_tab_icon": dp(52 if compact else 56),
        "bottom_tab_sp": chrome_sp(11 if compact else 12),
        "title_h": dp(title_h),
        "title_sp": int(20 * text_scale),
        "body_sp": int(15 * text_scale),
        "caption_sp": int(12 * text_scale),
        "control_sp": chrome_sp(int(15 * text_scale)),
        "button_h": dp(content_h(48 if compact else 52, 48)),
        "button_sp": chrome_sp(int(14 * text_scale)),
        "field_h": dp(field_h),
        "params_h": dp(params_h),
        "product_card_h": dp(product_card_h),
        "product_body_h": dp(product_body_h),
        "product_controls_h": dp(product_controls_h),
        "product_image_h": dp(product_image_h),
        "product_hint_h": dp(product_hint_h),
        "product_body_spacing": dp(12 if compact else 14),
        "placeholder_top": dp(content_h(32 if compact else 44)),
        "placeholder_bottom": dp(content_h(20 if compact else 28)),
        "placeholder_icon_sp": fixed_visual_sp(36 if compact else 42),
        "action_h": dp(action_h),
        "action_button_h": dp(action_button_h),
        "action_sp": chrome_sp(
            int(13 * text_scale) if compact else int(14 * text_scale)
        ),
        "results_h": dp(result_h),
        "results_spacing": dp(result_space),
        "total_h": dp(total_h),
        "total_sp": int(20 * text_scale),
        "stage_row_h": dp(stage_row_h),
        "stage_head_h": dp(content_h(38 if compact else 42, 38)),
        "stage_icon_w": dp(34 if compact else 38),
        "stage_icon_sp": fixed_visual_sp(22 if compact else 24),
        "unit_w": dp(content_h(64 if compact else 72, 64)),
        "unit_h": dp(content_h(48, 48)),
        "footer_h": dp(0 if landscape else chrome_h(56, 56)),
        "footer_sp": chrome_sp(int(11 * text_scale)),
        "pro_sp": chrome_sp(int(12 * text_scale)),
        "ad_sp": chrome_sp(int(12 * text_scale)),
        "pro_w": dp(148 if large_text else 116 if compact else 128),
        "pro_h": dp(48),
        "ad_h": dp(reserved_ad_h),
    }


@dataclass(frozen=True)
class ResponsiveLayoutView:
    """Widgets resized by the responsive shell controller."""

    root_host: Any
    root_bg_rect: Any
    toolbar: Any
    toolbar_brand_chip: Any
    toolbar_snowflake: Any
    toolbar_title: Any
    action_chips: tuple[Any, ...]
    action_buttons: tuple[Any, ...]
    tab_content_host: Any
    bottom_nav: Any
    bottom_tabs: tuple[Any, ...]
    footer_bar: Any
    footer_label: Any
    pro_button: Any
    ad_slot: Any
    ad_label: Any

    @classmethod
    def from_shell(cls, shell: Any) -> ResponsiveLayoutView:
        """Capture the responsive widgets exposed by the built app shell."""

        return cls(
            root_host=shell.root_host,
            root_bg_rect=shell._root_bg_rect,
            toolbar=shell.toolbar,
            toolbar_brand_chip=shell.toolbar_brand_chip,
            toolbar_snowflake=shell.toolbar_snowflake,
            toolbar_title=shell.lbl_toolbar_title,
            action_chips=(
                shell.btn_hints_chip,
                shell.btn_lang_chip,
                shell.btn_theme_chip,
                shell.btn_privacy_chip,
            ),
            action_buttons=(
                shell.btn_hints,
                shell.btn_lang,
                shell.btn_theme,
                shell.btn_privacy,
            ),
            tab_content_host=shell.tab_content_host,
            bottom_nav=shell.bottom_nav,
            bottom_tabs=(
                shell.bottom_freezing_tab,
                shell.bottom_valves_tab,
                shell.bottom_labor_tab,
            ),
            footer_bar=shell.footer_bar,
            footer_label=shell.footer_label,
            pro_button=shell.btn_pro,
            ad_slot=shell.ad_slot,
            ad_label=shell.ad_label,
        )


class ResponsiveLayoutController:
    """Computes metrics and applies them to the built mobile shell."""

    def __init__(
        self,
        *,
        dp: Callable[[float], float],
        get_screen_size: Callable[[], tuple[float, float]],
        hints_enabled: Callable[[], bool],
        native_ad_height_dp: Callable[[], float],
        pro_no_ads: Callable[[], bool],
        bottom_nav_bg: Callable[[], Any],
        refresh_privacy_button: Callable[[], None],
        apply_freezing_layout: Callable[[dict[str, Any]], None],
        font_scale: Callable[[], float] = lambda: 1.0,
    ) -> None:
        self._dp = dp
        self._get_screen_size = get_screen_size
        self._hints_enabled = hints_enabled
        self._native_ad_height_dp = native_ad_height_dp
        self._pro_no_ads = pro_no_ads
        self._bottom_nav_bg = bottom_nav_bg
        self._refresh_privacy_button = refresh_privacy_button
        self._apply_freezing_layout = apply_freezing_layout
        self._font_scale = font_scale
        self._view: ResponsiveLayoutView | None = None

    @property
    def is_attached(self) -> bool:
        return self._view is not None

    def attach(self, view: ResponsiveLayoutView) -> None:
        self._view = view

    def screen_dp(self) -> tuple[float, float]:
        width, height = self._get_screen_size()
        unit = max(float(self._dp(1)), 1.0)
        return width / unit, height / unit

    def metrics(self) -> dict[str, Any]:
        width_dp, height_dp = self.screen_dp()
        return compute_metrics(
            self._dp,
            width_dp,
            height_dp,
            hints_enabled=self._hints_enabled(),
            native_ad_height_dp=self._native_ad_height_dp(),
            font_scale=self._font_scale(),
        )

    def sync_root_background(self, *_args: object) -> bool:
        view = self._view
        if view is None:
            return False
        view.root_bg_rect.pos = view.root_host.pos
        view.root_bg_rect.size = view.root_host.size
        return True

    def apply(self, *_args: object) -> bool:
        view = self._view
        if view is None:
            return False

        dp = self._dp
        metrics = self.metrics()
        view.toolbar.height = metrics["toolbar_h"]
        view.toolbar.padding = [
            metrics["content_pad"],
            0,
            dp(6 if metrics["compact"] else 8),
            0,
        ]
        view.toolbar_brand_chip.width = metrics["toolbar_icon_w"]
        view.toolbar_brand_chip.height = metrics["toolbar_icon_w"]
        view.toolbar_snowflake.width = metrics["toolbar_icon_w"]
        view.toolbar_snowflake.icon_size = f'{metrics["toolbar_icon_sp"]}sp'
        view.toolbar_title.font_size = f'{metrics["toolbar_title_sp"]}sp'
        view.toolbar_title.line_height = 0.88
        view.toolbar_title.opacity = 1 if metrics["toolbar_title_visible"] else 0

        for chip in view.action_chips:
            if getattr(chip, "opacity", 1) > 0:
                chip.width = metrics["toolbar_btn_w"]
                chip.height = metrics["toolbar_btn_w"]
        for button in view.action_buttons:
            button.width = metrics["toolbar_btn_w"]
            button.icon_size = f'{metrics["toolbar_btn_sp"]}sp'
        self._refresh_privacy_button()

        view.tab_content_host.size_hint_y = 1
        view.bottom_nav.size_hint_y = None
        view.bottom_nav.height = metrics["bottom_nav_h"]
        view.bottom_nav.padding = [
            metrics["content_pad"],
            dp(3),
            metrics["content_pad"],
            dp(3),
        ]
        view.bottom_nav.spacing = dp(8 if metrics["compact"] else 10)
        view.bottom_nav.md_bg_color = self._bottom_nav_bg()
        for tab in view.bottom_tabs:
            tab.set_metrics(
                icon_size=metrics["bottom_tab_icon"],
                label_sp=metrics["bottom_tab_sp"],
            )

        self._apply_freezing_layout(metrics)
        view.footer_bar.height = metrics["footer_h"]
        view.footer_bar.opacity = 1 if metrics["footer_visible"] else 0
        view.footer_bar.disabled = not metrics["footer_visible"]
        view.footer_bar.padding = [
            metrics["content_pad"],
            dp(3),
            metrics["content_pad"],
            dp(3),
        ]
        view.footer_bar.spacing = dp(10 if metrics["compact"] else 12)
        view.footer_label.font_size = f'{metrics["footer_sp"]}sp'
        view.footer_label.shorten = True
        view.footer_label.opacity = 1 if metrics["footer_label_visible"] else 0
        view.pro_button.width = metrics["pro_w"]
        view.pro_button.height = metrics["pro_h"]
        view.pro_button.font_size = f'{metrics["pro_sp"]}sp'
        if not self._pro_no_ads():
            view.ad_slot.height = metrics["ad_h"]
            view.ad_slot.padding = [
                metrics["content_pad"],
                dp(2),
                metrics["content_pad"],
                dp(2),
            ]
        view.ad_label.font_size = f'{metrics["ad_sp"]}sp'
        return True

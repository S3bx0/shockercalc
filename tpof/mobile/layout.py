"""Responsive layout metrics for the mobile UI.

Pure computation: compute_metrics takes the Kivy dp callable plus screen
dimensions and UI flags and returns the metrics dict. No Kivy imports and no
application state, so it is unit-testable with dp=lambda value: value and
stays decoupled from the Kivy application module.
"""
from __future__ import annotations

from typing import Callable


def clamp(value: float, min_value: float, max_value: float) -> float:
    return max(min_value, min(max_value, value))


def compute_metrics(
    dp: Callable[[float], float],
    width_dp: float,
    height_dp: float,
    *,
    hints_enabled: bool,
    native_ad_height_dp: float = 0,
) -> dict:
    narrow = width_dp < 360
    compact = width_dp < 400
    short = height_dp < 720
    text_scale = clamp(width_dp / 412.0, 0.88, 1.06)
    product_horizontal = width_dp >= 370
    product_hint_h = 30 if hints_enabled else 0

    card_pad = 10 if narrow else 12 if compact else 14
    card_pad_x = card_pad
    card_pad_top = card_pad + (8 if compact else 10)
    card_pad_bottom = card_pad + (5 if compact else 6)
    content_pad = 10 if narrow else 14 if compact else 16
    stage_row_h = 66 if compact or short else 74
    action_h = 64 if compact else 68
    title_h = 42 if compact else 46
    total_h = 44 if compact else 50
    result_space = 8 if compact or short else 10
    field_h = 54 if compact or short else 60
    card_spacing = 10 if compact else 12
    native_ad_h = native_ad_height_dp
    reserved_ad_h = max(64 if compact else 70, native_ad_h + 8 if native_ad_h else 0)
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
        product_body_h = 180 if compact else 202
        product_card_h = (
            product_body_h + title_h + product_hint_h
            + card_pad_top + card_pad_bottom + 12
        )
        product_controls_h = product_body_h
        product_image_h = product_body_h
    else:
        product_controls_h = 130
        product_image_h = 162
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
        "text_scale": text_scale,
        "product_horizontal": product_horizontal,
        "content_pad": dp(content_pad),
        "content_top": dp(18 if compact else 20),
        "content_bottom": dp(26 if compact else 30),
        "content_spacing": dp(14 if compact or short else 16),
        "card_pad": dp(card_pad),
        "card_pad_x": dp(card_pad_x),
        "card_pad_top": dp(card_pad_top),
        "card_pad_bottom": dp(card_pad_bottom),
        "card_spacing": dp(card_spacing),
        "toolbar_h": dp(62 if narrow else 66 if compact else 72),
        "toolbar_icon_w": dp(38 if narrow else 42 if compact else 44),
        "toolbar_btn_w": dp(40 if narrow else 42 if compact else 44),
        "toolbar_icon_sp": 24 if narrow else 26 if compact else 28,
        "toolbar_btn_sp": 23 if narrow else 24 if compact else 26,
        "toolbar_title_sp": int(14 * text_scale) if narrow else int(15 * text_scale) if compact else 16,
        "bottom_nav_h": dp(64 if compact else 70),
        "bottom_tab_icon": dp(52 if compact else 56),
        "bottom_tab_sp": 11 if compact else 12,
        "title_h": dp(title_h),
        "title_sp": int(20 * text_scale),
        "body_sp": int(15 * text_scale),
        "caption_sp": int(12 * text_scale),
        "button_h": dp(46 if compact else 52),
        "button_sp": int(14 * text_scale),
        "field_h": dp(field_h),
        "params_h": dp(params_h),
        "product_card_h": dp(product_card_h),
        "product_body_h": dp(product_body_h),
        "product_controls_h": dp(product_controls_h),
        "product_image_h": dp(product_image_h),
        "product_hint_h": dp(product_hint_h),
        "product_body_spacing": dp(12 if compact else 14),
        "placeholder_top": dp(32 if compact else 44),
        "placeholder_bottom": dp(20 if compact else 28),
        "placeholder_icon_sp": 36 if compact else 42,
        "action_h": dp(action_h),
        "action_button_h": dp(44 if compact else 48),
        "action_sp": int(13 * text_scale) if compact else int(14 * text_scale),
        "results_h": dp(result_h),
        "results_spacing": dp(result_space),
        "total_h": dp(total_h),
        "total_sp": int(20 * text_scale),
        "stage_row_h": dp(stage_row_h),
        "stage_head_h": dp(34 if compact else 38),
        "stage_icon_w": dp(34 if compact else 38),
        "stage_icon_sp": 22 if compact else 24,
        "unit_w": dp(64 if compact else 72),
        "unit_h": dp(38 if compact else 42),
        "footer_h": dp(42 if compact else 46),
        "footer_sp": int(11 * text_scale),
        "pro_w": dp(116 if compact else 128),
        "pro_h": dp(28),
        "ad_h": dp(reserved_ad_h),
    }

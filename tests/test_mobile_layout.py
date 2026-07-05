"""Behavior tests for the mobile layout metrics helpers."""
from __future__ import annotations

from tpof.mobile.layout import clamp, compute_metrics


def _dp(value):
    return value


def test_clamp_bounds():
    assert clamp(1.5, 0.88, 1.06) == 1.06
    assert clamp(0.5, 0.88, 1.06) == 0.88
    assert clamp(1.0, 0.88, 1.06) == 1.0


def test_compute_metrics_wide_screen_not_compact():
    m = compute_metrics(_dp, 412, 800, hints_enabled=True)
    assert m["narrow"] is False
    assert m["compact"] is False
    assert m["short"] is False
    assert m["text_scale"] == 1.0
    assert m["product_hint_h"] == 30


def test_compute_metrics_narrow_short_screen():
    m = compute_metrics(_dp, 320, 700, hints_enabled=False)
    assert m["narrow"] is True
    assert m["compact"] is True
    assert m["short"] is True
    assert m["product_hint_h"] == 0


def test_compute_metrics_hints_toggle_affects_product_hint_height():
    on = compute_metrics(_dp, 412, 800, hints_enabled=True)
    off = compute_metrics(_dp, 412, 800, hints_enabled=False)
    assert on["product_hint_h"] == 30
    assert off["product_hint_h"] == 0


def test_compute_metrics_native_ad_height_reserves_more_space():
    small = compute_metrics(_dp, 412, 800, hints_enabled=True, native_ad_height_dp=0)
    large = compute_metrics(_dp, 412, 800, hints_enabled=True, native_ad_height_dp=200)
    assert large["ad_h"] > small["ad_h"]

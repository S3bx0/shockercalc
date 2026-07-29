"""Behavior tests for the mobile layout metrics helpers."""
from __future__ import annotations

from tpof.mobile.layout import (
    ResponsiveLayoutController,
    ResponsiveLayoutView,
    clamp,
    compute_metrics,
)


class _Widget:
    def __init__(self, *, opacity=1):
        self.opacity = opacity
        self.width = -1
        self.height = -1
        self.padding = None
        self.spacing = None
        self.font_size = None
        self.icon_size = None
        self.line_height = None
        self.size_hint_y = "initial"
        self.md_bg_color = None
        self.shorten = False


class _Root:
    pos = (12, 24)
    size = (640, 1400)


class _Rect:
    pos = None
    size = None


class _Tab:
    def __init__(self):
        self.metrics = None

    def set_metrics(self, **metrics):
        self.metrics = metrics


def _responsive_state(*, pro_no_ads=False):
    screen_size = [640.0, 1400.0]
    hints_enabled = [False]
    native_ad_height = [0.0]
    privacy_refreshes = []
    freezing_metrics = []
    tabs = (_Tab(), _Tab(), _Tab())
    visible_chip = _Widget()
    hidden_chip = _Widget(opacity=0)
    ad_slot = _Widget()
    ad_slot.height = 777
    ad_slot.padding = "unchanged"
    view = ResponsiveLayoutView(
        root_host=_Root(),
        root_bg_rect=_Rect(),
        toolbar=_Widget(),
        toolbar_brand_chip=_Widget(),
        toolbar_snowflake=_Widget(),
        toolbar_title=_Widget(),
        action_chips=(
            visible_chip,
            _Widget(),
            _Widget(),
            hidden_chip,
        ),
        action_buttons=(_Widget(), _Widget(), _Widget(), _Widget()),
        tab_content_host=_Widget(),
        bottom_nav=_Widget(),
        bottom_tabs=tabs,
        footer_bar=_Widget(),
        footer_label=_Widget(),
        pro_button=_Widget(),
        ad_slot=ad_slot,
        ad_label=_Widget(),
    )
    controller = ResponsiveLayoutController(
        dp=lambda value: value * 2,
        get_screen_size=lambda: tuple(screen_size),
        hints_enabled=lambda: hints_enabled[0],
        native_ad_height_dp=lambda: native_ad_height[0],
        pro_no_ads=lambda: pro_no_ads,
        bottom_nav_bg=lambda: "nav-color",
        refresh_privacy_button=lambda: privacy_refreshes.append(True),
        apply_freezing_layout=freezing_metrics.append,
    )
    return {
        "controller": controller,
        "view": view,
        "screen_size": screen_size,
        "hints_enabled": hints_enabled,
        "native_ad_height": native_ad_height,
        "privacy_refreshes": privacy_refreshes,
        "freezing_metrics": freezing_metrics,
        "tabs": tabs,
        "visible_chip": visible_chip,
        "hidden_chip": hidden_chip,
    }


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


def test_responsive_controller_computes_metrics_before_view_attachment():
    state = _responsive_state()
    controller = state["controller"]

    metrics = controller.metrics()

    assert controller.is_attached is False
    assert controller.screen_dp() == (320.0, 700.0)
    assert metrics["compact"] is True
    assert metrics["short"] is True
    assert controller.apply() is False


def test_responsive_controller_metrics_follow_hints_and_native_ad_height():
    state = _responsive_state()
    controller = state["controller"]
    without_hints = controller.metrics()

    state["hints_enabled"][0] = True
    state["native_ad_height"][0] = 180
    updated = controller.metrics()

    assert without_hints["product_hint_h"] == 0
    assert updated["product_hint_h"] == 60
    assert updated["ad_h"] > without_hints["ad_h"]


def test_responsive_controller_applies_shell_and_tab_metrics():
    state = _responsive_state()
    controller = state["controller"]
    view = state["view"]
    controller.attach(view)

    assert controller.apply() is True

    metrics = controller.metrics()
    assert controller.is_attached is True
    assert view.toolbar.height == metrics["toolbar_h"]
    assert view.toolbar_brand_chip.width == metrics["toolbar_icon_w"]
    assert view.toolbar_snowflake.icon_size == f'{metrics["toolbar_icon_sp"]}sp'
    assert view.toolbar_title.font_size == f'{metrics["toolbar_title_sp"]}sp'
    assert state["visible_chip"].width == metrics["toolbar_btn_w"]
    assert state["hidden_chip"].width == -1
    assert all(
        button.icon_size == f'{metrics["toolbar_btn_sp"]}sp'
        for button in view.action_buttons
    )
    assert state["privacy_refreshes"] == [True]
    assert view.bottom_nav.height == metrics["bottom_nav_h"]
    assert view.bottom_nav.md_bg_color == "nav-color"
    assert all(
        tab.metrics
        == {
            "icon_size": metrics["bottom_tab_icon"],
            "label_sp": metrics["bottom_tab_sp"],
        }
        for tab in state["tabs"]
    )
    assert state["freezing_metrics"] == [metrics]
    assert view.footer_bar.height == metrics["footer_h"]
    assert view.pro_button.width == metrics["pro_w"]
    assert view.ad_slot.height == metrics["ad_h"]
    assert view.ad_label.font_size == f'{metrics["caption_sp"]}sp'


def test_responsive_controller_preserves_hidden_pro_ad_slot():
    state = _responsive_state(pro_no_ads=True)
    controller = state["controller"]
    view = state["view"]
    controller.attach(view)

    assert controller.apply() is True

    assert view.ad_slot.height == 777
    assert view.ad_slot.padding == "unchanged"


def test_responsive_controller_syncs_root_canvas_rectangle():
    state = _responsive_state()
    controller = state["controller"]

    assert controller.sync_root_background() is False
    controller.attach(state["view"])
    assert controller.sync_root_background() is True

    assert state["view"].root_bg_rect.pos == (12, 24)
    assert state["view"].root_bg_rect.size == (640, 1400)

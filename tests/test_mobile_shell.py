"""Behavior tests for the framework-independent mobile shell builder."""

from __future__ import annotations

from tpof.mobile.constants import BRAND_ICE
from tpof.mobile.shell import (
    MobileShellBuilder,
    MobileShellCallbacks,
    MobileShellFactories,
)


class _Widget:
    def __init__(self, kind, **kwargs):
        self.kind = kind
        self.children = []
        for name, value in kwargs.items():
            setattr(self, name, value)

    def add_widget(self, widget):
        self.children.append(widget)


def _factory(kind):
    return lambda **kwargs: _Widget(kind, **kwargs)


def _shell_state(*, hints_enabled=True):
    calls = []
    factories = MobileShellFactories(
        box_layout=_factory("box"),
        icon=_factory("icon"),
        icon_button=_factory("icon_button"),
        label=_factory("label"),
        raised_button=_factory("raised_button"),
        brand_toolbar=_factory("toolbar"),
        frost_chip=_factory("chip"),
        bottom_nav_tab=_factory("tab"),
        center_notice=_factory("notice"),
    )
    callbacks = MobileShellCallbacks(
        translate=lambda key: f"translated:{key}",
        hints_enabled=lambda: hints_enabled,
        on_toggle_hints=lambda: calls.append("hints"),
        on_toggle_language=lambda: calls.append("language"),
        on_toggle_theme=lambda: calls.append("theme"),
        on_open_privacy=lambda: calls.append("privacy"),
        on_open_settings=lambda: calls.append("settings"),
        on_select_tab=lambda name: calls.append(f"tab:{name}"),
        bottom_nav_bg=lambda: "bottom-bg",
        footer_bg=lambda: "footer-bg",
        ad_slot_bg=lambda: "ad-bg",
        footer_text=lambda: "footer-text",
        pro_button_text=lambda: "PRO 9,99 zł/mies.",
        on_buy_pro=lambda: calls.append("buy"),
        ad_label_text=lambda: "ad-text",
    )
    builder = MobileShellBuilder(
        dp=lambda value: value * 2,
        factories=factories,
        callbacks=callbacks,
    )
    return builder, calls


def test_builder_creates_toolbar_and_routes_actions():
    builder, calls = _shell_state(hints_enabled=True)

    view = builder.build()

    assert view.toolbar.kind == "toolbar"
    assert view.toolbar.height == 144
    assert view.toolbar.children == [
        view.toolbar_brand_chip,
        view.lbl_toolbar_title,
        view.btn_hints_chip,
        view.btn_lang_chip,
        view.btn_theme_chip,
        view.btn_privacy_chip,
    ]
    assert view.toolbar_brand_chip.active is True
    assert view.toolbar_snowflake.text_color == BRAND_ICE
    assert view.btn_hints_chip.active is True
    assert view.btn_hints.icon == "lightbulb-on-outline"
    assert view.btn_hints.text_color == BRAND_ICE

    view.toolbar_snowflake.on_release(None)
    view.btn_hints.on_release(None)
    view.btn_lang.on_release(None)
    view.btn_theme.on_release(None)
    view.btn_privacy.on_release(None)

    assert calls == ["settings", "hints", "language", "theme", "privacy"]


def test_builder_uses_inactive_hint_icon_when_hints_are_disabled():
    builder, _calls = _shell_state(hints_enabled=False)

    view = builder.build()

    assert view.btn_hints_chip.active is False
    assert view.btn_hints.icon == "lightbulb-off-outline"
    assert view.btn_hints.text_color == (0.93, 0.98, 1.0, 0.94)


def test_builder_creates_translated_bottom_navigation():
    builder, calls = _shell_state()

    view = builder.build()

    assert view.bottom_nav.md_bg_color == "bottom-bg"
    assert view.bottom_nav.children == [
        view.bottom_freezing_tab,
        view.bottom_valves_tab,
        view.bottom_labor_tab,
    ]
    assert [
        (tab.name, tab.text, tab.mode)
        for tab in view.bottom_nav.children
    ] == [
        ("freezing", "translated:nav_freezing", "snowflake"),
        ("valves", "translated:nav_valves", "valve"),
        ("labor", "translated:nav_labor", "calculator"),
    ]

    view.bottom_labor_tab.on_select("labor")

    assert calls == ["tab:labor"]


def test_builder_creates_footer_ad_slot_and_pro_action():
    builder, calls = _shell_state()

    view = builder.build()

    assert view.footer_bar.md_bg_color == "footer-bg"
    assert view.footer_bar.children == [view.btn_pro, view.footer_label]
    assert view.footer_label.text == "footer-text"
    assert view.btn_pro.text == "PRO 9,99 zł/mies."
    assert view.ad_slot.md_bg_color == "ad-bg"
    assert view.ad_slot.children[0].icon == "bullhorn"
    assert view.ad_slot.children[1] is view.ad_label
    assert view.ad_label.text == "ad-text"
    assert view.center_notice.kind == "notice"

    view.btn_pro.on_release(None)

    assert calls == ["buy"]


def test_shell_view_installs_all_references_on_app_boundary():
    builder, _calls = _shell_state()
    view = builder.build()

    class Shell:
        pass

    shell = Shell()
    view.install_on(shell)

    assert shell.toolbar is view.toolbar
    assert shell.btn_theme is view.btn_theme
    assert shell.bottom_valves_tab is view.bottom_valves_tab
    assert shell.footer_bar is view.footer_bar
    assert shell.ad_slot is view.ad_slot
    assert shell.center_notice is view.center_notice

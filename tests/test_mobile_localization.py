"""Behavior tests for mobile language state and text synchronization."""

from __future__ import annotations

from tpof import __version__
from tpof.mobile.i18n import translate
from tpof.mobile.localization import LocalizationController, LocalizationView


class _TextWidget:
    text = ""


class _ThemeButton:
    icon = ""


class _NavTab:
    def __init__(self):
        self.text = ""

    def set_text(self, text):
        self.text = text


def _controller_state(
    *,
    initial_language="pl",
    is_android=False,
    dark=True,
    pro=False,
    trial=True,
    days=3,
):
    app_state = {
        "dark": dark,
        "pro": pro,
        "trial": trial,
        "days": days,
    }
    closed = []
    settings = []
    refreshed = []
    controller = LocalizationController(
        initial_language=initial_language,
        is_android=is_android,
        is_dark=lambda: app_state["dark"],
        is_pro_no_ads=lambda: app_state["pro"],
        is_trial_active=lambda: app_state["trial"],
        trial_days_left=lambda: app_state["days"],
        close_product_dialog=lambda: closed.append(True),
        refresh_settings_ui=lambda: settings.append(True),
        refresh_callbacks=(
            lambda: refreshed.append("freezing"),
            lambda: refreshed.append("labor"),
            lambda: refreshed.append("valves"),
            lambda: refreshed.append("monetization"),
            lambda: refreshed.append("forms"),
        ),
    )
    view = LocalizationView(
        toolbar_title=_TextWidget(),
        theme_button=_ThemeButton(),
        ad_label=_TextWidget(),
        footer_label=_TextWidget(),
        nav_tabs={
            "freezing": _NavTab(),
            "valves": _NavTab(),
            "labor": _NavTab(),
        },
    )
    controller.attach(view)
    return {
        "controller": controller,
        "view": view,
        "app_state": app_state,
        "closed": closed,
        "settings": settings,
        "refreshed": refreshed,
    }


def test_refresh_updates_shell_and_all_localized_consumers():
    state = _controller_state(initial_language="pl", dark=True)
    controller = state["controller"]
    view = state["view"]

    controller.refresh()

    assert view.toolbar_title.text == "Refrigeration\nCalc"
    assert view.theme_button.icon == "weather-night"
    assert view.ad_label.text == translate("pl", "ad_placeholder")
    assert view.nav_tabs["freezing"].text == translate("pl", "nav_freezing")
    assert view.nav_tabs["valves"].text == translate("pl", "nav_valves")
    assert view.nav_tabs["labor"].text == translate("pl", "nav_labor")
    assert f"Refrigeration Calc v{__version__}" in view.footer_label.text
    assert state["refreshed"] == [
        "freezing",
        "labor",
        "valves",
        "monetization",
        "forms",
    ]


def test_toggle_switches_to_english_and_refreshes_settings():
    state = _controller_state(initial_language="pl")
    controller = state["controller"]
    view = state["view"]

    controller.toggle()

    assert controller.language == "en"
    assert state["closed"] == [True]
    assert state["settings"] == [True]
    assert view.nav_tabs["freezing"].text == translate("en", "nav_freezing")
    assert view.nav_tabs["valves"].text == translate("en", "nav_valves")
    assert view.nav_tabs["labor"].text == translate("en", "nav_labor")
    assert controller.display_category("owoce") == "fruit"


def test_toggle_returns_to_polish_and_light_theme_icon_is_preserved():
    state = _controller_state(initial_language="en", dark=False)
    controller = state["controller"]

    controller.toggle()

    assert controller.language == "pl"
    assert state["view"].theme_button.icon == "weather-sunny"
    assert controller.display_category("owoce") == "owoce"


def test_ad_label_uses_android_copy_and_pro_override():
    android_state = _controller_state(is_android=True)
    controller = android_state["controller"]

    assert controller.ad_label_text() == translate("pl", "ad")

    android_state["app_state"]["pro"] = True
    assert controller.ad_label_text() == translate("pl", "pro_ads_off")


def test_footer_text_covers_trial_expiry_and_pro_states():
    state = _controller_state(days=4)
    controller = state["controller"]
    app_state = state["app_state"]

    assert translate("pl", "trial_active", days=4) in controller.footer_text()

    app_state["days"] = 1
    assert translate("pl", "trial_last_day") in controller.footer_text()

    app_state["trial"] = False
    assert translate("pl", "trial_expired") in controller.footer_text()

    app_state["pro"] = True
    assert translate("pl", "pro_unlocked_footer") in controller.footer_text()


def test_unknown_initial_language_falls_back_to_polish():
    state = _controller_state(initial_language="de")

    assert state["controller"].language == "pl"
    assert state["controller"].translate("nav_labor") == translate(
        "pl",
        "nav_labor",
    )


def test_toggle_keeps_android_ad_text_and_pro_footer_consistent():
    state = _controller_state(initial_language="pl", is_android=True, pro=True)
    controller = state["controller"]

    controller.toggle()

    assert controller.language == "en"
    assert controller.ad_label_text() == translate("en", "pro_ads_off")
    assert "PRO • full access" in controller.footer_text()
    assert "Refrigeration Calc" in controller.footer_text()

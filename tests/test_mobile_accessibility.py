"""Behavior tests for framework-independent Android accessibility coordination."""
from __future__ import annotations

from tpof.mobile.accessibility import (
    MIN_TOUCH_TARGET_DP,
    AccessibilityController,
)


def _translate(key: str, **values: str) -> str:
    labels = {
        "nav_freezing": "Chłodnicze",
        "nav_valves": "Zawory",
        "nav_labor": "Robocizna",
        "accessibility_freezing_instructions": "Wprowadź parametry chłodzenia.",
        "accessibility_valves_instructions": "Wprowadź parametry zaworów.",
        "accessibility_labor_instructions": "Wprowadź koszty pracy.",
        "accessibility_screen_summary": "{screen}. {instructions}",
        "accessibility_screen_changed": "Wybrano ekran {screen}.",
    }
    return labels[key].format(**values)


def _controller():
    descriptions: list[str] = []
    announcements: list[str] = []
    controller = AccessibilityController(
        translate=_translate,
        configure_root=lambda value: descriptions.append(value) is None,
        announce_native=lambda value: announcements.append(value) is None,
    )
    return controller, descriptions, announcements


def test_accessibility_contract_uses_48_dp_minimum():
    assert MIN_TOUCH_TARGET_DP == 48.0


def test_screen_can_be_selected_before_native_surface_starts():
    controller, descriptions, announcements = _controller()

    assert controller.activate_screen("labor") is True
    assert controller.active_tab == "labor"
    assert descriptions == []
    assert announcements == []

    assert controller.start() is True
    assert descriptions == ["Robocizna. Wprowadź koszty pracy."]


def test_screen_change_updates_description_and_announces_name():
    controller, descriptions, announcements = _controller()
    controller.start()

    assert controller.activate_screen("valves") is True
    assert descriptions[-1] == "Zawory. Wprowadź parametry zaworów."
    assert announcements == ["Wybrano ekran Zawory."]


def test_refresh_reconfigures_current_localized_description():
    controller, descriptions, _announcements = _controller()
    assert controller.refresh() is False
    controller.activate_screen("labor")
    controller.start()

    assert controller.refresh() is True
    assert descriptions[-1] == "Robocizna. Wprowadź koszty pracy."


def test_result_announcement_requires_started_surface_and_nonempty_message():
    controller, _descriptions, announcements = _controller()

    assert controller.announce("Wynik: 12 kW") is False
    controller.start()
    assert controller.announce("  ") is False
    assert controller.announce("  Wynik: 12 kW  ") is True
    assert announcements == ["Wynik: 12 kW"]


def test_unknown_screen_is_rejected_without_changing_active_tab():
    controller, _descriptions, _announcements = _controller()

    assert controller.activate_screen("settings") is False
    assert controller.active_tab == "freezing"

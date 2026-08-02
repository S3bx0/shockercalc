"""Static contract tests for the native Android accessibility bridge."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_activity_keeps_accessibility_as_a_thin_service_delegate():
    activity = (
        ROOT
        / "android/src/pl/smilczarek/refrigerationcalc/RefrigerationCalcActivity.java"
    ).read_text(encoding="utf-8")

    assert "private AccessibilityService accessibilityService;" in activity
    assert "accessibilityService.configureRoot(description);" in activity
    assert "accessibilityService.announce(message);" in activity
    assert "AccessibilityManager" not in activity


def test_native_service_exposes_kivy_surface_to_talkback():
    service = (
        ROOT / "android/src/pl/smilczarek/refrigerationcalc/AccessibilityService.java"
    ).read_text(encoding="utf-8")

    for token in (
        "runOnUiThread",
        "IMPORTANT_FOR_ACCESSIBILITY_YES",
        "setContentDescription",
        "ACCESSIBILITY_LIVE_REGION_POLITE",
        "AccessibilityManager",
        "manager.isEnabled()",
        "announceForAccessibility",
    ):
        assert token in service

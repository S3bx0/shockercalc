from __future__ import annotations

from pathlib import Path

import pytest

from tpof.mobile.android_bridge import AndroidActivityBridge

ROOT = Path(__file__).resolve().parents[1]


class FakeActivity:
    def __init__(self) -> None:
        self.active_tabs: list[str] = []
        self.banner_height = 72
        self.privacy_required = True
        self.privacy_form_calls = 0
        self.pending_shortcut = "labor"
        self.shared_files: list[tuple[str, str, str, str]] = []
        self.feedback_emails: list[tuple[str, str, str]] = []
        self.google_play_packages: list[str] = []
        self.accessibility_descriptions: list[str] = []
        self.accessibility_announcements: list[str] = []

    def setActiveAdTab(self, tab: str) -> None:
        self.active_tabs.append(tab)

    def getBannerHeightDp(self) -> int:
        return self.banner_height

    def isPrivacyOptionsRequired(self) -> bool:
        return self.privacy_required

    def showPrivacyOptionsForm(self) -> None:
        self.privacy_form_calls += 1

    def consumePendingShortcutTab(self) -> str:
        target = self.pending_shortcut
        self.pending_shortcut = ""
        return target

    def shareFile(
        self,
        path: str,
        mime_type: str,
        subject: str,
        text: str,
    ) -> None:
        self.shared_files.append((path, mime_type, subject, text))

    def openFeedbackEmail(
        self,
        recipient: str,
        subject: str,
        body: str,
    ) -> None:
        self.feedback_emails.append((recipient, subject, body))

    def openGooglePlayListing(self, package_name: str) -> None:
        self.google_play_packages.append(package_name)

    def configureAccessibility(self, description: str) -> None:
        self.accessibility_descriptions.append(description)

    def announceForAccessibility(self, message: str) -> None:
        self.accessibility_announcements.append(message)


def test_bridge_delegates_native_activity_contract():
    activity = FakeActivity()
    bridge = AndroidActivityBridge(
        is_android=True,
        activity_loader=lambda: activity,
    )

    assert bridge.activity() is activity
    assert bridge.set_active_ad_tab("valves") is True
    assert bridge.configure_accessibility("Ekran zaworów") is True
    assert bridge.announce_for_accessibility("Wynik: 4 zawory") is True
    assert bridge.consume_shortcut_tab() == "labor"
    assert bridge.consume_shortcut_tab() is None
    assert bridge.banner_height_dp() == 72
    assert bridge.resolved_banner_height(False, 0) == 72
    assert bridge.resolved_banner_height(True, 40) == 40
    assert bridge.privacy_options_required() is True
    assert bridge.show_privacy_options_form() is None
    assert (
        bridge.share_file(
            "/tmp/report.pdf",
            "application/pdf",
            "Raport",
            "W załączniku",
        )
        is True
    )
    assert (
        bridge.open_feedback_email(
            "tester@example.com",
            "Opinia",
            "Treść",
        )
        is True
    )
    assert bridge.open_google_play_listing("pl.smilczarek.refrigerationcalc") is True

    assert activity.active_tabs == ["valves"]
    assert activity.accessibility_descriptions == ["Ekran zaworów"]
    assert activity.accessibility_announcements == ["Wynik: 4 zawory"]
    assert activity.privacy_form_calls == 1
    assert activity.shared_files == [
        (
            "/tmp/report.pdf",
            "application/pdf",
            "Raport",
            "W załączniku",
        )
    ]
    assert activity.feedback_emails == [
        ("tester@example.com", "Opinia", "Treść")
    ]
    assert activity.google_play_packages == ["pl.smilczarek.refrigerationcalc"]


def test_bridge_is_safe_noop_off_android():
    loads: list[bool] = []
    bridge = AndroidActivityBridge(
        is_android=False,
        activity_loader=lambda: loads.append(True),
    )

    assert bridge.set_active_ad_tab("labor") is False
    assert bridge.configure_accessibility("Ekran robocizny") is False
    assert bridge.announce_for_accessibility("Wynik") is False
    assert bridge.announce_for_accessibility("  ") is False
    assert bridge.consume_shortcut_tab() is None
    assert bridge.banner_height_dp() == 0
    assert bridge.resolved_banner_height(False, 64) == 64
    assert bridge.privacy_options_required() is False
    assert bridge.show_privacy_options_form() is None
    assert bridge.share_file("x", "y", "z", "t") is False
    assert bridge.open_feedback_email("x", "y", "z") is False
    assert bridge.open_google_play_listing("x") is False
    assert loads == []

    with pytest.raises(RuntimeError, match="outside Android"):
        bridge.activity()


def test_bridge_contains_failures_for_optional_ad_and_share_calls():
    class BrokenActivity(FakeActivity):
        def setActiveAdTab(self, tab: str) -> None:
            raise RuntimeError(tab)

        def getBannerHeightDp(self) -> int:
            raise RuntimeError("banner")

        def shareFile(
            self,
            path: str,
            mime_type: str,
            subject: str,
            text: str,
        ) -> None:
            raise RuntimeError(path)

        def openFeedbackEmail(
            self,
            recipient: str,
            subject: str,
            body: str,
        ) -> None:
            raise RuntimeError(recipient)

        def openGooglePlayListing(self, package_name: str) -> None:
            raise RuntimeError(package_name)

        def configureAccessibility(self, description: str) -> None:
            raise RuntimeError(description)

        def announceForAccessibility(self, message: str) -> None:
            raise RuntimeError(message)

    bridge = AndroidActivityBridge(
        is_android=True,
        activity_loader=BrokenActivity,
    )

    assert bridge.set_active_ad_tab("freezing") is False
    assert bridge.configure_accessibility("bad") is False
    assert bridge.announce_for_accessibility("bad") is False
    assert bridge.banner_height_dp() == 0
    assert bridge.resolved_banner_height(False, 64) == 64
    assert bridge.share_file("bad.pdf", "application/pdf", "x", "y") is False
    assert bridge.open_feedback_email("bad@example.com", "x", "y") is False
    assert bridge.open_google_play_listing("bad.package") is False


def test_bridge_leaves_privacy_failures_for_dialog_controller_to_report():
    class BrokenPrivacyActivity(FakeActivity):
        def isPrivacyOptionsRequired(self) -> bool:
            raise RuntimeError("UMP status")

        def showPrivacyOptionsForm(self) -> None:
            raise RuntimeError("UMP form")

    bridge = AndroidActivityBridge(
        is_android=True,
        activity_loader=BrokenPrivacyActivity,
    )

    with pytest.raises(RuntimeError, match="UMP status"):
        bridge.privacy_options_required()
    with pytest.raises(RuntimeError, match="UMP form"):
        bridge.show_privacy_options_form()


def test_default_loader_keeps_pyjnius_cast_inside_bridge():
    bridge_source = (
        ROOT / "tpof" / "mobile" / "android_bridge.py"
    ).read_text(encoding="utf-8")

    assert 'autoclass("org.kivy.android.PythonActivity").mActivity' in bridge_source
    assert (
        '"pl.smilczarek.refrigerationcalc.RefrigerationCalcActivity"'
        in bridge_source
    )
    assert "from jnius import autoclass, cast" in bridge_source


def test_app_uses_bridge_without_direct_native_activity_calls():
    app_source = (ROOT / "tpof" / "mobile" / "app.py").read_text(encoding="utf-8")
    composition_source = (
        ROOT / "tpof" / "mobile" / "app_controllers.py"
    ).read_text(encoding="utf-8")

    assert "self._android = AndroidActivityBridge(" in composition_source
    assert "get_android_activity=self._android.activity" in composition_source
    assert "self._android.set_active_ad_tab(name)" in app_source
    assert "self._android.resolved_banner_height(" in app_source
    assert "share_file=self._android.share_file" in composition_source
    assert "open_email=self._android.open_feedback_email" in composition_source
    assert "open_google_play=self._android.open_google_play_listing" in composition_source
    assert (
        "privacy_options_required=self._android.privacy_options_required"
        in composition_source
    )
    assert "def _android_activity" not in app_source
    assert "def _set_active_ad_tab" not in app_source
    for source in (app_source, composition_source):
        assert "from jnius" not in source
        assert ".setActiveAdTab(" not in source
        assert ".getBannerHeightDp(" not in source
        assert ".shareFile(" not in source
        assert ".openFeedbackEmail(" not in source
        assert ".openGooglePlayListing(" not in source

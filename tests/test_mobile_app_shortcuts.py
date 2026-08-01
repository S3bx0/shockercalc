from __future__ import annotations

from pathlib import Path

from tpof.mobile.services.app_shortcuts import AppShortcutController

ROOT = Path(__file__).resolve().parents[1]


def test_shortcut_controller_routes_supported_tab_and_records_event():
    opened: list[str] = []
    events: list[tuple[str, dict[str, object] | None]] = []
    controller = AppShortcutController(
        consume_target=lambda: "labor",
        open_tab=lambda tab: not opened.append(tab),
        log_event=lambda name, payload=None: events.append((name, payload)),
    )

    assert controller.consume_pending() is True
    assert opened == ["labor"]
    assert events == [("app_shortcut_opened", {"tab": "labor"})]


def test_shortcut_controller_rejects_empty_and_unknown_targets():
    for target in (None, "", "settings"):
        opened: list[str] = []
        controller = AppShortcutController(
            consume_target=lambda target=target: target,
            open_tab=lambda tab, opened=opened: not opened.append(tab),
            log_event=lambda _name, _payload=None: None,
        )

        assert controller.consume_pending() is False
        assert opened == []


def test_shortcut_controller_does_not_report_failed_navigation():
    events: list[str] = []
    controller = AppShortcutController(
        consume_target=lambda: "valves",
        open_tab=lambda _tab: False,
        log_event=lambda name, _payload=None: events.append(name),
    )

    assert controller.consume_pending() is False
    assert events == []


def test_app_composes_and_consumes_shortcuts_through_existing_navigation():
    app = (ROOT / "tpof/mobile/app.py").read_text(encoding="utf-8")
    composition = (ROOT / "tpof/mobile/app_controllers.py").read_text(
        encoding="utf-8"
    )

    assert "self._app_shortcuts = AppShortcutController(" in composition
    assert "consume_target=self._android.consume_shortcut_tab" in composition
    assert "open_tab=lambda name: self._show_tab(name, animate=False)" in composition
    assert "self._app_shortcuts.consume_pending()" in app
    assert "def on_resume(self):" in app

"""Framework-independent coordination for Android accessibility feedback."""
from __future__ import annotations

from collections.abc import Callable

MIN_TOUCH_TARGET_DP = 48.0


class AccessibilityController:
    """Keep the native Kivy surface description in sync with the visible tab."""

    def __init__(
        self,
        *,
        translate: Callable[..., str],
        configure_root: Callable[[str], bool],
        announce_native: Callable[[str], bool],
    ) -> None:
        self._translate = translate
        self._configure_root = configure_root
        self._announce_native = announce_native
        self._active_tab = "freezing"
        self._started = False

    @property
    def active_tab(self) -> str:
        return self._active_tab

    def screen_name(self, tab: str | None = None) -> str:
        key = tab if tab in {"freezing", "valves", "labor"} else "freezing"
        return self._translate(f"nav_{key}")

    def screen_description(self, tab: str | None = None) -> str:
        key = tab if tab in {"freezing", "valves", "labor"} else "freezing"
        return self._translate(
            "accessibility_screen_summary",
            screen=self.screen_name(key),
            instructions=self._translate(f"accessibility_{key}_instructions"),
        )

    def start(self) -> bool:
        self._started = True
        return self._configure_root(self.screen_description(self._active_tab))

    def activate_screen(self, tab: str) -> bool:
        if tab not in {"freezing", "valves", "labor"}:
            return False
        self._active_tab = tab
        if not self._started:
            return True
        configured = self._configure_root(self.screen_description(tab))
        announced = self._announce_native(
            self._translate("accessibility_screen_changed", screen=self.screen_name(tab))
        )
        return configured or announced

    def refresh(self) -> bool:
        if not self._started:
            return False
        return self._configure_root(self.screen_description(self._active_tab))

    def announce(self, message: str) -> bool:
        if not self._started or not str(message).strip():
            return False
        return self._announce_native(str(message).strip())

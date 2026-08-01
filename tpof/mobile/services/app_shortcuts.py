"""Application-shortcut routing independent from Android and Kivy."""

from __future__ import annotations

from collections.abc import Callable

from tpof.mobile.navigation import TAB_NAMES


class AppShortcutController:
    """Consume a native shortcut target and route it through normal navigation."""

    def __init__(
        self,
        *,
        consume_target: Callable[[], str | None],
        open_tab: Callable[[str], bool],
        log_event: Callable[[str, dict[str, object] | None], None],
    ) -> None:
        self._consume_target = consume_target
        self._open_tab = open_tab
        self._log_event = log_event

    def consume_pending(self) -> bool:
        """Open one supported pending target, if the native layer has one."""

        target = self._consume_target()
        if target not in TAB_NAMES:
            return False
        if not self._open_tab(target):
            return False
        self._log_event("app_shortcut_opened", {"tab": target})
        return True

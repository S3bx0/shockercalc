"""Framework-independent navigation controller for the mobile application."""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping
from typing import Any

log = logging.getLogger(__name__)

TAB_NAMES = ("freezing", "valves", "labor")


class TabNavigationController:
    """Coordinates tab visibility and navigation side effects.

    The controller intentionally knows only the small widget protocol used by
    the application. It can therefore be tested without importing Kivy.
    """

    def __init__(
        self,
        *,
        get_tab_widgets: Callable[[], Mapping[str, Any]],
        get_nav_tabs: Callable[[], Mapping[str, Any]],
        get_host: Callable[[], Any | None],
        set_active_name: Callable[[str], None],
        report_tab: Callable[[str], None],
        on_tab_enter: Callable[[str], None],
        refresh_theme: Callable[[], None],
        schedule_once: Callable[[Callable[..., object], float], object],
        logger: logging.Logger | None = None,
    ) -> None:
        self._get_tab_widgets = get_tab_widgets
        self._get_nav_tabs = get_nav_tabs
        self._get_host = get_host
        self._set_active_name = set_active_name
        self._report_tab = report_tab
        self._on_tab_enter = on_tab_enter
        self._refresh_theme = refresh_theme
        self._schedule_once = schedule_once
        self._logger = logger or log
        self._active_name = TAB_NAMES[0]

    @property
    def active_name(self) -> str:
        return self._active_name

    def handle_legacy_switch(self, *args: object) -> bool:
        """Accept the callback shapes used by the former bottom navigation."""

        name = self.resolve_name(*args)
        return bool(name and self.show(name))

    @staticmethod
    def resolve_name(*args: object) -> str | None:
        for arg in args:
            if isinstance(arg, str) and arg in TAB_NAMES:
                return arg
            item_name = getattr(arg, "name", None)
            if item_name in TAB_NAMES:
                return str(item_name)
        return None

    def show(self, name: str, *, animate: bool = True, report: bool = True) -> bool:
        """Show one tab while disabling every hidden touch layer."""

        if name not in TAB_NAMES:
            return False

        self._active_name = name
        self._set_active_name(name)

        tab_widgets = self._get_tab_widgets()
        for tab_name, widget in tab_widgets.items():
            self.set_tab_visibility(widget, tab_name == name)
        self.raise_tab_widget(self._get_host(), tab_widgets.get(name))

        nav_tabs = self._get_nav_tabs()
        for tab_name, tab in nav_tabs.items():
            if tab is not None:
                tab.set_active(tab_name == name)

        if report:
            self._report_tab(name)
        if animate:
            self._animate_tab(nav_tabs.get(name))

        self._on_tab_enter(name)

        # KivyMD sometimes keeps disabled colors after a hidden tab returns.
        # Refresh immediately and once more on the next UI loop iteration.
        self._refresh_theme()
        self._schedule_once(lambda *_args: self._refresh_theme(), 0)
        return True

    @staticmethod
    def set_tab_visibility(widget: Any | None, active: bool) -> None:
        """Ensure a hidden tab cannot remain an invisible touch layer."""

        if widget is None:
            return
        if active:
            widget.size_hint = (1, 1)
            widget.pos_hint = {"x": 0, "y": 0}
            widget.opacity = 1
            widget.disabled = False
            return

        widget.opacity = 0
        widget.disabled = True
        widget.size_hint = (None, None)
        widget.size = (0, 0)
        widget.pos = (0, 0)
        widget.pos_hint = {}

    @staticmethod
    def raise_tab_widget(host: Any | None, widget: Any | None) -> None:
        if host is None or widget is None or widget.parent is not host:
            return
        host.remove_widget(widget)
        host.add_widget(widget)

    def _animate_tab(self, tab: Any | None) -> None:
        if tab is None:
            return
        try:
            tab.play()
        except Exception:
            self._logger.debug("Animacja zakładki nie powiodła się", exc_info=True)

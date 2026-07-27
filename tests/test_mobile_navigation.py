from __future__ import annotations

from types import SimpleNamespace

from tpof.mobile.navigation import TAB_NAMES, TabNavigationController


class _Widget:
    def __init__(self, parent=None) -> None:
        self.parent = parent
        self.size_hint = (1, 1)
        self.pos_hint = {"x": 0, "y": 0}
        self.opacity = 1
        self.disabled = False
        self.size = (100, 100)
        self.pos = (10, 20)


class _Host:
    def __init__(self) -> None:
        self.removed: list[_Widget] = []
        self.added: list[_Widget] = []

    def remove_widget(self, widget: _Widget) -> None:
        self.removed.append(widget)
        widget.parent = None

    def add_widget(self, widget: _Widget) -> None:
        self.added.append(widget)
        widget.parent = self


class _Tab:
    def __init__(self) -> None:
        self.active_states: list[bool] = []
        self.play_count = 0

    def set_active(self, active: bool) -> None:
        self.active_states.append(active)

    def play(self) -> None:
        self.play_count += 1


def _navigation_fixture():
    host = _Host()
    widgets = {name: _Widget(host) for name in TAB_NAMES}
    tabs = {name: _Tab() for name in TAB_NAMES}
    active_names = []
    reports = []
    entered = []
    theme_refreshes = []
    scheduled = []

    def schedule_once(callback, delay):
        scheduled.append((callback, delay))
        return object()

    controller = TabNavigationController(
        get_tab_widgets=lambda: widgets,
        get_nav_tabs=lambda: tabs,
        get_host=lambda: host,
        set_active_name=active_names.append,
        report_tab=reports.append,
        on_tab_enter=entered.append,
        refresh_theme=lambda: theme_refreshes.append(True),
        schedule_once=schedule_once,
    )
    return SimpleNamespace(
        controller=controller,
        host=host,
        widgets=widgets,
        tabs=tabs,
        active_names=active_names,
        reports=reports,
        entered=entered,
        theme_refreshes=theme_refreshes,
        scheduled=scheduled,
    )


def test_show_switches_visibility_and_updates_navigation_state():
    state = _navigation_fixture()

    assert state.controller.show("valves") is True

    assert state.controller.active_name == "valves"
    assert state.active_names == ["valves"]
    assert state.reports == ["valves"]
    assert state.entered == ["valves"]

    active = state.widgets["valves"]
    assert active.size_hint == (1, 1)
    assert active.pos_hint == {"x": 0, "y": 0}
    assert active.opacity == 1
    assert active.disabled is False
    assert state.host.removed == [active]
    assert state.host.added == [active]

    for name in ("freezing", "labor"):
        hidden = state.widgets[name]
        assert hidden.opacity == 0
        assert hidden.disabled is True
        assert hidden.size_hint == (None, None)
        assert hidden.size == (0, 0)
        assert hidden.pos == (0, 0)
        assert hidden.pos_hint == {}

    assert state.tabs["freezing"].active_states == [False]
    assert state.tabs["valves"].active_states == [True]
    assert state.tabs["labor"].active_states == [False]
    assert state.tabs["valves"].play_count == 1


def test_show_refreshes_theme_immediately_and_on_next_ui_tick():
    state = _navigation_fixture()

    state.controller.show("labor")

    assert len(state.theme_refreshes) == 1
    assert len(state.scheduled) == 1
    callback, delay = state.scheduled[0]
    assert delay == 0

    callback()

    assert len(state.theme_refreshes) == 2


def test_initial_switch_can_skip_animation_and_reporting():
    state = _navigation_fixture()

    assert state.controller.show("freezing", animate=False, report=False) is True

    assert state.reports == []
    assert all(tab.play_count == 0 for tab in state.tabs.values())
    assert state.entered == ["freezing"]


def test_unknown_tab_is_ignored_without_side_effects():
    state = _navigation_fixture()

    assert state.controller.show("unknown") is False

    assert state.active_names == []
    assert state.reports == []
    assert state.entered == []
    assert state.scheduled == []
    assert state.host.removed == []
    assert state.host.added == []


def test_legacy_callback_resolves_string_or_named_item():
    state = _navigation_fixture()

    assert state.controller.handle_legacy_switch(object(), "labor") is True
    assert state.controller.handle_legacy_switch(SimpleNamespace(name="valves")) is True
    assert state.controller.handle_legacy_switch(SimpleNamespace(name="other")) is False

    assert state.active_names == ["labor", "valves"]


def test_raise_tab_widget_ignores_widget_from_another_host():
    host = _Host()
    other_host = _Host()
    widget = _Widget(other_host)

    TabNavigationController.raise_tab_widget(host, widget)

    assert host.removed == []
    assert host.added == []

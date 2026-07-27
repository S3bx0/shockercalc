"""Behavior tests for framework-independent mobile form interactions."""

from __future__ import annotations

from tpof.mobile.constants import BRAND_ICE
from tpof.mobile.form_interactions import (
    FormInteractionController,
    FormInteractionView,
)


class _Field:
    def __init__(self):
        self.error = False
        self.helper_text = ""
        self.helper_text_mode = ""
        self.bindings = {}

    def bind(self, **kwargs):
        self.bindings.update(kwargs)


class _HintsButton:
    icon = ""
    text_color = None


class _HintsChip:
    def __init__(self):
        self.active = None

    def set_active(self, active):
        self.active = active


def _controller_state(*, enabled=True):
    field = _Field()
    persisted = []
    refreshed = []
    layouts = []
    messages = []
    events = []
    scheduled = []
    controller = FormInteractionController(
        hints_enabled=enabled,
        set_hints_enabled=persisted.append,
        translate=lambda key: f"translated:{key}",
        get_hint_field_items=lambda: ((field, "hint_mass"), (None, "ignored")),
        refresh_freezing_texts=lambda: refreshed.append(True),
        apply_responsive_layout=lambda: layouts.append(True),
        show_message=messages.append,
        log_event=lambda name, parameters: events.append((name, parameters)),
        schedule_once=lambda callback, delay: scheduled.append((callback, delay)),
        dp=lambda value: value * 2,
    )
    button = _HintsButton()
    chip = _HintsChip()
    controller.attach(FormInteractionView(button, chip))
    return {
        "controller": controller,
        "field": field,
        "button": button,
        "chip": chip,
        "persisted": persisted,
        "refreshed": refreshed,
        "layouts": layouts,
        "messages": messages,
        "events": events,
        "scheduled": scheduled,
    }


def test_apply_updates_shell_fields_and_binds_validation_once():
    state = _controller_state(enabled=True)
    controller = state["controller"]
    field = state["field"]

    controller.apply()
    first_binding = field.bindings["text"]
    controller.apply()

    assert state["button"].icon == "lightbulb-on-outline"
    assert state["button"].text_color == BRAND_ICE
    assert state["chip"].active is True
    assert field.helper_text == "translated:hint_mass"
    assert field.helper_text_mode == "on_focus"
    assert field.bindings["text"] is first_binding
    assert state["refreshed"] == [True, True]


def test_toggle_persists_state_refreshes_layout_and_reports_event():
    state = _controller_state(enabled=True)

    state["controller"].toggle()

    assert state["controller"].hints_enabled is False
    assert state["persisted"] == [False]
    assert state["layouts"] == [True]
    assert state["messages"] == ["translated:hints_off"]
    assert state["events"] == [("hints_toggled", {"enabled": False})]
    assert state["button"].icon == "lightbulb-off-outline"
    assert state["button"].text_color == (0.93, 0.98, 1.0, 0.94)
    assert state["chip"].active is False
    assert state["field"].helper_text == ""


def test_mark_and_clear_error_restore_the_matching_hint():
    state = _controller_state(enabled=True)
    controller = state["controller"]
    field = state["field"]

    controller.mark_field_error(field)
    assert field.error is True
    assert field.helper_text == "translated:field_required"
    assert field.helper_text_mode == "on_error"

    controller.clear_field_error(field)
    assert field.error is False
    assert field.helper_text == "translated:hint_mass"
    assert field.helper_text_mode == "on_focus"


def test_apply_does_not_overwrite_an_active_validation_error():
    state = _controller_state(enabled=True)
    controller = state["controller"]
    field = state["field"]
    controller.mark_field_error(field, "custom error")

    controller.apply()

    assert field.error is True
    assert field.helper_text == "custom error"
    assert field.helper_text_mode == "on_error"


def test_focused_field_schedules_two_keyboard_scroll_attempts():
    state = _controller_state()
    controller = state["controller"]
    field = state["field"]

    class _Scroll:
        def __init__(self):
            self.calls = []

        def scroll_to(self, widget, **kwargs):
            self.calls.append((widget, kwargs))

    scroll = _Scroll()
    controller.bind_keyboard_scroll((field, None), scroll)
    field.bindings["focus"](field, False)
    assert state["scheduled"] == []

    field.bindings["focus"](field, True)
    assert [delay for _, delay in state["scheduled"]] == [0.08, 0.35]

    for callback, _delay in state["scheduled"]:
        callback()
    assert scroll.calls == [
        (field, {"padding": 300, "animate": True}),
        (field, {"padding": 300, "animate": True}),
    ]


def test_keyboard_scroll_falls_back_for_older_scroll_view_signature():
    state = _controller_state()
    controller = state["controller"]
    field = state["field"]

    class _LegacyScroll:
        def __init__(self):
            self.calls = []

        def scroll_to(self, widget):
            self.calls.append(widget)

    scroll = _LegacyScroll()
    controller.bind_keyboard_scroll((field,), scroll)
    field.bindings["focus"](field, True)
    state["scheduled"][0][0]()

    assert scroll.calls == [field]

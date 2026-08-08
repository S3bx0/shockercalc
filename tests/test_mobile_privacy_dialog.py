from __future__ import annotations

from tpof.mobile.dialogs.privacy import (
    PrivacyDialogController,
    PrivacyDialogWidgets,
    PrivacyToolbarController,
)


class _Button:
    def __init__(self, **kwargs) -> None:
        self.text = kwargs["text"]
        self.on_release = kwargs["on_release"]


class _Dialog:
    def __init__(self, **kwargs) -> None:
        self.title = kwargs["title"]
        self.text = kwargs.get("text")
        self.buttons = kwargs["buttons"]
        self.type = kwargs.get("type")
        self.content_cls = kwargs.get("content_cls")
        self.opened = False
        self.dismissed = False

    def open(self) -> None:
        self.opened = True

    def dismiss(self) -> None:
        self.dismissed = True


class _ToolbarItem:
    disabled = False
    opacity = 1
    width = 0
    height = 0


def _state(
    *,
    is_android: bool = True,
    telemetry_available: bool = True,
    has_preference: bool = False,
    telemetry_enabled: bool = False,
    ad_privacy_required: bool = False,
    show_privacy_options_form=None,
    widgets: PrivacyDialogWidgets | None = None,
):
    telemetry_changes = []
    refreshes = []
    events = []
    exceptions = []
    dialogs = []

    def dialog_factory(**kwargs):
        dialog = _Dialog(**kwargs)
        dialogs.append(dialog)
        return dialog

    if widgets is None:
        widgets = PrivacyDialogWidgets(
            dialog=dialog_factory,
            flat_button=_Button,
            raised_button=_Button,
        )

    def translate(key, **_values):
        return key

    def set_telemetry_enabled(enabled):
        telemetry_changes.append(enabled)
        return True

    controller = PrivacyDialogController(
        translate=translate,
        is_android=is_android,
        telemetry_available=lambda: telemetry_available,
        telemetry_has_preference=lambda: has_preference,
        telemetry_enabled=lambda: telemetry_enabled,
        set_telemetry_enabled=set_telemetry_enabled,
        privacy_options_required=lambda: ad_privacy_required,
        show_privacy_options_form=show_privacy_options_form or (lambda: None),
        refresh_button=lambda: refreshes.append(True),
        log_event=lambda *args: events.append(args),
        record_exception=lambda exc, context: exceptions.append((exc, context)),
        widgets=widgets,
    )
    return {
        "controller": controller,
        "telemetry_changes": telemetry_changes,
        "refreshes": refreshes,
        "events": events,
        "exceptions": exceptions,
        "dialogs": dialogs,
    }


def test_options_available_only_on_android_with_telemetry_or_ump():
    assert _state(is_android=False)["controller"].options_available() is False
    assert (
        _state(
            telemetry_available=False,
            ad_privacy_required=False,
        )["controller"].options_available()
        is False
    )
    assert _state(telemetry_available=True)["controller"].options_available() is True
    assert (
        _state(
            telemetry_available=False,
            ad_privacy_required=True,
        )["controller"].options_available()
        is True
    )


def test_prompt_is_skipped_after_preference_and_refreshes_toolbar():
    state = _state(has_preference=True)

    assert state["controller"].prompt_telemetry_consent() is False

    assert state["refreshes"] == [True]
    assert state["dialogs"] == []


def test_prompt_opens_and_accepting_consent_releases_dialog():
    state = _state()
    controller = state["controller"]

    assert controller.prompt_telemetry_consent() is True

    dialog = state["dialogs"][0]
    assert dialog.opened is True
    assert dialog.title == "telemetry_title"
    assert [button.text for button in dialog.buttons] == [
        "telemetry_not_now",
        "telemetry_enable",
    ]
    assert controller.is_telemetry_prompt_open is True

    assert controller.set_telemetry_consent(True) is True

    assert state["telemetry_changes"] == [True]
    assert state["refreshes"] == [True]
    assert state["events"] == [("telemetry_enabled",)]
    assert dialog.dismissed is True
    assert controller.is_telemetry_prompt_open is False


def test_prompt_uses_scrollable_text_when_runtime_factory_supports_it():
    state = _state(
        widgets=PrivacyDialogWidgets(
            dialog=lambda **kwargs: _Dialog(**kwargs),
            flat_button=_Button,
            raised_button=_Button,
            scroll_text=lambda text: ("scroll", text),
        )
    )
    controller = state["controller"]

    assert controller.prompt_telemetry_consent() is True

    dialog = controller._telemetry_dialog
    assert dialog.type == "custom"
    assert dialog.text is None
    assert dialog.content_cls == ("scroll", "telemetry_text")


def test_privacy_dialog_combines_telemetry_and_ump_actions():
    form_calls = []
    state = _state(
        ad_privacy_required=True,
        show_privacy_options_form=lambda: form_calls.append(True),
    )
    controller = state["controller"]

    assert controller.open() is True

    dialog = state["dialogs"][0]
    assert dialog.opened is True
    assert dialog.title == "privacy_title"
    assert dialog.text == "telemetry_off"
    assert [button.text for button in dialog.buttons] == [
        "telemetry_enable",
        "ad_privacy",
        "close",
    ]
    assert state["events"] == [
        ("settings_opened", {"section": "privacy"}),
    ]
    assert controller.is_open is True

    assert dialog.buttons[1].on_release() is True

    assert form_calls == [True]
    assert dialog.dismissed is True
    assert controller.is_open is False


def test_changing_telemetry_from_settings_closes_and_refreshes():
    state = _state()
    controller = state["controller"]
    assert controller.open() is True
    dialog = state["dialogs"][0]

    assert controller.change_telemetry(False) is True

    assert state["telemetry_changes"] == [False]
    assert state["refreshes"] == [True]
    assert state["events"] == [
        ("settings_opened", {"section": "privacy"}),
    ]
    assert dialog.dismissed is True
    assert controller.is_open is False


def test_open_reports_widget_failure_and_clears_dialog_state():
    def fail_dialog(**_kwargs):
        raise RuntimeError("dialog unavailable")

    state = _state(
        widgets=PrivacyDialogWidgets(
            dialog=fail_dialog,
            flat_button=_Button,
            raised_button=_Button,
        )
    )

    assert state["controller"].open() is False

    assert len(state["exceptions"]) == 1
    error, context = state["exceptions"][0]
    assert isinstance(error, RuntimeError)
    assert context == "open_privacy_options"
    assert state["controller"].is_open is False


def test_ad_privacy_form_failure_is_reported_without_escaping():
    def fail_form():
        raise RuntimeError("UMP unavailable")

    state = _state(
        telemetry_available=False,
        ad_privacy_required=True,
        show_privacy_options_form=fail_form,
    )

    assert state["controller"].open_ad_privacy_options() is False

    assert len(state["exceptions"]) == 1
    error, context = state["exceptions"][0]
    assert isinstance(error, RuntimeError)
    assert context == "open_ad_privacy_options"


def test_privacy_toolbar_controller_shows_and_sizes_button_and_chip():
    button = _ToolbarItem()
    chip = _ToolbarItem()
    controller = PrivacyToolbarController(
        options_available=lambda: True,
        get_button=lambda: button,
        get_chip=lambda: chip,
        get_target_width=lambda: 56,
        get_fallback_width=lambda: 48,
    )

    controller.refresh()

    assert button.disabled is False
    assert button.opacity == 1
    assert button.width == 56
    assert chip.disabled is False
    assert chip.opacity == 1
    assert chip.width == 56
    assert chip.height == 56


def test_privacy_toolbar_controller_hides_unavailable_controls():
    button = _ToolbarItem()
    chip = _ToolbarItem()
    controller = PrivacyToolbarController(
        options_available=lambda: False,
        get_button=lambda: button,
        get_chip=lambda: chip,
        get_target_width=lambda: 56,
        get_fallback_width=lambda: 48,
    )

    controller.refresh()

    assert button.disabled is True
    assert button.opacity == 0
    assert button.width == 0
    assert chip.disabled is True
    assert chip.opacity == 0
    assert chip.width == 0
    assert chip.height == 56


def test_privacy_toolbar_controller_uses_fallback_and_allows_missing_view():
    button = _ToolbarItem()
    controller = PrivacyToolbarController(
        options_available=lambda: True,
        get_button=lambda: button,
        get_chip=lambda: None,
        get_target_width=lambda: (_ for _ in ()).throw(RuntimeError("no layout")),
        get_fallback_width=lambda: 48,
    )

    controller.refresh()

    assert button.width == 48

    missing_controller = PrivacyToolbarController(
        options_available=lambda: True,
        get_button=lambda: None,
        get_chip=lambda: None,
        get_target_width=lambda: 56,
        get_fallback_width=lambda: 48,
    )
    missing_controller.refresh()

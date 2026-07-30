from __future__ import annotations

from tpof.mobile.i18n import translate
from tpof.mobile.services.user_feedback import (
    CONTACT_EMAIL,
    UserFeedbackController,
    build_feedback_draft,
)


def test_feedback_draft_contains_only_editable_template_and_app_metadata():
    draft = build_feedback_draft(
        translate=lambda key, **kwargs: translate("pl", key, **kwargs),
        language="pl",
        app_version="1.5.12",
    )

    assert draft.recipient == CONTACT_EMAIL
    assert "1.5.12" in draft.subject
    assert "Opisz swoją opinię lub problem" in draft.body
    assert "Aplikacja: Refrigeration Calc" in draft.body
    assert "Wersja: 1.5.12" in draft.body
    assert "Język: pl" in draft.body
    assert "urządzen" not in draft.body.casefold()
    assert "android id" not in draft.body.casefold()


def test_feedback_draft_is_localized_to_english():
    draft = build_feedback_draft(
        translate=lambda key, **kwargs: translate("en", key, **kwargs),
        language="en",
        app_version="2.0.0",
    )

    assert draft.subject == "Refrigeration Calc 2.0.0 — feedback or bug"
    assert "Steps to reproduce:" in draft.body
    assert "Language: en" in draft.body


def test_feedback_controller_opens_native_draft_and_logs_action():
    opened: list[tuple[str, str, str]] = []
    events: list[tuple[str, object]] = []
    messages: list[str] = []
    errors: list[tuple[BaseException, str]] = []
    controller = UserFeedbackController(
        translate=lambda key, **kwargs: translate("pl", key, **kwargs),
        get_language=lambda: "pl",
        open_email=lambda recipient, subject, body: (
            opened.append((recipient, subject, body)) or True
        ),
        show_message=messages.append,
        log_event=lambda name, params=None: events.append((name, params)),
        record_exception=lambda exc, context: errors.append((exc, context)),
        app_version="1.5.12",
    )

    assert controller.open() is True
    assert opened[0][0] == CONTACT_EMAIL
    assert events == [("feedback_opened", {"channel": "email"})]
    assert messages == []
    assert errors == []


def test_feedback_controller_reports_missing_email_app():
    messages: list[str] = []
    controller = UserFeedbackController(
        translate=lambda key, **kwargs: translate("en", key, **kwargs),
        get_language=lambda: "en",
        open_email=lambda _recipient, _subject, _body: False,
        show_message=messages.append,
        log_event=lambda _name, _params=None: None,
        record_exception=lambda _exc, _context: None,
    )

    assert controller.open() is False
    assert messages == [
        "The email app could not be opened. Contact: "
        "milczarek.sebastian1988@gmail.com"
    ]


def test_feedback_controller_contains_platform_exception():
    errors: list[tuple[BaseException, str]] = []
    messages: list[str] = []

    def fail(_recipient: str, _subject: str, _body: str) -> bool:
        raise RuntimeError("platform")

    controller = UserFeedbackController(
        translate=lambda key, **kwargs: translate("pl", key, **kwargs),
        get_language=lambda: "pl",
        open_email=fail,
        show_message=messages.append,
        log_event=lambda _name, _params=None: None,
        record_exception=lambda exc, context: errors.append((exc, context)),
    )

    assert controller.open() is False
    assert errors[0][1] == "open_feedback"
    assert "Nie udało się otworzyć aplikacji pocztowej" in messages[0]

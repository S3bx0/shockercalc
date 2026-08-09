"""User-initiated feedback drafts for the mobile application.

The service prepares an editable email and delegates opening the composer to
the platform bridge. It never sends data or collects diagnostics in the
background.
"""
from __future__ import annotations

import logging
from collections.abc import Callable, Mapping
from dataclasses import dataclass

from tpof import __version__
from tpof.mobile.constants import APP_NAME

log = logging.getLogger(__name__)

CONTACT_EMAIL = "milczarek.sebastian1988@gmail.com"
GOOGLE_PLAY_PACKAGE_NAME = "pl.smilczarek.refrigerationcalc"


@dataclass(frozen=True)
class FeedbackDraft:
    """Editable message passed to the platform email client."""

    recipient: str
    subject: str
    body: str


def build_feedback_draft(
    *,
    translate: Callable[..., str],
    language: str,
    app_version: str = __version__,
) -> FeedbackDraft:
    """Build a localized, structured draft with non-sensitive app metadata."""

    return FeedbackDraft(
        recipient=CONTACT_EMAIL,
        subject=translate("feedback_email_subject", version=app_version),
        body=translate(
            "feedback_email_body",
            app_name=APP_NAME,
            version=app_version,
            language_code=language,
        ),
    )


class UserFeedbackController:
    """Prepare a feedback draft and open it in a user-controlled email app."""

    def __init__(
        self,
        *,
        translate: Callable[..., str],
        get_language: Callable[[], str],
        open_email: Callable[[str, str, str], bool],
        open_google_play: Callable[[str], bool],
        show_message: Callable[[str], None],
        log_event: Callable[[str, Mapping[str, object] | None], None],
        record_exception: Callable[[BaseException, str], None],
        app_version: str = __version__,
    ) -> None:
        self._translate = translate
        self._get_language = get_language
        self._open_email = open_email
        self._open_google_play = open_google_play
        self._show_message = show_message
        self._log_event = log_event
        self._record_exception = record_exception
        self._app_version = app_version

    def open(self) -> bool:
        """Open an editable draft; return whether the native handoff succeeded."""

        try:
            draft = build_feedback_draft(
                translate=self._translate,
                language=self._get_language(),
                app_version=self._app_version,
            )
            if self._open_email(draft.recipient, draft.subject, draft.body):
                self._log_event(
                    "feedback_opened",
                    {"channel": "email", "template_version": 2},
                )
                return True
        except Exception as exc:  # pragma: no cover - platform boundary
            self._record_exception(exc, "open_feedback")
            log.exception("Otwarcie formularza opinii")

        self._show_message(self._translate("feedback_unavailable"))
        return False

    def open_google_play_feedback(self) -> bool:
        """Open Google Play; the tester chooses whether to post feedback there."""

        try:
            if self._open_google_play(GOOGLE_PLAY_PACKAGE_NAME):
                self._log_event("feedback_opened", {"channel": "google_play"})
                return True
        except Exception as exc:  # pragma: no cover - platform boundary
            self._record_exception(exc, "open_google_play_feedback")
            log.exception("Otwarcie Google Play dla opinii testowej")

        self._show_message(self._translate("feedback_google_play_unavailable"))
        return False

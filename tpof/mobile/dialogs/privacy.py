"""Privacy and telemetry dialogs isolated from the mobile application shell."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class PrivacyDialogWidgets:
    """Factories used to build KivyMD dialogs, injectable for unit tests."""

    dialog: Callable[..., Any]
    flat_button: Callable[..., Any]
    raised_button: Callable[..., Any]


class PrivacyDialogController:
    """Owns Firebase telemetry consent and Google UMP privacy options."""

    def __init__(
        self,
        *,
        translate: Callable[..., str],
        is_android: bool,
        telemetry_available: Callable[[], bool],
        telemetry_has_preference: Callable[[], bool],
        telemetry_enabled: Callable[[], bool],
        set_telemetry_enabled: Callable[[bool], bool],
        privacy_options_required: Callable[[], bool],
        show_privacy_options_form: Callable[[], None],
        refresh_button: Callable[[], None],
        log_event: Callable[..., None],
        record_exception: Callable[[Exception, str], None],
        widgets: PrivacyDialogWidgets | None = None,
    ) -> None:
        self._translate = translate
        self._is_android = is_android
        self._telemetry_available = telemetry_available
        self._telemetry_has_preference = telemetry_has_preference
        self._telemetry_enabled = telemetry_enabled
        self._set_telemetry_enabled = set_telemetry_enabled
        self._privacy_options_required = privacy_options_required
        self._show_privacy_options_form = show_privacy_options_form
        self._refresh_button = refresh_button
        self._log_event = log_event
        self._record_exception = record_exception
        self._injected_widgets = widgets

        self._dialog: Any | None = None
        self._telemetry_dialog: Any | None = None

    @property
    def is_open(self) -> bool:
        return self._dialog is not None

    @property
    def is_telemetry_prompt_open(self) -> bool:
        return self._telemetry_dialog is not None

    def _widgets(self) -> PrivacyDialogWidgets:
        if self._injected_widgets is not None:
            return self._injected_widgets

        from kivymd.uix.button import MDFlatButton, MDRaisedButton
        from kivymd.uix.dialog import MDDialog

        return PrivacyDialogWidgets(
            dialog=MDDialog,
            flat_button=MDFlatButton,
            raised_button=MDRaisedButton,
        )

    def _ad_privacy_required(self) -> bool:
        if not self._is_android:
            return False
        try:
            return bool(self._privacy_options_required())
        except Exception:
            log.debug(
                "Nie udało się sprawdzić opcji prywatności",
                exc_info=True,
            )
            return False

    def options_available(self) -> bool:
        """Return whether the toolbar should expose any privacy setting."""

        if not self._is_android:
            return False
        return self._ad_privacy_required() or bool(self._telemetry_available())

    def prompt_telemetry_consent(self) -> bool:
        """Ask once for optional Firebase telemetry consent."""

        if (
            not self._is_android
            or not self._telemetry_available()
            or self._telemetry_has_preference()
        ):
            self._refresh_button()
            return False

        self.close_telemetry_prompt()
        try:
            widgets = self._widgets()
            self._telemetry_dialog = widgets.dialog(
                title=self._translate("telemetry_title"),
                text=self._translate("telemetry_text"),
                buttons=[
                    widgets.flat_button(
                        text=self._translate("telemetry_not_now"),
                        on_release=lambda *_: self.set_telemetry_consent(False),
                    ),
                    widgets.raised_button(
                        text=self._translate("telemetry_enable"),
                        on_release=lambda *_: self.set_telemetry_consent(True),
                    ),
                ],
            )
            self._telemetry_dialog.open()
            return True
        except Exception as exc:
            self._record_exception(exc, "open_telemetry_consent")
            log.exception("Nie udało się pokazać zgody Firebase")
            self.close_telemetry_prompt()
            return False

    def close_telemetry_prompt(self, *_args: object) -> None:
        if self._telemetry_dialog is not None:
            self._telemetry_dialog.dismiss()
        self._telemetry_dialog = None

    def set_telemetry_consent(self, enabled: bool) -> bool:
        changed = self._set_telemetry_enabled(enabled)
        self.close_telemetry_prompt()
        self._refresh_button()
        if enabled:
            self._log_event("telemetry_enabled")
        return changed

    def close(self, *_args: object) -> None:
        if self._dialog is not None:
            self._dialog.dismiss()
        self._dialog = None

    def open(self) -> bool:
        """Open combined Firebase telemetry and Google UMP settings."""

        if not self._is_android:
            return False

        self.close()
        try:
            analytics_available = bool(self._telemetry_available())
            ad_privacy_required = self._ad_privacy_required()
            if not analytics_available and not ad_privacy_required:
                self._refresh_button()
                return False

            enabled = bool(self._telemetry_enabled())
            widgets = self._widgets()
            buttons = []
            if analytics_available:
                buttons.append(
                    widgets.raised_button(
                        text=self._translate(
                            "telemetry_disable" if enabled else "telemetry_enable"
                        ),
                        on_release=lambda *_: self.change_telemetry(not enabled),
                    )
                )
            if ad_privacy_required:
                buttons.append(
                    widgets.flat_button(
                        text=self._translate("ad_privacy"),
                        on_release=lambda *_: self.open_ad_privacy_options(),
                    )
                )
            buttons.append(
                widgets.flat_button(
                    text=self._translate("close"),
                    on_release=self.close,
                )
            )
            self._dialog = widgets.dialog(
                title=self._translate("privacy_title"),
                text=self._translate("telemetry_on" if enabled else "telemetry_off"),
                buttons=buttons,
            )
            self._dialog.open()
            self._log_event("settings_opened", {"section": "privacy"})
            return True
        except Exception as exc:
            self._record_exception(exc, "open_privacy_options")
            log.exception("Ustawienia prywatności")
            self.close()
            return False

    def change_telemetry(self, enabled: bool) -> bool:
        changed = self._set_telemetry_enabled(enabled)
        self.close()
        self._refresh_button()
        if enabled:
            self._log_event("telemetry_enabled")
        return changed

    def open_ad_privacy_options(self) -> bool:
        self.close()
        if not self._is_android:
            return False
        try:
            self._show_privacy_options_form()
            return True
        except Exception as exc:
            self._record_exception(exc, "open_ad_privacy_options")
            log.exception("Formularz prywatności reklam")
            return False

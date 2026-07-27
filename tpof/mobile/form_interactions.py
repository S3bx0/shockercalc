"""Form hints, validation feedback, and keyboard-aware scrolling.

The controller has no Kivy imports. Framework widgets and scheduling functions
are injected by the mobile composition root, which keeps this behavior directly
unit-testable.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from typing import Any, Protocol

from tpof.mobile.constants import BRAND_ICE

log = logging.getLogger(__name__)

_HINTS_INACTIVE_COLOR = (0.93, 0.98, 1.0, 0.94)


class HintTextField(Protocol):
    error: bool
    helper_text: str
    helper_text_mode: str

    def bind(self, **kwargs: Callable[..., Any]) -> Any: ...


class HintsButton(Protocol):
    icon: str
    text_color: Any


class HintsChip(Protocol):
    def set_active(self, active: bool) -> None: ...


@dataclass(frozen=True)
class FormInteractionView:
    """Shell controls that expose the global hints state."""

    hints_button: HintsButton
    hints_chip: HintsChip

    @classmethod
    def from_shell(cls, shell: Any) -> FormInteractionView:
        return cls(
            hints_button=shell.btn_hints,
            hints_chip=shell.btn_hints_chip,
        )


class FormInteractionController:
    """Coordinates shared form behavior without owning application widgets."""

    def __init__(
        self,
        *,
        hints_enabled: bool,
        set_hints_enabled: Callable[[bool], None],
        translate: Callable[[str], str],
        get_hint_field_items: Callable[[], Iterable[tuple[HintTextField | None, str]]],
        refresh_freezing_texts: Callable[[], None],
        apply_responsive_layout: Callable[[], None],
        show_message: Callable[[str], None],
        log_event: Callable[[str, Mapping[str, object] | None], None],
        schedule_once: Callable[[Callable[..., Any], float], Any],
        dp: Callable[[float], float],
    ) -> None:
        self._hints_enabled = hints_enabled
        self._set_hints_enabled = set_hints_enabled
        self._translate = translate
        self._get_hint_field_items = get_hint_field_items
        self._refresh_freezing_texts = refresh_freezing_texts
        self._apply_responsive_layout = apply_responsive_layout
        self._show_message = show_message
        self._log_event = log_event
        self._schedule_once = schedule_once
        self._dp = dp
        self._validation_bound_fields: set[int] = set()
        self._view: FormInteractionView | None = None

    @property
    def hints_enabled(self) -> bool:
        return self._hints_enabled

    def attach(self, view: FormInteractionView) -> None:
        self._view = view

    def toggle(self) -> None:
        self._hints_enabled = not self._hints_enabled
        self._set_hints_enabled(self._hints_enabled)
        self.apply()
        self._apply_responsive_layout()
        message_key = "hints_on" if self._hints_enabled else "hints_off"
        self._show_message(self._translate(message_key))
        self._log_event("hints_toggled", {"enabled": self._hints_enabled})

    def hint_field_items(self) -> tuple[tuple[HintTextField | None, str], ...]:
        return tuple(self._get_hint_field_items())

    def apply(self) -> None:
        if self._view is not None:
            self._view.hints_button.icon = (
                "lightbulb-on-outline" if self._hints_enabled else "lightbulb-off-outline"
            )
            self._view.hints_button.text_color = (
                BRAND_ICE if self._hints_enabled else _HINTS_INACTIVE_COLOR
            )
            self._view.hints_chip.set_active(self._hints_enabled)

        self._refresh_freezing_texts()
        for field, hint_key in self.hint_field_items():
            if field is None:
                continue
            field_id = id(field)
            if field_id not in self._validation_bound_fields:
                field.bind(text=lambda widget, _value: self.clear_field_error(widget))
                self._validation_bound_fields.add(field_id)
            if not getattr(field, "error", False):
                field.helper_text = self._translate(hint_key) if self._hints_enabled else ""
                # KivyMD 1.2.0 does not support helper_text_mode="none".
                field.helper_text_mode = "on_focus"

    def clear_field_error(self, field: HintTextField) -> None:
        if not getattr(field, "error", False):
            return
        field.error = False
        hint_key = next(
            (key for candidate, key in self.hint_field_items() if candidate is field),
            None,
        )
        field.helper_text = (
            self._translate(hint_key) if self._hints_enabled and hint_key is not None else ""
        )
        field.helper_text_mode = "on_focus"

    def mark_field_error(
        self,
        field: HintTextField,
        message: str | None = None,
    ) -> None:
        field.error = True
        field.helper_text = message or self._translate("field_required")
        field.helper_text_mode = "on_error"

    def bind_keyboard_scroll(
        self,
        fields: Iterable[HintTextField | None],
        scroll: Any,
    ) -> None:
        if scroll is None:
            return
        for field in fields:
            if field is None:
                continue
            field.bind(
                focus=lambda widget, focused, _scroll=scroll: self._on_input_focus(
                    widget,
                    focused,
                    _scroll,
                )
            )

    def _on_input_focus(
        self,
        field: HintTextField,
        focused: bool,
        scroll: Any,
    ) -> None:
        if not focused or scroll is None:
            return
        self._schedule_once(
            lambda *_: self._scroll_input_into_view(field, scroll),
            0.08,
        )
        self._schedule_once(
            lambda *_: self._scroll_input_into_view(field, scroll),
            0.35,
        )

    def _scroll_input_into_view(
        self,
        field: HintTextField,
        scroll: Any,
    ) -> None:
        try:
            scroll.scroll_to(field, padding=self._dp(150), animate=True)
        except TypeError:
            try:
                scroll.scroll_to(field)
            except Exception:
                log.debug(
                    "Could not scroll focused field above keyboard.",
                    exc_info=True,
                )
        except Exception:
            log.debug(
                "Could not scroll focused field above keyboard.",
                exc_info=True,
            )

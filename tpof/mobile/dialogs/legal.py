"""Offline legal-document browser for the mobile application."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class LegalDocument:
    """A packaged legal document and the localization key for its title."""

    identifier: str
    title_key: str
    relative_path: str


LEGAL_DOCUMENTS = (
    LegalDocument("eula", "legal_eula", "EULA"),
    LegalDocument("source", "legal_source_license", "LICENSE"),
    LegalDocument("ai", "legal_ai_policy", "AI_USAGE_POLICY"),
    LegalDocument("third_party", "legal_third_party", "THIRD_PARTY_NOTICES"),
    LegalDocument("lgpl", "legal_lgpl", "legal/LGPL-3.0-only"),
    LegalDocument("gpl", "legal_gpl", "legal/GPL-3.0-only"),
)


def split_legal_text(text: str, max_chars: int = 2400) -> list[str]:
    """Split a long notice into render-safe labels while preserving paragraphs."""

    if max_chars < 200:
        raise ValueError("max_chars must be at least 200")
    paragraphs = text.replace("\r\n", "\n").strip().split("\n\n")
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        parts = [
            paragraph[index : index + max_chars]
            for index in range(0, len(paragraph), max_chars)
        ] or [""]
        for part in parts:
            candidate = f"{current}\n\n{part}" if current else part
            if current and len(candidate) > max_chars:
                chunks.append(current)
                current = part
            else:
                current = candidate
    if current:
        chunks.append(current)
    return chunks


class LegalDialogController:
    """Displays packaged terms and third-party notices without network access."""

    def __init__(
        self,
        *,
        translate: Callable[..., str],
        project_root: Path,
    ) -> None:
        self._translate = translate
        self._project_root = project_root.resolve()
        self._dialog: Any | None = None

    @property
    def is_open(self) -> bool:
        return self._dialog is not None

    @property
    def documents(self) -> tuple[LegalDocument, ...]:
        return LEGAL_DOCUMENTS

    def close(self, *_args) -> None:
        if self._dialog is not None:
            self._dialog.dismiss()
        self._dialog = None

    def read_document(self, identifier: str) -> str:
        document = next(
            (item for item in self.documents if item.identifier == identifier),
            None,
        )
        if document is None:
            raise KeyError(identifier)
        path = (self._project_root / document.relative_path).resolve()
        if not path.is_relative_to(self._project_root):
            raise ValueError("Legal document escapes the application root")
        return path.read_text(encoding="utf-8")

    def open(self) -> bool:
        """Open the legal-document index."""

        self.close()
        try:
            from kivy.core.window import Window
            from kivy.metrics import dp
            from kivymd.uix.boxlayout import MDBoxLayout
            from kivymd.uix.button import MDFlatButton, MDRaisedButton
            from kivymd.uix.dialog import MDDialog
            from kivymd.uix.label import MDLabel
            from kivymd.uix.scrollview import MDScrollView

            content = MDBoxLayout(
                orientation="vertical",
                spacing=dp(8),
                padding=[0, dp(4), 0, dp(4)],
                size_hint_y=None,
            )
            content.bind(minimum_height=content.setter("height"))
            content.add_widget(
                MDLabel(
                    text=self._translate("legal_intro"),
                    theme_text_color="Hint",
                    font_style="Caption",
                    adaptive_height=True,
                )
            )
            for document in self.documents:
                button = MDRaisedButton(
                    text=self._translate(document.title_key),
                    size_hint=(1, None),
                    height=dp(46),
                    on_release=lambda _button, selected=document.identifier: (
                        self.open_document(selected)
                    ),
                )
                content.add_widget(button)

            scroll = MDScrollView(
                size_hint=(1, None),
                height=max(dp(300), min(dp(560), Window.height * 0.68)),
                do_scroll_x=False,
            )
            scroll.add_widget(content)
            self._dialog = MDDialog(
                title=self._translate("legal_title"),
                type="custom",
                content_cls=scroll,
                buttons=[
                    MDFlatButton(
                        text=self._translate("close"),
                        on_release=self.close,
                    )
                ],
            )
            self._dialog.open()
            return True
        except Exception:
            log.exception("Legal information dialog")
            self.close()
            return False

    def open_document(self, identifier: str) -> bool:
        """Open one legal document from the offline package."""

        document = next(
            (item for item in self.documents if item.identifier == identifier),
            None,
        )
        if document is None:
            return False
        try:
            text = self.read_document(identifier)
            from kivy.core.window import Window
            from kivy.metrics import dp
            from kivymd.uix.boxlayout import MDBoxLayout
            from kivymd.uix.button import MDFlatButton
            from kivymd.uix.dialog import MDDialog
            from kivymd.uix.label import MDLabel
            from kivymd.uix.scrollview import MDScrollView

            self.close()
            content = MDBoxLayout(
                orientation="vertical",
                spacing=dp(8),
                padding=[0, dp(4), dp(4), dp(8)],
                size_hint_y=None,
            )
            content.bind(minimum_height=content.setter("height"))
            for chunk in split_legal_text(text):
                label = MDLabel(
                    text=chunk,
                    markup=False,
                    theme_text_color="Primary",
                    font_style="Caption",
                    size_hint_y=None,
                )
                label.bind(
                    width=lambda widget, width: setattr(
                        widget, "text_size", (width, None)
                    )
                )
                label.bind(
                    texture_size=lambda widget, size: setattr(
                        widget, "height", size[1] + dp(10)
                    )
                )
                content.add_widget(label)

            scroll = MDScrollView(
                size_hint=(1, None),
                height=max(dp(320), min(dp(590), Window.height * 0.72)),
                do_scroll_x=False,
            )
            scroll.add_widget(content)
            self._dialog = MDDialog(
                title=self._translate(document.title_key),
                type="custom",
                content_cls=scroll,
                buttons=[
                    MDFlatButton(
                        text=self._translate("legal_back"),
                        on_release=lambda *_: self.open(),
                    ),
                    MDFlatButton(
                        text=self._translate("close"),
                        on_release=self.close,
                    ),
                ],
            )
            self._dialog.open()
            return True
        except Exception:
            log.exception("Legal document dialog: %s", identifier)
            self.close()
            return False

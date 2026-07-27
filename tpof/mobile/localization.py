"""Application language state and coordinated mobile text refresh.

This module has no Kivy imports. The composition root injects widget references
and refresh callbacks, so language switching can be tested without the mobile
framework.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

from tpof import __version__
from tpof.mobile.constants import APP_NAME
from tpof.mobile.i18n import display_category, translate

_FOOTER_AUTHOR = "Sebastian Milczarek"


class TextWidget(Protocol):
    text: str


class ThemeButton(Protocol):
    icon: str


class NavigationTab(Protocol):
    def set_text(self, text: str) -> None: ...


@dataclass(frozen=True)
class LocalizationView:
    """Shell widgets whose text follows the selected language."""

    toolbar_title: TextWidget
    theme_button: ThemeButton
    ad_label: TextWidget
    footer_label: TextWidget
    nav_tabs: dict[str, NavigationTab]

    @classmethod
    def from_shell(cls, shell: Any) -> LocalizationView:
        return cls(
            toolbar_title=shell.lbl_toolbar_title,
            theme_button=shell.btn_theme,
            ad_label=shell.ad_label,
            footer_label=shell.footer_label,
            nav_tabs={
                "freezing": shell.bottom_freezing_tab,
                "valves": shell.bottom_valves_tab,
                "labor": shell.bottom_labor_tab,
            },
        )


class LocalizationController:
    """Owns language state and refreshes all localized mobile surfaces."""

    def __init__(
        self,
        *,
        initial_language: str,
        is_android: bool,
        is_dark: Callable[[], bool],
        is_pro_no_ads: Callable[[], bool],
        is_trial_active: Callable[[], bool],
        trial_days_left: Callable[[], int],
        close_product_dialog: Callable[[], None],
        refresh_settings_ui: Callable[[], None],
        refresh_callbacks: tuple[Callable[[], None], ...],
    ) -> None:
        self._language = "en" if initial_language == "en" else "pl"
        self._is_android = is_android
        self._is_dark = is_dark
        self._is_pro_no_ads = is_pro_no_ads
        self._is_trial_active = is_trial_active
        self._trial_days_left = trial_days_left
        self._close_product_dialog = close_product_dialog
        self._refresh_settings_ui = refresh_settings_ui
        self._refresh_callbacks = refresh_callbacks
        self._view: LocalizationView | None = None

    @property
    def language(self) -> str:
        return self._language

    def attach(self, view: LocalizationView) -> None:
        self._view = view

    def translate(self, key: str, **kwargs: Any) -> str:
        return translate(self._language, key, **kwargs)

    def display_category(self, category: str | None) -> str:
        return display_category(self._language, category)

    def ad_label_text(self) -> str:
        if self._is_pro_no_ads():
            return self.translate("pro_ads_off")
        key = "ad" if self._is_android else "ad_placeholder"
        return self.translate(key)

    def footer_text(self) -> str:
        base = f"{APP_NAME} v{__version__}  |  {_FOOTER_AUTHOR}"
        if self._is_pro_no_ads():
            return f"{base}\n{self.translate('pro_unlocked_footer')}"
        if self._is_trial_active():
            days = self._trial_days_left()
            if days <= 1:
                return f"{base}\n{self.translate('trial_last_day')}"
            return f"{base}\n{self.translate('trial_active', days=days)}"
        return f"{base}\n{self.translate('trial_expired')}"

    def toggle(self) -> None:
        self._close_product_dialog()
        self._language = "en" if self._language == "pl" else "pl"
        self.refresh()
        self._refresh_settings_ui()

    def refresh(self) -> None:
        if self._view is not None:
            self._view.toolbar_title.text = "Refrigeration\nCalc"
            self._view.theme_button.icon = "weather-night" if self._is_dark() else "weather-sunny"
            self._view.ad_label.text = self.ad_label_text()
            self._view.footer_label.text = self.footer_text()
            self._view.nav_tabs["freezing"].set_text(self.translate("nav_freezing"))
            self._view.nav_tabs["valves"].set_text(self.translate("nav_valves"))
            self._view.nav_tabs["labor"].set_text(self.translate("nav_labor"))

        for callback in self._refresh_callbacks:
            callback()

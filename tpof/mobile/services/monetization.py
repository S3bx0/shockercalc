"""PRO subscription state and purchase orchestration for the mobile UI.

This module intentionally has no Kivy or PyJNIus imports. The application
provides the platform bridge, scheduler and view-update callbacks.
"""
from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Protocol

log = logging.getLogger(__name__)


class AndroidBillingActivity(Protocol):
    """Narrow PyJNIus contract used by the PRO controller."""

    def isProNoAdsActive(self) -> bool: ...

    def getProFormattedPrice(self) -> str: ...

    def launchProPurchase(self) -> None: ...


class ProMonetizationController:
    """Owns PRO status, localized Play price and purchase refresh timing."""

    INITIAL_REFRESH_DELAYS = (0.8, 3.0, 8.0)
    PURCHASE_REFRESH_DELAYS = (1.0, 4.0, 10.0)

    def __init__(
        self,
        *,
        is_android: bool,
        translate: Callable[..., str],
        get_android_activity: Callable[[], AndroidBillingActivity],
        schedule_once: Callable[[Callable[..., None], float], object],
        on_state_changed: Callable[[bool, str], None],
        refresh_ad_slot_height: Callable[[], None],
        show_message: Callable[[str], None],
        log_event: Callable[..., None],
        record_exception: Callable[..., None],
    ) -> None:
        self._is_android = is_android
        self._translate = translate
        self._get_android_activity = get_android_activity
        self._schedule_once = schedule_once
        self._on_state_changed = on_state_changed
        self._refresh_ad_slot_height = refresh_ad_slot_height
        self._show_message = show_message
        self._log_event = log_event
        self._record_exception = record_exception
        self._active = False
        self._thanks_shown = False
        self._formatted_price = ""

    @property
    def active(self) -> bool:
        return self._active

    @property
    def formatted_price(self) -> str:
        return self._formatted_price

    def button_text(self) -> str:
        """Return active, dynamic-price or localized fallback button text."""
        if self._active:
            return self._translate("pro_active")
        if self._formatted_price:
            return self._translate(
                "pro_button_price",
                price=self._formatted_price,
            )
        return self._translate("pro_button")

    def refresh_label(self) -> None:
        """Re-render the current state, for example after language changes."""
        self._on_state_changed(self._active, self.button_text())

    def start(self) -> None:
        """Schedule initial reads while Google Play Billing connects."""
        for delay in self.INITIAL_REFRESH_DELAYS:
            self._schedule_once(
                lambda *_args: self.refresh(),
                delay,
            )

    def refresh(self, announce: bool = False) -> None:
        """Read subscription state and the current localized Play price."""
        if not self._is_android:
            self._active = False
            self.refresh_label()
            return

        try:
            activity = self._get_android_activity()
            was_active = self._active
            active = bool(activity.isProNoAdsActive())
            try:
                formatted_price = str(activity.getProFormattedPrice() or "").strip()
            except Exception:  # pragma: no cover - legacy Android bridge only
                formatted_price = ""
                log.debug("Nie udało się odczytać ceny PRO", exc_info=True)
            if formatted_price:
                self._formatted_price = formatted_price
            self._active = active
            self.refresh_label()
            self._refresh_ad_slot_height()
            if announce and active and not was_active and not self._thanks_shown:
                self._thanks_shown = True
                self._show_message(self._translate("pro_thanks"))
        except Exception:  # pragma: no cover - Android only
            log.debug("Nie udało się odczytać statusu PRO", exc_info=True)

    def buy(self) -> None:
        """Launch Google Play Billing and schedule entitlement refreshes."""
        if self._active:
            return
        if not self._is_android:
            self._show_message(self._translate("pro_google_play_only"))
            return
        try:
            self._log_event("pro_purchase_started")
            self._get_android_activity().launchProPurchase()
            for delay in self.PURCHASE_REFRESH_DELAYS:
                self._schedule_once(
                    lambda *_args: self.refresh(announce=True),
                    delay,
                )
        except Exception as exc:  # pragma: no cover - Android only
            self._record_exception(exc, "buy_pro")
            log.exception("Zakup PRO")
            self._show_message(self._translate("pro_unavailable"))

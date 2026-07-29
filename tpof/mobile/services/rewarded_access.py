"""Rewarded-ad tokens and paid-module access orchestration.

The controller intentionally has no Kivy or PyJNIus imports. The application
injects the Android bridge, scheduler and the small UI callbacks it needs.
"""
from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from typing import Protocol

from tpof.mobile.entitlements import (
    FREE_PRODUCTS_PER_CATEGORY,
    MODULE_VALVES,
    Entitlements,
)
from tpof.mobile.services.entitlements_ui import _sync_module_ownership

log = logging.getLogger(__name__)


class AndroidRewardedAccessActivity(Protocol):
    """Narrow native bridge contract used by the access controller."""

    def consumePendingRewardTokens(self) -> int: ...

    def isRewardedAdReady(self) -> bool: ...

    def showRewardedAd(self) -> None: ...

    def isModuleValvesOwned(self) -> bool: ...

    def launchModulePurchase(self) -> None: ...


class RewardedAccessController:
    """Own rewarded tokens and access to products and the valves module."""

    PURCHASE_REFRESH_DELAYS = (1.0, 4.0, 10.0)
    REWARD_REFRESH_DELAYS = (1.0, 3.0)

    def __init__(
        self,
        *,
        is_android: bool,
        entitlements: Entitlements,
        translate: Callable[..., str],
        get_pro_no_ads: Callable[[], bool],
        get_products: Callable[[str], Sequence[str]],
        get_android_activity: Callable[[], AndroidRewardedAccessActivity],
        schedule_once: Callable[[Callable[..., None], float], object],
        refresh_valve_lock_view: Callable[[bool], None],
        show_message: Callable[[str], None],
    ) -> None:
        self._is_android = is_android
        self._entitlements = entitlements
        self._translate = translate
        self._get_pro_no_ads = get_pro_no_ads
        self._get_products = get_products
        self._get_android_activity = get_android_activity
        self._schedule_once = schedule_once
        self._refresh_valve_lock_view = refresh_valve_lock_view
        self._show_message = show_message

    def valve_module_available(self) -> bool:
        """Allow a valves calculation through ownership or one reward token."""
        self.refresh_module_valves_status()
        pro = self._get_pro_no_ads()
        if self._entitlements.has_module(MODULE_VALVES, pro):
            return True
        self.credit_pending_reward_tokens()
        if self._entitlements.try_unlock_module_with_token(MODULE_VALVES, pro):
            return True
        self._show_message(self._translate("valve_locked_hint"))
        return False

    def ensure_product_access(self, category: str, product_name: str) -> bool:
        """Allow a locked refrigeration product through one reward token."""
        pro = self._get_pro_no_ads()
        if self._entitlements.is_unlocked(pro):
            return True
        products = self._get_products(category)
        try:
            index = products.index(product_name)
        except ValueError:
            index = FREE_PRODUCTS_PER_CATEGORY
        if self._entitlements.is_product_allowed(index, pro):
            return True
        self.credit_pending_reward_tokens()
        if self._entitlements.try_unlock_product_with_token(index, pro):
            return True
        self.offer_reward_ad()
        return False

    def refresh_module_valves_status(self) -> None:
        """Synchronize the locally cached module state with Google Play."""
        if not self._is_android:
            return
        try:
            owned = bool(self._get_android_activity().isModuleValvesOwned())
        except Exception:  # pragma: no cover - Android only
            log.debug("Nie udało się odczytać statusu modułu zaworów", exc_info=True)
            return
        _sync_module_ownership(self._entitlements, MODULE_VALVES, owned)

    def refresh_valve_lock_ui(self) -> None:
        """Refresh ownership and show or hide the module lock card."""
        self.refresh_module_valves_status()
        locked = not self._entitlements.has_module(
            MODULE_VALVES,
            self._get_pro_no_ads(),
        )
        self._refresh_valve_lock_view(locked)

    def buy_valve_module(self) -> None:
        """Launch the one-time module purchase and schedule ownership reads."""
        if self._entitlements.has_module(MODULE_VALVES, self._get_pro_no_ads()):
            return
        if not self._is_android:
            self._show_message(self._translate("pro_google_play_only"))
            return
        try:
            self._get_android_activity().launchModulePurchase()
            for delay in self.PURCHASE_REFRESH_DELAYS:
                self._schedule_once(
                    lambda *_args: self._after_valve_purchase(),
                    delay,
                )
        except Exception:  # pragma: no cover - Android only
            log.exception("Zakup modułu zaworów")
            self._show_message(self._translate("valve_purchase_unavailable"))

    def credit_pending_reward_tokens(self) -> int:
        """Transfer completed rewarded-ad callbacks from Android to local state."""
        if not self._is_android:
            return 0
        try:
            pending = int(
                self._get_android_activity().consumePendingRewardTokens()
            )
        except Exception:  # pragma: no cover - Android only
            log.debug("Nie udało się odczytać tokenów reward", exc_info=True)
            return 0
        granted = 0
        for _ in range(max(0, pending)):
            granted += int(self._entitlements.grant_reward_for_ad())
        return granted

    def offer_reward_ad(self) -> None:
        """Offer one rewarded ad in exchange for one calculation token."""
        if not self._is_android:
            self._show_message(self._translate("product_locked"))
            return
        if not self._entitlements.can_watch_ad():
            self._show_message(self._translate("ad_limit_reached"))
            return
        try:
            activity = self._get_android_activity()
            if not bool(activity.isRewardedAdReady()):
                self._show_message(self._translate("ad_not_ready"))
                return
            activity.showRewardedAd()
            self._show_message(self._translate("watch_ad_for_token"))
            self._schedule_once(
                self._credit_pending_reward_tokens_after_delay,
                self.REWARD_REFRESH_DELAYS[0],
            )
            self._schedule_once(
                lambda *_args: self._after_reward_ad(),
                self.REWARD_REFRESH_DELAYS[1],
            )
        except Exception:  # pragma: no cover - Android only
            log.exception("Reklama rewarded")
            self._show_message(self._translate("pro_unavailable"))

    def _credit_pending_reward_tokens_after_delay(self, *_args: object) -> None:
        self.credit_pending_reward_tokens()

    def _after_valve_purchase(self) -> None:
        was_locked = not self._entitlements.has_module(
            MODULE_VALVES,
            self._get_pro_no_ads(),
        )
        self.refresh_module_valves_status()
        self.refresh_valve_lock_ui()
        if was_locked and self._entitlements.has_module(
            MODULE_VALVES,
            self._get_pro_no_ads(),
        ):
            self._show_message(self._translate("valve_unlocked_thanks"))

    def _after_reward_ad(self) -> None:
        self.credit_pending_reward_tokens()
        if self._entitlements.reward_tokens() > 0:
            self._show_message(self._translate("ad_thanks"))
        self.refresh_valve_lock_ui()

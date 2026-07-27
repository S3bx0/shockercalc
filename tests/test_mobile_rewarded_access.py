from __future__ import annotations

from pathlib import Path

from tpof.mobile.entitlements import (
    MODULE_VALVES,
    REWARD_DAILY_AD_CAP,
    Entitlements,
)
from tpof.mobile.services.rewarded_access import RewardedAccessController

ROOT = Path(__file__).resolve().parents[1]


class FakeClock:
    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now


class FakeRewardedAccessActivity:
    def __init__(self) -> None:
        self.pending_tokens = 0
        self.reward_ready = True
        self.module_owned = False
        self.reward_shows = 0
        self.purchase_launches = 0

    def consumePendingRewardTokens(self) -> int:
        pending = self.pending_tokens
        self.pending_tokens = 0
        return pending

    def isRewardedAdReady(self) -> bool:
        return self.reward_ready

    def showRewardedAd(self) -> None:
        self.reward_shows += 1

    def isModuleValvesOwned(self) -> bool:
        return self.module_owned

    def launchModulePurchase(self) -> None:
        self.purchase_launches += 1


def _translate(key: str, **_kwargs) -> str:
    return {
        "valve_locked_hint": "Zawory zablokowane.",
        "product_locked": "Produkt zablokowany.",
        "ad_limit_reached": "Limit reklam.",
        "ad_not_ready": "Reklama niegotowa.",
        "watch_ad_for_token": "Obejrzyj reklamę.",
        "pro_unavailable": "Usługa niedostępna.",
        "pro_google_play_only": "Tylko Google Play.",
        "valve_purchase_unavailable": "Zakup niedostępny.",
        "valve_unlocked_thanks": "Moduł odblokowany.",
        "ad_thanks": "Token przyznany.",
    }[key]


def _controller(
    tmp_path: Path,
    *,
    is_android: bool = True,
    pro_state: list[bool] | None = None,
):
    clock = FakeClock()
    entitlements = Entitlements(tmp_path / "entitlements.json", clock=clock)
    entitlements.ensure_started()
    clock.now += 2 * 24 * 60 * 60
    activity = FakeRewardedAccessActivity()
    messages: list[str] = []
    scheduled: list[tuple[object, float]] = []
    lock_states: list[bool] = []
    current_pro = pro_state if pro_state is not None else [False]
    controller = RewardedAccessController(
        is_android=is_android,
        entitlements=entitlements,
        translate=_translate,
        get_pro_no_ads=lambda: current_pro[0],
        get_products=lambda category: {
            "Mięso": ["Wołowina", "Wieprzowina"],
        }.get(category, []),
        get_android_activity=lambda: activity,
        schedule_once=lambda callback, delay: scheduled.append((callback, delay)),
        refresh_valve_lock_view=lock_states.append,
        show_message=messages.append,
    )
    return (
        controller,
        entitlements,
        activity,
        clock,
        messages,
        scheduled,
        lock_states,
    )


def test_free_product_does_not_consume_or_offer_reward(tmp_path):
    controller, entitlements, activity, _clock, messages, scheduled, _locks = (
        _controller(tmp_path)
    )

    assert controller.ensure_product_access("Mięso", "Wołowina") is True
    assert entitlements.reward_tokens() == 0
    assert activity.reward_shows == 0
    assert messages == []
    assert scheduled == []


def test_locked_product_uses_pending_android_reward_token(tmp_path):
    controller, entitlements, activity, *_rest = _controller(tmp_path)
    activity.pending_tokens = 1

    assert controller.ensure_product_access("Mięso", "Wieprzowina") is True
    assert entitlements.reward_tokens() == 0
    assert activity.pending_tokens == 0


def test_locked_product_off_android_shows_local_lock_message(tmp_path):
    controller, _entitlements, activity, _clock, messages, scheduled, _locks = (
        _controller(tmp_path, is_android=False)
    )

    assert controller.ensure_product_access("Mięso", "Wieprzowina") is False
    assert messages == ["Produkt zablokowany."]
    assert activity.reward_shows == 0
    assert scheduled == []


def test_valves_calculation_uses_one_pending_token(tmp_path):
    controller, entitlements, activity, _clock, messages, _scheduled, _locks = (
        _controller(tmp_path)
    )
    activity.pending_tokens = 1

    assert controller.valve_module_available() is True
    assert entitlements.reward_tokens() == 0
    assert messages == []

    assert controller.valve_module_available() is False
    assert messages == ["Zawory zablokowane."]


def test_refresh_syncs_owned_valves_module_and_lock_view(tmp_path):
    controller, entitlements, activity, _clock, _messages, _scheduled, locks = (
        _controller(tmp_path)
    )
    activity.module_owned = True

    controller.refresh_valve_lock_ui()

    assert entitlements.has_module(MODULE_VALVES, pro=False) is True
    assert locks == [False]


def test_rewarded_ad_schedules_token_transfer_and_ui_refresh(tmp_path):
    controller, entitlements, activity, _clock, messages, scheduled, locks = (
        _controller(tmp_path)
    )

    controller.offer_reward_ad()

    assert activity.reward_shows == 1
    assert messages == ["Obejrzyj reklamę."]
    assert [delay for _callback, delay in scheduled] == [1.0, 3.0]

    activity.pending_tokens = 1
    first_callback = scheduled[0][0]
    second_callback = scheduled[1][0]
    assert callable(first_callback)
    assert callable(second_callback)
    first_callback()
    second_callback()

    assert entitlements.reward_tokens() == 1
    assert messages == ["Obejrzyj reklamę.", "Token przyznany."]
    assert locks == [True]


def test_rewarded_ad_handles_not_ready_and_daily_limit(tmp_path):
    controller, entitlements, activity, _clock, messages, scheduled, _locks = (
        _controller(tmp_path)
    )
    activity.reward_ready = False

    controller.offer_reward_ad()

    assert messages == ["Reklama niegotowa."]
    assert scheduled == []

    activity.reward_ready = True
    for _ in range(REWARD_DAILY_AD_CAP):
        assert entitlements.grant_reward_for_ad() is True
    controller.offer_reward_ad()

    assert messages[-1] == "Limit reklam."
    assert activity.reward_shows == 0


def test_valves_purchase_refreshes_ownership_and_announces_once(tmp_path):
    controller, entitlements, activity, _clock, messages, scheduled, locks = (
        _controller(tmp_path)
    )

    controller.buy_valve_module()

    assert activity.purchase_launches == 1
    assert [delay for _callback, delay in scheduled] == [1.0, 4.0, 10.0]
    activity.module_owned = True
    callback = scheduled[0][0]
    assert callable(callback)
    callback()

    assert entitlements.has_module(MODULE_VALVES, pro=False) is True
    assert locks == [False]
    assert messages == ["Moduł odblokowany."]

    second_callback = scheduled[1][0]
    assert callable(second_callback)
    second_callback()
    assert messages == ["Moduł odblokowany."]


def test_valves_purchase_off_android_uses_google_play_message(tmp_path):
    controller, _entitlements, activity, _clock, messages, scheduled, _locks = (
        _controller(tmp_path, is_android=False)
    )

    controller.buy_valve_module()

    assert messages == ["Tylko Google Play."]
    assert activity.purchase_launches == 0
    assert scheduled == []


def test_pro_access_bypasses_product_and_module_tokens(tmp_path):
    pro_state = [True]
    controller, entitlements, _activity, _clock, messages, _scheduled, _locks = (
        _controller(tmp_path, pro_state=pro_state)
    )

    assert controller.ensure_product_access("Mięso", "Wieprzowina") is True
    assert controller.valve_module_available() is True
    assert entitlements.reward_tokens() == 0
    assert messages == []


def test_app_delegates_rewarded_access_orchestration_to_controller():
    app_source = (ROOT / "tpof" / "mobile" / "app.py").read_text(encoding="utf-8")
    controller_source = (
        ROOT / "tpof" / "mobile" / "services" / "rewarded_access.py"
    ).read_text(encoding="utf-8")

    assert "RewardedAccessController" in app_source
    assert "self._rewarded_access = RewardedAccessController(" in app_source
    assert "can_calculate=self._rewarded_access.valve_module_available" in app_source
    assert "on_watch=self._rewarded_access.offer_reward_ad" in app_source
    assert (
        "ensure_product_access=self._rewarded_access.ensure_product_access"
        in app_source
    )
    assert "class RewardedAccessController" in controller_source
    assert "def _credit_pending_reward_tokens" not in app_source
    assert "def _offer_reward_ad" not in app_source
    assert "def _buy_valve_module" not in app_source
    assert "def _ensure_freezing_product_access" not in app_source

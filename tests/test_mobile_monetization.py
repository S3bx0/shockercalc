from __future__ import annotations

from pathlib import Path

from tpof.mobile.services.monetization import ProMonetizationController

ROOT = Path(__file__).resolve().parents[1]


class FakeBillingActivity:
    def __init__(self, *, active: bool = False, price: str = "") -> None:
        self.active = active
        self.price = price
        self.purchase_launches = 0

    def isProNoAdsActive(self) -> bool:
        return self.active

    def getProFormattedPrice(self) -> str:
        return self.price

    def launchProPurchase(self) -> None:
        self.purchase_launches += 1


def _translate(key: str, **kwargs) -> str:
    texts = {
        "pro_active": "PRO",
        "pro_button": "PRO 9,99 zł/mies.",
        "pro_button_price": "PRO {price}/mies.",
        "pro_thanks": "Dziękujemy za PRO.",
        "pro_google_play_only": "Tylko Google Play.",
        "pro_unavailable": "PRO niedostępne.",
    }
    text = texts[key]
    return text.format(**kwargs) if kwargs else text


def _controller(
    activity: FakeBillingActivity,
    *,
    is_android: bool = True,
):
    states: list[tuple[bool, str]] = []
    messages: list[str] = []
    scheduled: list[tuple[object, float]] = []
    events: list[str] = []
    exceptions: list[tuple[BaseException, str]] = []
    ad_refreshes: list[bool] = []

    controller = ProMonetizationController(
        is_android=is_android,
        translate=_translate,
        get_android_activity=lambda: activity,
        schedule_once=lambda callback, delay: scheduled.append((callback, delay)),
        on_state_changed=lambda active, text: states.append((active, text)),
        refresh_ad_slot_height=lambda: ad_refreshes.append(True),
        show_message=messages.append,
        log_event=lambda name, *_args: events.append(name),
        record_exception=lambda exc, context: exceptions.append((exc, context)),
    )
    return (
        controller,
        states,
        messages,
        scheduled,
        events,
        exceptions,
        ad_refreshes,
    )


def test_controller_uses_fallback_until_google_play_returns_price():
    activity = FakeBillingActivity()
    controller, states, *_rest = _controller(activity)

    assert controller.button_text() == "PRO 9,99 zł/mies."

    controller.refresh()

    assert states[-1] == (False, "PRO 9,99 zł/mies.")


def test_controller_uses_localized_google_play_price():
    activity = FakeBillingActivity(price="9,99 zł")
    controller, states, *_rest = _controller(activity)

    controller.refresh()

    assert controller.formatted_price == "9,99 zł"
    assert controller.button_text() == "PRO 9,99 zł/mies."
    assert states[-1] == (False, "PRO 9,99 zł/mies.")


def test_controller_owns_initial_billing_refresh_schedule():
    activity = FakeBillingActivity()
    controller, _states, _messages, scheduled, *_rest = _controller(activity)

    controller.start()

    assert [delay for _callback, delay in scheduled] == [0.8, 3.0, 8.0]


def test_controller_launches_purchase_and_schedules_status_refreshes():
    activity = FakeBillingActivity(price="9,99 zł")
    (
        controller,
        _states,
        messages,
        scheduled,
        events,
        exceptions,
        _ad_refreshes,
    ) = _controller(activity)

    controller.buy()

    assert activity.purchase_launches == 1
    assert events == ["pro_purchase_started"]
    assert [delay for _callback, delay in scheduled] == [1.0, 4.0, 10.0]
    assert messages == []
    assert exceptions == []

    activity.active = True
    callback = scheduled[0][0]
    assert callable(callback)
    callback()
    callback()

    assert messages == ["Dziękujemy za PRO."]


def test_controller_reports_google_play_requirement_off_android():
    activity = FakeBillingActivity()
    controller, _states, messages, scheduled, *_rest = _controller(
        activity,
        is_android=False,
    )

    controller.buy()

    assert messages == ["Tylko Google Play."]
    assert activity.purchase_launches == 0
    assert scheduled == []


def test_main_delegates_pro_orchestration_to_controller():
    main_source = (ROOT / "tpof" / "mobile" / "main.py").read_text(encoding="utf-8")
    i18n_source = (ROOT / "tpof" / "mobile" / "i18n.py").read_text(encoding="utf-8")

    assert "ProMonetizationController" in main_source
    assert "self._monetization.start()" in main_source
    assert "self._monetization.buy()" in main_source
    assert "def _apply_pro_ui_state" in main_source
    assert "def _refresh_pro_status" not in main_source
    assert "def _set_pro_status" not in main_source
    assert "def _buy_pro" not in main_source
    assert '"pro_button": "PRO 9,99 zł/mies."' in i18n_source
    assert '"pro_button_price": "PRO {price}/mies."' in i18n_source

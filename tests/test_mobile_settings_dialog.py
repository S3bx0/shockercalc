from decimal import Decimal
from pathlib import Path

from tpof.mobile.currency import ExchangeRates
from tpof.mobile.dialogs.settings import SettingsDialogController


class _Widget:
    def __init__(self, name: str = "") -> None:
        self.name = name
        self.text = ""


def _controller(styles):
    def translate(key, **kwargs):
        if key == "settings_currency_rate_missing":
            return f"missing {kwargs['currency']}"
        return key

    return SettingsDialogController(
        translate=translate,
        style_button=lambda widget, variant: styles.append((widget.name, variant)),
        card_bg=lambda: (0, 0, 0, 1),
        get_display_currency=lambda: "EUR",
        get_exchange_rates=lambda: ExchangeRates(
            {"PLN": Decimal("1"), "EUR": Decimal("4.25")}
        ),
        get_language=lambda: "en",
        get_auto_update=lambda: True,
        get_status_text=lambda: "NBP status",
        on_set_unit_system=lambda _value: None,
        on_set_display_currency=lambda _value: None,
        on_toggle_auto_update=lambda: None,
        on_open_feedback=lambda: None,
        on_open_legal=lambda: None,
    )


def test_settings_controller_refreshes_view_from_injected_state():
    styles = []
    controller = _controller(styles)
    controller._currency_buttons = {
        "PLN": _Widget("PLN"),
        "EUR": _Widget("EUR"),
        "USD": _Widget("USD"),
    }
    controller._currency_rate_labels = {
        "PLN": _Widget(),
        "EUR": _Widget(),
        "USD": _Widget(),
    }
    controller._currency_auto_button = _Widget("auto")
    controller._currency_status = _Widget()

    controller.refresh()

    assert styles == [
        ("PLN", "muted"),
        ("EUR", "ice"),
        ("USD", "muted"),
        ("auto", "ice"),
    ]
    assert controller._currency_rate_labels["PLN"].text == "1 PLN = 1.0000 PLN"
    assert controller._currency_rate_labels["EUR"].text == "1 EUR = 4.2500 PLN"
    assert controller._currency_rate_labels["USD"].text == "missing USD"
    assert controller._currency_auto_button.text == "settings_currency_auto_on"
    assert controller._currency_status.text == "NBP status"


def test_settings_controller_close_releases_widget_references():
    styles = []
    controller = _controller(styles)
    dialog = _Widget()
    dialog.dismissed = False
    dialog.dismiss = lambda: setattr(dialog, "dismissed", True)
    controller._dialog = dialog
    controller._currency_buttons = {"PLN": _Widget()}

    controller.close()

    assert dialog.dismissed is True
    assert controller.is_open is False
    assert controller._currency_buttons == {}


def test_settings_controller_keeps_feedback_action_outside_dialog_logic():
    source = (
        Path(__file__).resolve().parents[1]
        / "tpof"
        / "mobile"
        / "dialogs"
        / "settings.py"
    ).read_text(encoding="utf-8")

    assert "on_open_feedback" in source
    assert 'self._translate("settings_feedback_button")' in source
    assert "openFeedbackEmail" not in source
    assert "mailto:" not in source


def test_settings_dialog_orders_sections_by_user_priority():
    source = (
        Path(__file__).resolve().parents[1]
        / "tpof"
        / "mobile"
        / "dialogs"
        / "settings.py"
    ).read_text(encoding="utf-8")

    feedback = source.index('text=self._translate("settings_feedback_title")')
    currency = source.index('text=self._translate("settings_currency_title")')
    units = source.index('text=self._translate("units_title")')
    legal = source.index('text=self._translate("settings_legal_title")')

    assert feedback < currency < units < legal

import sys
from decimal import Decimal
from pathlib import Path
from types import ModuleType, SimpleNamespace

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
        get_refresh_running=lambda: False,
        get_status_text=lambda: "NBP status",
        on_set_unit_system=lambda _value: None,
        on_set_display_currency=lambda _value: None,
        on_toggle_auto_update=lambda: None,
        on_refresh_rates=lambda: None,
        on_open_feedback=lambda: None,
        on_open_google_play_feedback=lambda: None,
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
    controller._currency_refresh_button = _Widget()

    controller.close()

    assert dialog.dismissed is True
    assert controller.is_open is False
    assert controller._currency_buttons == {}
    assert controller._currency_refresh_button is None


def test_settings_controller_keeps_feedback_action_outside_dialog_logic():
    source = (
        Path(__file__).resolve().parents[1]
        / "tpof"
        / "mobile"
        / "dialogs"
        / "settings.py"
    ).read_text(encoding="utf-8")

    assert "on_open_feedback" in source
    assert "on_open_google_play_feedback" in source
    assert 'self._translate("settings_feedback_button")' in source
    assert 'self._translate("settings_feedback_google_play_button")' in source
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


def test_manual_button_tracks_update_preference_and_active_request():
    controller = _controller([])
    button = _Widget()
    controller._currency_refresh_button = button
    controller.refresh()
    assert button.text == "settings_currency_refresh_now"
    assert button.disabled is False
    controller._get_refresh_running = lambda: True
    controller.refresh()
    assert button.disabled is True
    controller._get_refresh_running = lambda: False
    controller._get_auto_update = lambda: False
    controller.refresh()
    assert button.disabled is True
    controller._get_auto_update = lambda: True
    controller.refresh()
    assert button.disabled is False


def test_dialog_builds_and_wires_manual_refresh_with_adaptive_card(monkeypatch):
    widgets = []

    class View:
        def __init__(self, **kwargs):
            self.name = ""
            self.children = []
            self.bindings = {}
            self.__dict__.update(kwargs)
            widgets.append(self)

        def add_widget(self, child):
            self.children.append(child)

        def bind(self, **bindings):
            self.bindings.update(bindings)

        def setter(self, key):
            return lambda _widget, value: setattr(self, key, value)

        def open(self):
            self.opened = True

        def dismiss(self):
            self.opened = False

    modules = {
        "kivy.core.window": {"Window": SimpleNamespace(height=720)},
        "kivy.metrics": {"dp": lambda value: value},
        "kivymd.uix.boxlayout": {"MDBoxLayout": View},
        "kivymd.uix.button": {"MDFlatButton": View, "MDRaisedButton": View},
        "kivymd.uix.card": {"MDCard": View},
        "kivymd.uix.dialog": {"MDDialog": View},
        "kivymd.uix.label": {"MDLabel": View},
        "kivymd.uix.scrollview": {"MDScrollView": View},
    }
    for name, attributes in modules.items():
        module = ModuleType(name)
        module.__dict__.update(attributes)
        monkeypatch.setitem(sys.modules, name, module)

    controller = _controller([])
    calls = []
    controller._on_refresh_rates = lambda: calls.append("refresh")
    assert controller.open() is True
    button = controller._currency_refresh_button
    assert button.height >= 48 and button.size_hint == (1, None)
    button.on_release(button)
    assert calls == ["refresh"]
    card = next(widget for widget in widgets if button in widget.children)
    assert "minimum_height" in card.bindings
    card.bindings["minimum_height"](card, 420)
    assert card.height == 420
    controller.close()
    assert controller._currency_refresh_button is None

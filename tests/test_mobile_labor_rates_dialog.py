from tpof.mobile.dialogs.labor_rates import LaborRatesDialogController


class _Widget:
    def __init__(self, text: str = "") -> None:
        self.text = text
        self.dismissed = False

    def dismiss(self) -> None:
        self.dismissed = True


def _controller(state, *, save_values=None):
    def translate(key, **kwargs):
        if kwargs:
            return f"{key}:{next(iter(kwargs.values()))}"
        return key

    return LaborRatesDialogController(
        translate=translate,
        get_values=lambda: state["values"],
        save_values=save_values or (lambda values: state["saved"].append(dict(values))),
        reset_values=lambda: state["reset"].append(True),
        clear_field_error=lambda field: state["cleared"].append(field),
        mark_field_error=lambda field: state["marked"].append(field),
        numeric_input_filter=lambda value, _undo: value,
        invalidate_results=lambda: state["invalidated"].append(True),
        show_message=lambda message: state["messages"].append(message),
        on_opened=lambda: state["events"].append("opened"),
        on_saved=lambda: state["events"].append("saved"),
        on_reset=lambda: state["events"].append("reset"),
        report_exception=lambda exc, context: state["exceptions"].append((exc, context)),
    )


def _state():
    return {
        "values": {"labor_hourly_rate": "100", "hours_per_day": "8"},
        "saved": [],
        "reset": [],
        "cleared": [],
        "marked": [],
        "invalidated": [],
        "messages": [],
        "events": [],
        "exceptions": [],
    }


def test_labor_rates_controller_saves_and_releases_dialog_widgets():
    state = _state()
    controller = _controller(state)
    dialog = _Widget()
    fields = {
        "labor_hourly_rate": _Widget("125,50"),
        "hours_per_day": _Widget("8"),
    }
    controller._dialog = dialog
    controller._fields = fields

    assert controller.save() is True

    assert state["saved"] == [
        {"labor_hourly_rate": "125,50", "hours_per_day": "8"}
    ]
    assert state["invalidated"] == [True]
    assert state["messages"] == ["labor_rates_saved"]
    assert state["events"] == ["saved"]
    assert dialog.dismissed is True
    assert controller.is_open is False
    assert controller._fields == {}


def test_labor_rates_controller_marks_only_field_named_by_validation_error():
    state = _state()

    def reject(_values):
        raise ValueError("labor_hourly_rate must be positive")

    controller = _controller(state, save_values=reject)
    hourly_rate = _Widget("0")
    hours_per_day = _Widget("8")
    controller._dialog = _Widget()
    controller._fields = {
        "labor_hourly_rate": hourly_rate,
        "hours_per_day": hours_per_day,
    }

    assert controller.save() is False

    assert state["marked"] == [hourly_rate]
    assert state["invalidated"] == []
    assert state["messages"] == [
        "labor_rates_invalid:labor_hourly_rate must be positive"
    ]
    assert controller.is_open is True


def test_labor_rates_controller_resets_fields_from_persistent_defaults():
    state = _state()

    def reset_values():
        state["reset"].append(True)
        state["values"] = {"labor_hourly_rate": "95", "hours_per_day": "7.5"}

    controller = _controller(state)
    controller._reset_values = reset_values
    hourly_rate = _Widget("125")
    hours_per_day = _Widget("8")
    controller._fields = {
        "labor_hourly_rate": hourly_rate,
        "hours_per_day": hours_per_day,
    }

    controller.reset()

    assert state["reset"] == [True]
    assert hourly_rate.text == "95"
    assert hours_per_day.text == "7.5"
    assert state["cleared"] == [hourly_rate, hours_per_day]
    assert state["invalidated"] == [True]
    assert state["messages"] == ["labor_rates_reset"]
    assert state["events"] == ["reset"]

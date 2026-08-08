from tpof.mobile.tabs.valves import ValvesTabController, ValvesTabView


class _Widget:
    def __init__(self, text=""):
        self.text = text
        self.hint_text = ""
        self.height = 0
        self.opacity = 0
        self.disabled = False


def _view() -> ValvesTabView:
    return ValvesTabView(
        scroll=_Widget(),
        lock_card=_Widget(),
        locked_label=_Widget(),
        buy_button=_Widget(),
        watch_button=_Widget(),
        input_card=_Widget(),
        title_label=_Widget(),
        type_button=_Widget(),
        volume_mode_button=_Widget(),
        dimensions_mode_button=_Widget(),
        volume_box=_Widget(),
        volume_input=_Widget("100"),
        dimensions_box=_Widget(),
        length_input=_Widget("10"),
        width_input=_Widget("5"),
        height_input=_Widget("2"),
        temp_before_input=_Widget("20"),
        temp_after_input=_Widget("-30"),
        coolers_input=_Widget("2"),
        flow_input=_Widget("1.5"),
        calculate_button=_Widget(),
        result_card=_Widget(),
        result_title_label=_Widget(),
        count_label=_Widget(),
        delta_label=_Widget(),
        total_flow_label=_Widget(),
        flow_label=_Widget(),
        unit_flow_label=_Widget(),
    )


def _controller(*, access=True):
    state = {
        "messages": [],
        "events": [],
        "marked": [],
        "cleared": [],
        "styled": [],
        "exceptions": [],
        "access_denied": 0,
    }

    def translate(key, **kwargs):
        values = ",".join(
            f"{name}={value}" for name, value in sorted(kwargs.items())
        )
        return f"{key}({values})" if values else key

    def access_denied():
        state["access_denied"] += 1

    controller = ValvesTabController(
        translate=translate,
        card_bg=lambda: (0, 0, 0, 1),
        total_color=(0, 1, 0, 1),
        numeric_input_filter=lambda *_args: True,
        register_themed_card=lambda _card: None,
        bind_keyboard_scroll=lambda _fields, _scroll: None,
        style_button=lambda button, variant: state["styled"].append(
            (button, variant)
        ),
        clear_field_error=lambda field: state["cleared"].append(field),
        mark_field_error=lambda field, message=None: state["marked"].append(
            (field, message)
        ),
        show_message=state["messages"].append,
        log_event=lambda name, payload=None: state["events"].append(
            (name, payload or {})
        ),
        record_exception=lambda exc, context: state["exceptions"].append(
            (exc, context)
        ),
        can_calculate=lambda: access,
        on_access_denied=access_denied,
        on_buy=lambda: None,
        on_watch=lambda: None,
        menu_factory=lambda *_args: None,
        is_compact=lambda: False,
        menu_text_color=lambda: (1, 1, 1, 1),
    )
    controller.view = _view()
    return controller, state


def test_valves_tab_view_exposes_input_fields_in_keyboard_navigation_order():
    view = _view()

    assert view.input_fields == (
        view.volume_input,
        view.length_input,
        view.width_input,
        view.height_input,
        view.temp_before_input,
        view.temp_after_input,
        view.coolers_input,
        view.flow_input,
    )


def test_valves_controller_owns_volume_and_dimensions_mode_state():
    controller, state = _controller()
    view = controller.view
    assert view is not None

    controller.set_input_mode("K")

    assert controller.input_mode == "K"
    assert view.volume_box.height == 60
    assert view.volume_box.opacity == 1
    assert view.volume_box.disabled is False
    assert view.dimensions_box.height == 0
    assert view.dimensions_box.disabled is True
    assert state["styled"][-2:] == [
        (view.volume_mode_button, "ice"),
        (view.dimensions_mode_button, "muted"),
    ]

    controller.set_input_mode("W")

    assert controller.input_mode == "W"
    assert view.volume_box.height == 0
    assert view.volume_box.disabled is True
    assert view.dimensions_box.height == 180
    assert view.dimensions_box.opacity == 1
    assert view.dimensions_box.disabled is False
    assert state["styled"][-2:] == [
        (view.volume_mode_button, "muted"),
        (view.dimensions_mode_button, "ice"),
    ]


def test_valves_controller_calculates_from_direct_volume_and_renders_result():
    controller, state = _controller()
    view = controller.view
    assert view is not None

    assert controller.calculate() is True

    result = controller.last_results
    assert result is not None
    assert result.delta_T == 0.025
    assert result.Q == 9.15
    assert result.ilosc_zaworow == 1
    assert controller.last_total_flow == 3.0
    assert view.count_label.text == "valve_count(value=1)"
    assert view.delta_label.text == "valve_delta_t(value=0.03)"
    assert view.total_flow_label.text == "valve_total_flow(value=3.0)"
    assert view.flow_label.text == "valve_flow(value=9.2)"
    assert [name for name, _payload in state["events"]] == [
        "calculation_started",
        "calculation_finished",
    ]


def test_valves_controller_calculates_volume_from_dimensions():
    controller, _state = _controller()
    controller.set_input_mode("W")

    assert controller.calculate() is True

    result = controller.last_results
    assert result is not None
    assert result.delta_T == 0.025
    assert result.Q == 9.15


def test_valves_controller_accepts_decimal_comma():
    controller, _state = _controller()
    view = controller.view
    assert view is not None
    view.flow_input.text = "1,5"

    assert controller.calculate() is True
    assert controller.last_total_flow == 3.0


def test_valves_controller_rejects_non_integer_cooler_count():
    controller, state = _controller()
    view = controller.view
    assert view is not None
    view.coolers_input.text = "1.5"

    assert controller.calculate() is False

    assert controller.last_results is None
    assert state["marked"][-1][0] is view.coolers_input
    assert state["marked"][-1][1] == (
        "invalid_field(name=valve_coolers)"
    )
    assert state["messages"][-1] == "invalid_field(name=valve_coolers)"


def test_valves_controller_does_not_calculate_without_access():
    controller, state = _controller(access=False)

    assert controller.calculate() is False

    assert controller.last_results is None
    assert state["access_denied"] == 1
    assert state["events"] == []


def test_valves_controller_only_renders_entitlement_state():
    controller, _state = _controller()
    view = controller.view
    assert view is not None

    controller.refresh_lock_ui(True)
    assert view.lock_card.height == 196
    assert view.lock_card.opacity == 1
    assert view.lock_card.disabled is False

    controller.refresh_lock_ui(False)
    assert view.lock_card.height == 0
    assert view.lock_card.opacity == 0
    assert view.lock_card.disabled is True


def test_valves_controller_refreshes_localized_text_and_theme():
    controller, state = _controller()
    view = controller.view
    assert view is not None

    controller.refresh_texts()
    controller.apply_theme()

    assert view.locked_label.text == "valve_locked"
    assert view.volume_input.hint_text == "valve_volume"
    assert view.calculate_button.text == "valve_calculate"
    assert (view.buy_button, "pro") in state["styled"]
    assert (view.watch_button, "ice") in state["styled"]
    assert (view.type_button, "primary") in state["styled"]
    assert (view.calculate_button, "ice") in state["styled"]


def test_valves_controller_uses_compact_volume_label_for_large_text():
    controller, _state = _controller()
    view = controller.view
    assert view is not None
    controller._large_text_layout = True

    controller.refresh_texts()

    assert view.volume_input.hint_text == "valve_volume_short"

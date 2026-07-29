import sys
from pathlib import Path
from types import ModuleType

from tpof.core import Product
from tpof.mobile.layout import compute_metrics
from tpof.mobile.tabs.freezing import (
    FreezingStageView,
    FreezingTabController,
    FreezingTabView,
)

ROOT = Path(__file__).parents[1]


def test_freezing_view_has_a_separate_composition_boundary():
    controller_source = (
        ROOT / "tpof" / "mobile" / "tabs" / "freezing.py"
    ).read_text(encoding="utf-8")
    view_source = (
        ROOT / "tpof" / "mobile" / "tabs" / "freezing_view.py"
    ).read_text(encoding="utf-8")

    assert "class FreezingTabViewCompositionMixin" in view_source
    assert "class FreezingTabView" in view_source
    assert "class FreezingStageView" in view_source
    assert "def build(self: Any) -> FreezingTabView:" in view_source
    assert "FreezingTabViewCompositionMixin," in controller_source
    assert "def build(self) -> FreezingTabView:" not in controller_source
    assert "from kivy.uix.image import AsyncImage" not in controller_source
    assert "from kivymd.uix.card import MDCard" not in controller_source
    assert "class FreezingTabView:" not in controller_source
    assert "class FreezingStageView:" not in controller_source
    assert "from tpof.mobile.tabs.freezing import" not in view_source
    assert len(controller_source.splitlines()) <= 820


def test_freezing_product_selection_has_a_separate_module_boundary():
    controller_source = (
        ROOT / "tpof" / "mobile" / "tabs" / "freezing.py"
    ).read_text(encoding="utf-8")
    products_source = (
        ROOT / "tpof" / "mobile" / "tabs" / "freezing_products.py"
    ).read_text(encoding="utf-8")

    assert "class FreezingProductSelectionMixin" in products_source
    assert (
        "FreezingProductSelectionMixin," in controller_source
        and "FreezingTabViewCompositionMixin," in controller_source
    )
    assert "def open_category_menu(" not in controller_source
    assert "def open_product_menu(" not in controller_source
    assert "def refresh_product_search_results(" not in controller_source
    assert "def select_product(" not in controller_source
    assert "_search_product_names" not in controller_source
    assert "def calculate(" not in products_source
    assert "from tpof.mobile.tabs.freezing import" not in products_source
    assert len(controller_source.splitlines()) <= 590


def test_freezing_calculation_workflow_has_a_separate_module_boundary():
    controller_source = (
        ROOT / "tpof" / "mobile" / "tabs" / "freezing.py"
    ).read_text(encoding="utf-8")
    workflow_source = (
        ROOT / "tpof" / "mobile" / "tabs" / "freezing_workflow.py"
    ).read_text(encoding="utf-8")

    assert "class FreezingCalculationWorkflowMixin" in workflow_source
    assert "FreezingCalculationWorkflowMixin," in controller_source
    assert "def clear_validation(" not in controller_source
    assert "def _parse_required_field(" not in controller_source
    assert "def temperature_warning(" not in controller_source
    assert "def validate_temperature(" not in controller_source
    assert "def calculate(" not in controller_source
    assert "FreezingInputs" not in controller_source
    assert "calculate_freezing" not in controller_source
    assert "find_product" not in controller_source
    assert "class _FreezingResultsPresenter(Protocol)" in workflow_source
    assert "STAGE_COLORS" not in workflow_source
    assert "stage.bar.value" not in workflow_source
    assert "from tpof.mobile.tabs.freezing import" not in workflow_source
    assert len(controller_source.splitlines()) <= 390


def test_freezing_results_have_a_separate_presentation_boundary():
    controller_source = (
        ROOT / "tpof" / "mobile" / "tabs" / "freezing.py"
    ).read_text(encoding="utf-8")
    results_source = (
        ROOT / "tpof" / "mobile" / "tabs" / "freezing_results.py"
    ).read_text(encoding="utf-8")

    assert "class FreezingResultsPresentationMixin" in results_source
    assert "FreezingResultsPresentationMixin," in controller_source
    assert "def total_text(" not in controller_source
    assert "def render_results(" not in controller_source
    assert "def reset_inputs(" not in controller_source
    assert "def total_text(" in results_source
    assert "def render_results(" in results_source
    assert "def reset_inputs(" in results_source
    assert "def calculate(" not in results_source
    assert "FreezingInputs" not in results_source
    assert "from tpof.mobile.tabs.freezing import" not in results_source
    assert len(controller_source.splitlines()) <= 300


def test_freezing_theme_and_layout_have_a_separate_presentation_boundary():
    controller_source = (
        ROOT / "tpof" / "mobile" / "tabs" / "freezing.py"
    ).read_text(encoding="utf-8")
    presentation_source = (
        ROOT / "tpof" / "mobile" / "tabs" / "freezing_presentation.py"
    ).read_text(encoding="utf-8")

    assert "class FreezingTabPresentationMixin" in presentation_source
    assert "FreezingTabPresentationMixin," in controller_source
    assert "def apply_theme(" not in controller_source
    assert "def apply_layout(" not in controller_source
    assert "def apply_theme(" in presentation_source
    assert "def apply_layout(" in presentation_source
    assert "def refresh_texts(" not in presentation_source
    assert "from tpof.mobile.tabs.freezing import" not in presentation_source
    assert len(controller_source.splitlines()) <= 180


class _Widget:
    def __init__(self, text=""):
        self.text = text
        self.hint_text = ""
        self.helper_text = ""
        self.helper_text_mode = ""
        self.height = 0
        self.width = 0
        self.opacity = 0
        self.disabled = False
        self.error = False
        self.value = 0
        self.source = ""
        self.children = []
        self.scroll_y = 0

    def add_widget(self, widget):
        self.children.append(widget)

    def clear_widgets(self):
        self.children.clear()


class _Scroll(_Widget):
    def __init__(self):
        super().__init__()
        self.calls = []

    def scroll_to(self, widget, **kwargs):
        self.calls.append((widget, kwargs))


class _Window:
    def __init__(self, softinput_mode="below_target"):
        self.softinput_mode = softinput_mode


class _Dialog:
    def __init__(self):
        self.dismissed = False

    def dismiss(self):
        self.dismissed = True


def _stage() -> FreezingStageView:
    return FreezingStageView(
        row=_Widget(),
        head=_Widget(),
        icon_chip=_Widget(),
        icon=_Widget(),
        name_label=_Widget(),
        value_label=_Widget("—"),
        bar=_Widget(),
    )


def _view() -> FreezingTabView:
    return FreezingTabView(
        scroll=_Scroll(),
        content=_Widget(),
        product_card=_Widget(),
        product_title_row=_Widget(),
        product_title_label=_Widget(),
        add_product_button=_Widget(),
        product_hint_label=_Widget(),
        product_body=_Widget(),
        product_controls=_Widget(),
        category_button=_Widget(),
        category_field_box=_Widget(),
        category_error_line=_Widget(),
        product_button=_Widget(),
        product_field_box=_Widget(),
        product_error_line=_Widget(),
        image_box=_Widget(),
        image_placeholder=_Widget(),
        image_placeholder_icon=_Widget(),
        image_placeholder_label=_Widget(),
        product_image=_Widget(),
        params_card=_Widget(),
        params_title_label=_Widget(),
        mass_row=_Widget(),
        mass_input=_Widget("100"),
        unit_button=_Widget("kg"),
        temp_start_input=_Widget("5"),
        temp_end_input=_Widget("-18"),
        time_input=_Widget("24"),
        results_card=_Widget(),
        results_title_row=_Widget(),
        results_title_label=_Widget(),
        action_row=_Widget(),
        calculate_button=_Widget(),
        pdf_button=_Widget(),
        clear_button=_Widget(),
        total_label=_Widget(),
        stages={
            "schladzanie": _stage(),
            "zamrozenie": _stage(),
            "domrozenie": _stage(),
        },
    )


def _controller(*, access=True):
    product = Product(
        nazwa="Szynka",
        kategoria="Mieso",
        c1=3.2,
        c2=1.7,
        T_zam=-2.0,
        L1=240.0,
    )
    state = {
        "messages": [],
        "events": [],
        "marked": [],
        "cleared": [],
        "styled": [],
        "exceptions": [],
        "recent": [],
    }

    def translate(key, **kwargs):
        values = ",".join(
            f"{name}={value}" for name, value in sorted(kwargs.items())
        )
        return f"{key}({values})" if values else key

    controller = FreezingTabController(
        catalog={"Mieso": [product]},
        categories=["Mieso"],
        translate=translate,
        display_category=lambda category: f"display:{category}",
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
        ensure_product_access=lambda _category, _name: access,
        is_product_selectable=lambda _index: True,
        recent_products=lambda _category, _names: (),
        add_recent_product=lambda category, name: state["recent"].append(
            (category, name)
        ),
        is_custom_product=lambda _category, _name: False,
        resolve_product_image=lambda name: f"/images/{name}.png",
        on_add_custom_product=lambda: None,
        on_export_pdf=lambda: None,
        menu_factory=lambda *_args: None,
        is_compact=lambda: False,
        menu_text_color=lambda: (1, 1, 1, 1),
        divider_color=lambda: (0.5, 0.5, 0.5, 1),
        hints_enabled=lambda: True,
    )
    controller.view = _view()
    return controller, state


def test_freezing_tab_view_exposes_input_fields_in_keyboard_order():
    view = _view()

    assert view.input_fields == (
        view.mass_input,
        view.temp_start_input,
        view.temp_end_input,
        view.time_input,
    )


def test_freezing_controller_owns_product_and_mass_unit_state():
    controller, state = _controller()
    view = controller.view
    assert view is not None

    controller.select_category("Mieso")
    controller.select_product("Szynka")
    controller.toggle_mass_unit()

    assert controller.selected_category == "Mieso"
    assert controller.selected_product == "Szynka"
    assert controller.mass_unit == "t"
    assert view.category_button.text == "display:Mieso"
    assert view.product_button.text == "Szynka"
    assert view.product_button.disabled is False
    assert view.unit_button.text == "t"
    assert state["recent"] == [("Mieso", "Szynka")]
    assert view.product_image.source == "/images/Szynka.png"


def test_product_dialog_temporarily_disables_below_target_window_panning():
    controller, _state = _controller()
    window = _Window()
    search_field = _Widget()
    search_field.focus = True
    dialog = _Dialog()

    controller._begin_product_dialog_softinput_mode(window)
    controller._product_search_field = search_field
    controller._product_dialog = dialog

    assert window.softinput_mode == ""

    controller.close_product_dialog()

    assert window.softinput_mode == "below_target"
    assert search_field.focus is False
    assert dialog.dismissed is True


def test_freezing_controller_calculates_and_renders_result():
    controller, state = _controller()
    view = controller.view
    assert view is not None
    controller.select_category("Mieso")
    controller.select_product("Szynka")

    assert controller.calculate() is True

    results = controller.last_results
    assert results is not None
    assert results.inputs.masa_kg == 100
    assert view.total_label.text.startswith("total_power(")
    assert all(stage.value_label.text.endswith(")") for stage in view.stages.values())
    assert [name for name, _payload in state["events"]] == [
        "calculation_started",
        "calculation_finished",
    ]


def test_freezing_controller_converts_tonnes_to_kilograms():
    controller, _state = _controller()
    view = controller.view
    assert view is not None
    controller.select_category("Mieso")
    controller.select_product("Szynka")
    controller.set_mass_unit("t")
    view.mass_input.text = "1,5"

    assert controller.calculate() is True
    assert controller.last_results is not None
    assert controller.last_results.inputs.masa_kg == 1500


def test_freezing_controller_rejects_missing_selection():
    controller, state = _controller()
    view = controller.view
    assert view is not None

    assert controller.calculate() is False

    assert controller.last_results is None
    assert view.category_error_line.opacity == 1
    assert view.product_error_line.opacity == 1
    assert view.scroll.scroll_y == 1
    assert state["messages"][-1] == "pick_product_error"


def test_freezing_controller_rejects_temperature_below_absolute_zero():
    controller, state = _controller()
    view = controller.view
    assert view is not None
    controller.select_category("Mieso")
    controller.select_product("Szynka")
    view.temp_end_input.text = "-274"

    assert controller.calculate() is False

    assert controller.last_results is None
    assert state["marked"][-1][0] is view.temp_end_input
    assert state["marked"][-1][1].startswith("temperature_error_absolute(")
    assert state["messages"][-1].startswith("temperature_error_absolute(")


def test_freezing_controller_stops_when_product_access_is_denied():
    controller, state = _controller(access=False)
    controller.select_category("Mieso")
    controller.select_product("Szynka")

    assert controller.calculate() is False

    assert controller.last_results is None
    assert [name for name, _payload in state["events"]] == [
        "calculation_started"
    ]


def test_freezing_controller_resets_inputs_and_results():
    controller, _state = _controller()
    view = controller.view
    assert view is not None
    controller.select_category("Mieso")
    controller.select_product("Szynka")
    assert controller.calculate() is True

    controller.reset_inputs()

    assert [field.text for field in view.input_fields] == ["", "", "", ""]
    assert controller.last_results is None
    assert view.total_label.text == "total_power(value=—)"
    assert all(stage.bar.value == 0 for stage in view.stages.values())
    assert all(stage.bar.color[-1] == 0 for stage in view.stages.values())
    assert all(stage.value_label.text == "—" for stage in view.stages.values())

    for field, value in zip(
        view.input_fields,
        ("100", "5", "-18", "24"),
        strict=True,
    ):
        field.text = value
    assert controller.calculate() is True
    assert all(
        stage.bar.color[-1] == 1 for stage in view.stages.values()
    )


def test_freezing_controller_refreshes_localized_text_and_theme():
    controller, state = _controller()
    view = controller.view
    assert view is not None

    controller.refresh_texts()
    controller.apply_theme()

    assert view.product_title_label.text == "product"
    assert view.mass_input.hint_text == "mass"
    assert view.calculate_button.text == "calculate"
    assert (view.category_button, "primary") in state["styled"]
    assert (view.pdf_button, "ice") in state["styled"]
    assert (view.clear_button, "dark") in state["styled"]


def test_freezing_controller_applies_responsive_layout(monkeypatch):
    fake_kivy = ModuleType("kivy")
    fake_metrics = ModuleType("kivy.metrics")
    fake_metrics.dp = lambda value: value
    fake_kivy.metrics = fake_metrics
    monkeypatch.setitem(sys.modules, "kivy", fake_kivy)
    monkeypatch.setitem(sys.modules, "kivy.metrics", fake_metrics)

    controller, _state = _controller()
    view = controller.view
    assert view is not None
    metrics = compute_metrics(
        lambda value: value,
        412,
        800,
        hints_enabled=True,
    )

    controller.apply_layout(metrics)

    assert view.content.padding == [16, 20, 16, 30]
    assert view.product_body.orientation == "horizontal"
    assert view.product_card.height == metrics["product_card_h"]
    assert view.mass_input.height == metrics["field_h"]
    assert view.results_card.height == metrics["results_h"]
    assert view.product_hint_label.opacity == 1
    assert view.stages["schladzanie"].icon_chip.width == metrics["stage_icon_w"]

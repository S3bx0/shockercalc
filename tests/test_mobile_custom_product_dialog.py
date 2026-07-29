from __future__ import annotations

from tpof.mobile.dialogs.custom_product import (
    CUSTOM_PRODUCT_FIELD_KEYS,
    CustomProductDialogController,
)
from tpof.mobile.user_data import CustomProductStore

VALID_VALUES = {
    "nazwa": "Produkt testowy",
    "kategoria": "Owoce",
    "wilgotnosc": "72,5",
    "t_zam": "-1,2",
    "c1": "3,7",
    "c2": "1,9",
    "l1": "240",
    "bialko": "1",
    "tluszcz": "2",
    "weglowodany": "3",
    "blonnik": "4",
    "popiol": "5",
}


class _Field:
    def __init__(self, text: str = "") -> None:
        self.text = text


class _Dialog:
    def __init__(self) -> None:
        self.dismissed = False

    def dismiss(self) -> None:
        self.dismissed = True


class _FailingStore:
    def count(self) -> int:
        return 0

    def upsert(self, _product) -> None:
        raise OSError("storage unavailable")

    def merge_into(self, _catalog) -> None:
        raise AssertionError("merge must not run after failed persistence")


def _state(tmp_path, *, is_pro=True, limit=250, store=None):
    catalog = {}
    categories = []
    messages = []
    events = []
    exceptions = []
    marked = []
    cleared = []
    selected = []
    product_store = store or CustomProductStore(tmp_path / "custom_products.json")

    def translate(key, **values):
        if values:
            value = next(iter(values.values()))
            return f"{key}:{value}"
        return key

    controller = CustomProductDialogController(
        translate=translate,
        is_pro=lambda: is_pro,
        get_product_limit=lambda: limit,
        store=product_store,
        catalog=catalog,
        categories=categories,
        get_selected_category=lambda: "Owoce",
        select_saved_product=selected.append,
        numeric_input_filter=lambda value, _undo: value,
        clear_field_error=cleared.append,
        mark_field_error=lambda field, message=None: marked.append(
            (field, message)
        ),
        show_message=messages.append,
        log_event=lambda *args: events.append(args),
        record_exception=lambda exc, context: exceptions.append((exc, context)),
    )
    return {
        "controller": controller,
        "store": product_store,
        "catalog": catalog,
        "categories": categories,
        "messages": messages,
        "events": events,
        "exceptions": exceptions,
        "marked": marked,
        "cleared": cleared,
        "selected": selected,
    }


def test_field_specs_cover_complete_product_record_and_prefill_category(tmp_path):
    state = _state(tmp_path)

    specs = state["controller"].field_specs()

    assert tuple(spec[0] for spec in specs) == CUSTOM_PRODUCT_FIELD_KEYS
    assert specs[1] == ("kategoria", "custom_category", None, "Owoce")
    assert specs[2][2] is not None


def test_open_requires_pro_before_importing_kivy(tmp_path):
    state = _state(tmp_path, is_pro=False)

    assert state["controller"].open() is False

    assert state["messages"] == ["custom_product_pro"]
    assert state["controller"].is_open is False


def test_open_enforces_remote_product_limit(tmp_path):
    store = CustomProductStore(tmp_path / "custom_products.json")
    state = _state(tmp_path, limit=1, store=store)
    state["controller"]._fields = {
        key: _Field(value) for key, value in VALID_VALUES.items()
    }
    assert state["controller"].save() is True

    assert state["controller"].open() is False

    assert state["messages"][-1] == "custom_product_limit:1"


def test_save_persists_merges_selects_and_releases_widgets(tmp_path):
    state = _state(tmp_path)
    controller = state["controller"]
    dialog = _Dialog()
    controller._dialog = dialog
    controller._fields = {
        key: _Field(value) for key, value in VALID_VALUES.items()
    }

    assert controller.save() is True

    assert state["store"].count() == 1
    assert state["categories"] == ["owoce"]
    assert state["catalog"]["owoce"][0].nazwa == "Produkt testowy"
    assert state["selected"][0].nazwa == "Produkt testowy"
    assert state["messages"] == ["custom_product_saved"]
    assert state["events"] == [("custom_product_saved",)]
    assert dialog.dismissed is True
    assert controller.is_open is False
    assert controller._fields == {}


def test_save_marks_field_named_by_validation_error(tmp_path):
    state = _state(tmp_path)
    controller = state["controller"]
    name_field = _Field("")
    controller._dialog = _Dialog()
    controller._fields = {
        key: _Field(value) for key, value in VALID_VALUES.items()
    }
    controller._fields["nazwa"] = name_field

    assert controller.save() is False

    assert state["marked"] == [(name_field, "custom_required")]
    assert state["messages"] == ["custom_required"]
    assert state["store"].count() == 0
    assert controller.is_open is True


def test_save_reports_storage_error_without_updating_catalog(tmp_path):
    state = _state(tmp_path, store=_FailingStore())
    controller = state["controller"]
    controller._dialog = _Dialog()
    controller._fields = {
        key: _Field(value) for key, value in VALID_VALUES.items()
    }

    assert controller.save() is False

    assert len(state["exceptions"]) == 1
    error, context = state["exceptions"][0]
    assert isinstance(error, OSError)
    assert context == "save_custom_product"
    assert state["messages"] == ["calc_error:storage unavailable"]
    assert state["catalog"] == {}
    assert controller.is_open is True


def test_close_dismisses_dialog_and_clears_fields(tmp_path):
    state = _state(tmp_path)
    controller = state["controller"]
    dialog = _Dialog()
    controller._dialog = dialog
    controller._fields = {"nazwa": _Field("Test")}

    controller.close()

    assert dialog.dismissed is True
    assert controller.is_open is False
    assert controller._fields == {}

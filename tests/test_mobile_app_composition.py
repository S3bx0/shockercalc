from __future__ import annotations

import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).parents[1]


def _source(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_mobile_main_is_a_thin_lazy_launcher():
    source = _source("tpof/mobile/main.py")

    assert "from tpof.mobile.app import ShockerCalcApp" in source
    assert "ShockerCalcApp().run()" in source
    assert "class ShockerCalcApp" not in source
    assert len(source.splitlines()) <= 40


def test_mobile_app_owns_the_kivy_composition_root():
    source = _source("tpof/mobile/app.py")

    assert "class ShockerCalcApp(MDApp):" in source
    assert "def build(self):" in source
    assert "MobileShellBuilder(" in source
    assert "ShockerCalcApp().run()" not in source


def test_mobile_main_delegates_to_app_class(monkeypatch):
    calls: list[str] = []

    class FakeApp:
        def run(self) -> None:
            calls.append("run")

    fake_module = ModuleType("tpof.mobile.app")
    fake_module.ShockerCalcApp = FakeApp
    monkeypatch.setitem(sys.modules, "tpof.mobile.app", fake_module)

    from tpof.mobile.main import main

    main()

    assert calls == ["run"]

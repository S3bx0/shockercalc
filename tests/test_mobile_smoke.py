"""Smoke testy warstwy mobilnej — nie wymagają zainstalowanego KivyMD.

Sprawdzamy tylko, że:
  • moduł `tpof.mobile.main` importuje się bez błędu (czysty Python),
  • ścieżki do zasobów są poprawnie skonfigurowane,
  • okablowanie mobilnego UI pozostaje obecne po refaktorze.
"""
from __future__ import annotations

import importlib
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]


def _source(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_mobile_main_importuje_sie():
    module = importlib.import_module("tpof.mobile.main")
    assert hasattr(module, "main")
    assert callable(module.main)


def test_mobilny_wynik_nie_ujawnia_wlasciwosci_produktu():
    source = _source("tpof/mobile/main.py")

    assert "self.props_grid" not in source
    assert "lbl_props_title" not in source
    assert "watermark_image_path=None" in source


def test_mobilny_font_ma_fallback_do_kivy():
    from tpof.mobile.android_bridge import _runtime_font_path

    assert _runtime_font_path() is not None


def test_przelacznik_podpowiedzi_uzywa_obslugiwanego_trybu_kivymd():
    source = _source("tpof/mobile/main.py")

    assert 'helper_text_mode = "none"' not in source
    assert 'field.helper_text_mode = "on_focus"' in source


def test_mobilny_naglowek_uzywa_brandowego_gradientu():
    source = _source("tpof/mobile/main.py")
    toolbar_source = _source("tpof/mobile/widgets/toolbar.py")

    assert "class BrandToolbar" in toolbar_source
    assert "class FrostChip" in toolbar_source
    assert "from tpof.mobile.widgets import (" in source
    assert 'text="Refrigeration\\nCalc"' in source
    assert "self.toolbar_snowflake = MDIconButton" in source
    assert "md_bg_color=(0.12, 0.55, 0.86, 1)" not in source


def test_mobilne_wyniki_uzywaja_animowanych_ikon_i_tla_marki():
    source = _source("tpof/mobile/main.py")
    stage_source = _source("tpof/mobile/widgets/stage_icons.py")
    frost_source = _source("tpof/mobile/widgets/frost.py")

    assert "class StageMotionIcon" in stage_source
    assert "StageMotionIcon(" in source
    assert "self._position_bands()" in frost_source
    assert "assets/images" in source


def test_mobilne_tlo_ma_stabilna_warstwe_i_nawigacja_nie_zapada_zakladek():
    source = _source("tpof/mobile/main.py")
    layout_source = _source("tpof/mobile/layout.py")

    assert "self._root_bg_color = Color(*SURFACE_DARK)" in source
    assert "self._root_bg_rect = Rectangle" in source
    assert "self.tab_frost_background = FrostBackground" in source
    assert "self.bottom_nav.size_hint_y = 1" not in source
    assert '"bottom_nav_h"' in source
    assert 'self.bottom_nav.height = m["bottom_nav_h"]' in source
    assert "reserved_ad_h = max(64 if compact else 70" in layout_source


def test_mobilne_zakladki_maja_wlasne_animowane_ikony():
    source = _source("tpof/mobile/main.py")
    nav_source = _source("tpof/mobile/widgets/bottom_nav.py")

    assert "class BottomNavMotionIcon" in nav_source
    assert "class BottomNavTab" in nav_source
    assert "self.bottom_freezing_tab" in source
    assert "self.bottom_valves_tab" in source
    assert "self.bottom_labor_tab" in source
    assert "def _show_tab" in source
    assert "tab.play()" in source
    assert "width=dp(1.15)" in nav_source
    assert "width=dp(1.45)" not in nav_source


def test_jasny_motyw_ma_lodowy_dolny_pasek_zakladek():
    source = _source("tpof/mobile/main.py")
    constants_source = _source("tpof/mobile/constants.py")
    nav_source = _source("tpof/mobile/widgets/bottom_nav.py")

    assert "BOTTOM_NAV_BG_LIGHT" in constants_source
    assert "def _bottom_nav_bg" in source
    assert "self.bottom_nav.md_bg_color = self._bottom_nav_bg()" in source
    assert "def set_theme_light" in nav_source
    assert "self.bottom_freezing_tab.set_theme_light" in source
    assert "self.bottom_valves_tab.set_theme_light" in source
    assert "self.bottom_labor_tab.set_theme_light" in source
    assert "self.bottom_nav.md_bg_color = (0.04, 0.05, 0.07, 1)" not in source


def test_przelaczenie_zakladki_odswieza_motyw_po_odblokowaniu():
    source = _source("tpof/mobile/main.py")
    show_tab_block = source[
        source.index("def _show_tab") : source.index("def _set_tab_visibility")
    ]
    toggle_theme_block = source[
        source.index("def _toggle_theme") : source.index("def _reset_inputs")
    ]

    assert "self._sync_theme_surfaces()" in show_tab_block
    assert "Clock.schedule_once(lambda *_: self._sync_theme_surfaces(), 0)" in show_tab_block
    assert "Clock.schedule_once(lambda *_: self._sync_theme_surfaces(), 0)" in toggle_theme_block


def test_przyciski_zaworow_uzywaja_brandowej_palety():
    source = _source("tpof/mobile/main.py")
    theme_source = _source("tpof/mobile/theme.py")

    assert '"muted"' in theme_source
    assert "def _style_valve_mode_buttons" in source
    assert '(getattr(self, "valve_btn_buy", None), "pro")' in source
    assert '(getattr(self, "valve_btn_watch", None), "ice")' in source
    assert '(getattr(self, "valve_btn_type", None), "primary")' in source
    assert '(getattr(self, "valve_btn_calc", None), "ice")' in source
    assert 'self._style_app_button(self.valve_btn_mode_k, "ice" if k else "muted")' in source
    assert 'self._style_app_button(self.valve_btn_mode_w, "muted" if k else "ice")' in source
    assert "active = self.theme_cls.primary_color" not in source


def test_nieaktywna_zakladka_nie_blokuje_dotyku():
    source = _source("tpof/mobile/main.py")

    assert "def _set_tab_visibility" in source
    assert "widget.size = (0, 0)" in source
    assert '"labor": getattr(self, "labor_scroll", None)' in source
    assert "self._raise_tab_widget(tab_widgets.get(name))" in source
    assert "host.remove_widget(widget)" in source
    assert "host.add_widget(widget)" in source


def test_mobilna_walidacja_temperatur_chroni_przed_skrajnymi_wartosciami():
    source = _source("tpof/mobile/main.py")
    constants_source = _source("tpof/mobile/constants.py")

    assert "ABSOLUTE_ZERO_C = -273.15" in constants_source
    assert "TEMP_HIGH_ERROR_C = 130.0" in constants_source
    assert "def _validate_temperature_input" in source
    assert "temperature_warning_co2" in source


def test_mobilne_ustawienia_i_lokalizacja_sa_przygotowane():
    source = _source("tpof/mobile/main.py")
    i18n_source = _source("tpof/mobile/i18n.py")
    languages = ROOT / "resources" / "strings" / "languages.json"

    assert "def _open_settings_dialog" in source
    assert "self.toolbar_snowflake = MDIconButton" in source
    assert "on_release=lambda *_: self._open_settings_dialog()" in source
    assert "units_imperial_disabled" in source
    assert "def _refresh_exchange_rates_async" in source
    assert "SUPPORTED_DISPLAY_CURRENCIES" in source
    assert "self._preferences.set_display_currency(value)" in source
    assert "for _fallback_lang in (\"es\", \"fr\", \"it\", \"pt\", \"ja\", \"zh\")" in i18n_source
    assert languages.exists()


def test_mobilny_edytor_stawek_robocizny_jest_w_pro_i_uzywa_zapisanych_stawek():
    source = _source("tpof/mobile/main.py")

    assert "def _open_labor_rates_dialog" in source
    assert "labor_rates_pro_required" in source
    assert "labor_rates_factory" in source
    assert "self._preferences.set_labor_rate_values" in source
    assert "self._preferences.reset_labor_rate_values" in source
    assert "def _reset_labor_rates" in source
    assert "self._preferences.reset_labor_rate_values()" in source
    assert "self._labor_rate_config()" in source


def test_mobilne_pola_przewijaja_sie_nad_klawiature():
    source = _source("tpof/mobile/main.py")

    assert 'Window.softinput_mode = "below_target"' in source
    assert "def _configure_text_field" in source
    assert "field.font_size = sp(18)" in source
    assert "field.padding = [0, dp(12), 0, dp(8)]" in source
    assert "self._configure_text_field(self.in_m)" in source
    assert "self._configure_text_field(w)" in source
    assert "def _bind_keyboard_scroll" in source
    assert "def _scroll_input_into_view" in source
    assert "padding=dp(150)" in source
    assert "(self.in_m, self.in_T1, self.in_T2, self.in_t)" in source
    assert "self.valve_in_V," in source
    assert "self.valve_in_q," in source
    assert "self.labor_in_people," in source
    assert "self.labor_in_additional," in source


def test_robocizna_ma_wykres_kolowy_kosztow():
    source = _source("tpof/mobile/main.py")
    widgets_source = _source("tpof/mobile/widgets/__init__.py")
    chart_source = _source("tpof/mobile/widgets/charts.py")

    assert "class LaborPieChart" in chart_source
    assert "SEGMENT_COLORS" in chart_source
    assert "def on_touch_down" in chart_source
    assert "LaborPieChart" in widgets_source
    assert "self.labor_chart = LaborPieChart" in source
    assert "on_release=lambda *_: self._open_labor_chart_dialog()" in source
    assert "self._set_labor_chart_data(" in source
    assert "center_label=self._t(\"labor_chart_total\")" in source
    assert "Animation(progress=1.0, duration=0.75" in chart_source
    assert "prepare_cost_segments" in chart_source
    assert "self.labor_chart_legend" in source
    assert "def _render_labor_chart_legend" in source
    assert "def _open_labor_chart_dialog" in source
    assert "labor_chart_tap" in source
    assert "from kivymd.uix.dialog import MDDialog" in source
    assert "from kivymd.uix.button import MDFlatButton" in source


def test_mobilne_komunikaty_walidacji_sa_centralne_i_zanikaja():
    source = _source("tpof/mobile/main.py")
    notice_source = _source("tpof/mobile/widgets/notice.py")

    assert "class CenterNotice" in notice_source
    assert "self.center_notice = CenterNotice()" in source
    assert "notice.show(message)" in source
    assert "Animation(opacity=1, d=1.5) + Animation(opacity=0, d=0.5)" in notice_source
    assert '"center_y": 0.54' in notice_source
    assert "def _hide_after_fade" in notice_source
    assert "self.size = (0, 0)" in notice_source


def test_paths_wskazuja_na_istniejace_zasoby():
    from tpof.mobile.paths import DATA_PATH, IMAGES_DIR

    assert DATA_PATH.exists(), f"Brak bazy danych: {DATA_PATH}"
    assert IMAGES_DIR.exists(), f"Brak katalogu obrazów: {IMAGES_DIR}"


def test_sync_module_ownership_nadaje_modul(tmp_path):
    from tpof.mobile.entitlements import MODULE_VALVES, Entitlements
    from tpof.mobile.services.entitlements_ui import _sync_module_ownership

    ent = Entitlements(state_path=tmp_path / "entitlement.json")
    _sync_module_ownership(ent, MODULE_VALVES, True)
    assert MODULE_VALVES in ent.owned_modules()


def test_sync_module_ownership_cofa_modul_po_revoke(tmp_path):
    from tpof.mobile.entitlements import MODULE_VALVES, Entitlements
    from tpof.mobile.services.entitlements_ui import _sync_module_ownership

    ent = Entitlements(state_path=tmp_path / "entitlement.json")
    ent.grant_module(MODULE_VALVES)
    _sync_module_ownership(ent, MODULE_VALVES, False)
    assert MODULE_VALVES not in ent.owned_modules()


def test_pdf_output_dir_na_desktopie_zwraca_cwd():
    from tpof.mobile.pdf_export import _pdf_output_dir

    out = _pdf_output_dir()
    assert out.exists()
    assert out.is_dir()


def test_main_bez_kivymd_rzuca_systemexit(monkeypatch):
    """Gdy KivyMD nie jest dostępne, main() powinien zakończyć się czytelnym SystemExit."""
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name.startswith("kivymd") or name.startswith("kivy"):
            raise ImportError(f"symulowany brak: {name}")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    from tpof.mobile.main import main

    with pytest.raises(SystemExit) as exc_info:
        main()
    assert "KivyMD" in str(exc_info.value)

"""Smoke testy warstwy mobilnej — nie wymagają zainstalowanego KivyMD.

Sprawdzamy tylko, że:
  • moduł `tpof.mobile.main` importuje się bez błędu (czysty Python),
  • ścieżki do zasobów są poprawnie skonfigurowane,
  • okablowanie mobilnego UI pozostaje obecne w modułach kompozycji aplikacji.
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
    source = _source("tpof/mobile/app.py")
    pdf_source = _source("tpof/mobile/pdf_export.py")

    assert "self.props_grid" not in source
    assert "lbl_props_title" not in source
    assert "watermark_image_path=None" in pdf_source


def test_mobilny_font_ma_fallback_do_kivy():
    from tpof.mobile.android_bridge import _runtime_font_path

    assert _runtime_font_path() is not None


def test_przelacznik_podpowiedzi_uzywa_obslugiwanego_trybu_kivymd():
    source = _source("tpof/mobile/app.py")
    composition_source = _source("tpof/mobile/app_controllers.py")
    interactions_source = _source("tpof/mobile/form_interactions.py")

    assert 'helper_text_mode = "none"' not in source
    assert 'helper_text_mode = "none"' not in interactions_source
    assert 'field.helper_text_mode = "on_focus"' in interactions_source
    assert "class FormInteractionController" in interactions_source
    assert "self._form_interactions = FormInteractionController(" in composition_source
    assert "def _apply_hints" not in source


def test_mobilny_naglowek_uzywa_brandowego_gradientu():
    source = _source("tpof/mobile/app.py")
    shell_source = _source("tpof/mobile/shell.py")
    toolbar_source = _source("tpof/mobile/widgets/toolbar.py")

    assert "class BrandToolbar" in toolbar_source
    assert "class FrostChip" in toolbar_source
    assert "from tpof.mobile.widgets import (" in source
    assert 'text="Refrigeration\\nCalc"' in shell_source
    assert "toolbar_snowflake = factories.icon_button" in shell_source
    assert "MobileShellBuilder(" in source
    assert "md_bg_color=(0.12, 0.55, 0.86, 1)" not in source


def test_mobilne_wyniki_uzywaja_animowanych_ikon_i_tla_marki():
    source = _source("tpof/mobile/app.py")
    freezing_view_source = _source("tpof/mobile/tabs/freezing_view.py")
    stage_source = _source("tpof/mobile/widgets/stage_icons.py")
    frost_source = _source("tpof/mobile/widgets/frost.py")

    assert "class StageMotionIcon" in stage_source
    assert "StageMotionIcon(" in freezing_view_source
    assert "self._position_bands()" in frost_source
    assert "assets/images" in source


def test_mobilne_tlo_ma_stabilna_warstwe_i_nawigacja_nie_zapada_zakladek():
    source = _source("tpof/mobile/app.py")
    composition_source = _source("tpof/mobile/app_controllers.py")
    layout_source = _source("tpof/mobile/layout.py")

    assert "self._root_bg_color = Color(*SURFACE_DARK)" in source
    assert "self._root_bg_rect = Rectangle" in source
    assert "self.tab_frost_background = FrostBackground" in source
    assert "self.bottom_nav.size_hint_y = 1" not in source
    assert '"bottom_nav_h"' in layout_source
    assert "class ResponsiveLayoutController" in layout_source
    assert "self._responsive_controller = ResponsiveLayoutController(" in composition_source
    assert 'view.bottom_nav.height = metrics["bottom_nav_h"]' in layout_source
    assert "ResponsiveLayoutView.from_shell(self)" in source
    assert "def _apply_responsive_layout" not in source
    assert "reserved_ad_h = max(64 if compact else 70" in layout_source


def test_mobilne_zakladki_maja_wlasne_animowane_ikony():
    source = _source("tpof/mobile/app.py")
    controller_source = _source("tpof/mobile/navigation.py")
    nav_source = _source("tpof/mobile/widgets/bottom_nav.py")

    assert "class TabNavigationController" in controller_source
    assert "class BottomNavMotionIcon" in nav_source
    assert "class BottomNavTab" in nav_source
    assert "self._navigation_controller = TabNavigationController(" in source
    assert "self.bottom_freezing_tab" in source
    assert "self.bottom_valves_tab" in source
    assert "self.bottom_labor_tab" in source
    assert "def _show_tab" in source
    assert "tab.play()" in controller_source
    assert "width=dp(1.15)" in nav_source
    assert "width=dp(1.45)" not in nav_source


def test_jasny_motyw_ma_lodowy_dolny_pasek_zakladek():
    source = _source("tpof/mobile/app.py")
    composition_source = _source("tpof/mobile/app_controllers.py")
    shell_source = _source("tpof/mobile/shell.py")
    constants_source = _source("tpof/mobile/constants.py")
    theme_source = _source("tpof/mobile/theme.py")
    nav_source = _source("tpof/mobile/widgets/bottom_nav.py")

    assert "BOTTOM_NAV_BG_LIGHT" in constants_source
    assert "class ThemeSyncController" in theme_source
    assert "self._theme_controller = ThemeSyncController(" in composition_source
    assert "bottom_nav_bg=self._theme_controller.bottom_nav_bg" in composition_source
    assert "md_bg_color=callbacks.bottom_nav_bg()" in shell_source
    assert "view.bottom_nav.md_bg_color = bottom_nav_bg(dark)" in theme_source
    assert "def set_theme_light" in nav_source
    assert "tab.set_theme_light(not dark)" in theme_source
    assert "self.bottom_nav.md_bg_color = (0.04, 0.05, 0.07, 1)" not in source


def test_przelaczenie_zakladki_odswieza_motyw_po_odblokowaniu():
    source = _source("tpof/mobile/app.py")
    controller_source = _source("tpof/mobile/navigation.py")
    theme_source = _source("tpof/mobile/theme.py")

    assert "self._refresh_theme()" in controller_source
    assert "self._schedule_once(lambda *_args: self._refresh_theme(), 0)" in controller_source
    assert "refresh_theme=self._theme_controller.apply" in source
    assert "def toggle(self) -> bool" in theme_source
    assert "self._schedule_once(lambda *_args: self.apply(), 0)" in theme_source
    assert "def _toggle_theme" not in source


def test_przyciski_zaworow_uzywaja_brandowej_palety():
    source = _source("tpof/mobile/tabs/valves.py")
    theme_source = _source("tpof/mobile/theme.py")

    assert '"muted"' in theme_source
    assert "def style_mode_buttons" in source
    assert '(self.view.buy_button, "pro")' in source
    assert '(self.view.watch_button, "ice")' in source
    assert '(self.view.type_button, "primary")' in source
    assert '(self.view.calculate_button, "ice")' in source
    assert '"ice" if volume_mode else "muted"' in source
    assert '"muted" if volume_mode else "ice"' in source
    assert "active = self.theme_cls.primary_color" not in source


def test_nieaktywna_zakladka_nie_blokuje_dotyku():
    source = _source("tpof/mobile/app.py")
    controller_source = _source("tpof/mobile/navigation.py")

    assert "def set_tab_visibility" in controller_source
    assert "widget.size = (0, 0)" in controller_source
    assert '"valves": self._valves_tab_controller.scroll' in source
    assert '"labor": self._labor_tab_controller.scroll' in source
    assert "self.raise_tab_widget(self._get_host(), tab_widgets.get(name))" in controller_source
    assert "host.remove_widget(widget)" in controller_source
    assert "host.add_widget(widget)" in controller_source


def test_mobilna_walidacja_temperatur_chroni_przed_skrajnymi_wartosciami():
    source = _source("tpof/mobile/tabs/freezing.py")
    constants_source = _source("tpof/mobile/constants.py")

    assert "ABSOLUTE_ZERO_C = -273.15" in constants_source
    assert "TEMP_HIGH_ERROR_C = 130.0" in constants_source
    assert "def validate_temperature" in source
    assert "temperature_warning_co2" in source


def test_mobilne_ustawienia_i_lokalizacja_sa_przygotowane():
    source = _source("tpof/mobile/app.py")
    composition_source = _source("tpof/mobile/app_controllers.py")
    shell_source = _source("tpof/mobile/shell.py")
    localization_source = _source("tpof/mobile/localization.py")
    settings_source = _source("tpof/mobile/dialogs/settings.py")
    state_source = _source("tpof/mobile/settings_state.py")
    i18n_source = _source("tpof/mobile/i18n.py")
    languages = ROOT / "resources" / "strings" / "languages.json"

    assert "def _open_settings_dialog" in source
    assert "toolbar_snowflake = factories.icon_button" in shell_source
    assert "on_open_settings=self._open_settings_dialog" in source
    assert "on_release=lambda *_args: callbacks.on_open_settings()" in shell_source
    assert "units_imperial_disabled" in state_source
    assert "SettingsStateController" in composition_source
    assert "def refresh_exchange_rates_async" in state_source
    assert "SUPPORTED_DISPLAY_CURRENCIES" in state_source
    assert "self._preferences.set_display_currency(value)" in state_source
    assert "SettingsDialogController" in composition_source
    assert "self._settings_dialog_controller.open()" in source
    assert "class SettingsStateController" in state_source
    assert "class SettingsDialogController" in settings_source
    assert "class LocalizationController" in localization_source
    assert "self._localization = LocalizationController(" in composition_source
    assert "self._t = self._localization.translate" in composition_source
    assert "on_toggle_language=self._localization.toggle" in source
    assert "def _toggle_language" not in source
    assert "def _refresh_texts" not in source
    assert "settings_currency_rates_title" in settings_source
    assert "self._currency_rate_labels" in settings_source
    assert "format_exchange_rate(code, rates, language)" in settings_source
    assert "content_cls=settings_scroll" in settings_source
    assert "self._settings_currency_rate_labels" not in source
    assert "for _fallback_lang in (\"es\", \"fr\", \"it\", \"pt\", \"ja\", \"zh\")" in i18n_source
    assert languages.exists()


def test_mobilny_edytor_stawek_robocizny_jest_w_pro_i_uzywa_zapisanych_stawek():
    composition_source = _source("tpof/mobile/app_controllers.py")
    dialog_source = _source("tpof/mobile/dialogs/labor_rates.py")
    labor_tab_source = _source("tpof/mobile/tabs/labor.py")

    assert (
        "open_rates_dialog=lambda: self._labor_rates_dialog_controller.open()"
        in composition_source
    )
    assert "def open_rates" in labor_tab_source
    assert "labor_rates_pro_required" in labor_tab_source
    assert "LaborRatesDialogController" in composition_source
    assert "self._preferences.set_labor_rate_values" in composition_source
    assert "self._preferences.reset_labor_rate_values" in composition_source
    assert "def _rate_config" in labor_tab_source
    assert "rate_config_from_values(self._get_rate_values())" in labor_tab_source
    assert "class LaborRatesDialogController" in dialog_source
    assert "labor_rates_factory" in dialog_source
    assert "def save(" in dialog_source
    assert "def reset(" in dialog_source
    assert "self._labor_rate_fields" not in composition_source


def test_mobilny_formularz_wlasnego_produktu_ma_osobny_kontroler():
    source = _source("tpof/mobile/app.py")
    composition_source = _source("tpof/mobile/app_controllers.py")
    dialog_source = _source("tpof/mobile/dialogs/custom_product.py")

    assert "CustomProductDialogController" in composition_source
    assert "self._custom_product_dialog_controller.open" in composition_source
    assert "class CustomProductDialogController" in dialog_source
    assert "CUSTOM_PRODUCT_FIELD_KEYS" in dialog_source
    assert "create_custom_product(values)" in dialog_source
    assert "self._store.upsert(product)" in dialog_source
    assert "def _open_custom_product_dialog" not in source
    assert "self._custom_product_fields" not in source


def test_mobilna_prywatnosc_i_telemetria_maja_osobny_kontroler():
    source = _source("tpof/mobile/app.py")
    composition_source = _source("tpof/mobile/app_controllers.py")
    shell_source = _source("tpof/mobile/shell.py")
    dialog_source = _source("tpof/mobile/dialogs/privacy.py")

    assert "PrivacyDialogController" in composition_source
    assert "on_open_privacy=self._privacy_dialog_controller.open" in source
    assert "on_release=callbacks.on_open_privacy" in shell_source
    assert (
        "self._privacy_dialog_controller.options_available()" in composition_source
    )
    assert "class PrivacyDialogController" in dialog_source
    assert "def prompt_telemetry_consent" in dialog_source
    assert "def open_ad_privacy_options" in dialog_source
    assert "def _open_privacy_options" not in source
    assert "self._privacy_dialog = None" not in source
    assert "self._telemetry_dialog = None" not in source


def test_mobilna_robocizna_deleguje_prezentacje_wykresu_do_osobnego_modulu():
    source = _source("tpof/mobile/app.py")
    composition_source = _source("tpof/mobile/app_controllers.py")
    presenter_source = _source("tpof/mobile/tabs/labor.py")

    assert "LaborTabController" in composition_source
    assert "labor_scroll = self._labor_tab_controller.build().scroll" in source
    assert "self._labor_tab_controller.refresh_texts()" in composition_source
    assert "self._labor_tab_controller.apply_theme()" in composition_source
    assert "class LaborTabPresenter" in presenter_source
    assert "class LaborTabController" in presenter_source
    assert "class LaborTabView" in presenter_source
    assert "class LaborChartRow" in presenter_source
    assert "_CHART_LABEL_KEYS" in presenter_source
    assert "def calculate(self) -> bool" in presenter_source
    assert "self._presenter.chart_rows(breakdown)" in presenter_source
    assert "self._presenter.travel_mode_text(breakdown.travel_mode)" in presenter_source
    assert "self.labor_in_people" not in source
    assert "self._last_labor_breakdown" not in source
    assert "self._labor_use_highways" not in source


def test_mobilne_pola_przewijaja_sie_nad_klawiature():
    source = _source("tpof/mobile/app.py")
    composition_source = _source("tpof/mobile/app_controllers.py")
    interactions_source = _source("tpof/mobile/form_interactions.py")
    freezing_view_source = _source("tpof/mobile/tabs/freezing_view.py")
    labor_tab_source = _source("tpof/mobile/tabs/labor.py")
    valves_tab_source = _source("tpof/mobile/tabs/valves.py")

    assert 'Window.softinput_mode = "below_target"' in source
    assert "def _configure_text_field" in freezing_view_source
    assert "field.font_size = sp(18)" in freezing_view_source
    assert "field.padding = [0, dp(12), 0, dp(8)]" in freezing_view_source
    assert "self._configure_text_field(mass_input" in freezing_view_source
    assert "self._configure_text_field(field" in freezing_view_source
    assert "def bind_keyboard_scroll" in interactions_source
    assert "def _scroll_input_into_view" in interactions_source
    assert "padding=self._dp(150)" in interactions_source
    assert "def _bind_keyboard_scroll" not in source
    assert (
        "bind_keyboard_scroll=self._form_interactions.bind_keyboard_scroll"
        in composition_source
    )
    assert (
        "self._bind_keyboard_scroll(self.view.input_fields, scroll)"
        in freezing_view_source
    )
    assert "self._bind_keyboard_scroll(view.input_fields, scroll)" in valves_tab_source
    assert "self.view.volume_input" in valves_tab_source
    assert "self.view.flow_input" in valves_tab_source
    assert "self._bind_keyboard_scroll(view.input_fields, scroll)" in labor_tab_source
    assert "self.view.people_input" in labor_tab_source
    assert "self.view.additional_input" in labor_tab_source


def test_mobilne_zawory_maja_wlasny_kontroler_i_granice_widoku():
    source = _source("tpof/mobile/app.py")
    composition_source = _source("tpof/mobile/app_controllers.py")
    valves_tab_source = _source("tpof/mobile/tabs/valves.py")

    assert "ValvesTabController" in composition_source
    assert "valve_scroll = self._valves_tab_controller.build().scroll" in source
    assert "self._valves_tab_controller.refresh_texts()" in composition_source
    assert "self._valves_tab_controller.apply_theme()" in composition_source
    assert "class ValvesTabController" in valves_tab_source
    assert "class ValvesTabView" in valves_tab_source
    assert "def calculate(self) -> bool" in valves_tab_source
    assert "calculate_decompression_valves(" in valves_tab_source
    assert "self.valve_in_V" not in source
    assert "self._last_valve_results" not in source
    assert "self._valve_input_mode" not in source
    assert "def _build_valve_tab" not in source
    assert "def _calculate_valves" not in source


def test_robocizna_ma_wykres_kolowy_kosztow():
    source = _source("tpof/mobile/app.py")
    labor_tab_source = _source("tpof/mobile/tabs/labor.py")
    widgets_source = _source("tpof/mobile/widgets/__init__.py")
    chart_source = _source("tpof/mobile/widgets/charts.py")

    assert "class LaborPieChart" in chart_source
    assert "SEGMENT_COLORS" in chart_source
    assert "def on_touch_down" in chart_source
    assert "LaborPieChart" in widgets_source
    assert "chart_factory=LaborPieChart" in source
    assert "chart = self._chart_factory(" in labor_tab_source
    assert "on_release=lambda *_: self.open_chart_dialog()" in labor_tab_source
    assert "self._set_chart_data(" in labor_tab_source
    assert 'center_label=self._translate("labor_chart_total")' in labor_tab_source
    assert "Animation(progress=1.0, duration=0.75" in chart_source
    assert "prepare_cost_segments" in chart_source
    assert "Mesh(vertices=vertices" in chart_source
    assert "gap = min(2.2, sweep * 0.18) if multiple_segments else 0.0" in chart_source
    assert "font_size * available_width / measurement.texture.size[0]" in chart_source
    assert "ring_width + dp(5)" not in chart_source
    assert "self._chart_dialog.size_hint_x = 0.94" in labor_tab_source
    assert "self.view.chart_legend" in labor_tab_source
    assert "def _render_chart_legend" in labor_tab_source
    assert "def open_chart_dialog" in labor_tab_source
    assert "labor_chart_tap" in labor_tab_source
    assert "from kivymd.uix.dialog import MDDialog" in labor_tab_source
    assert "from kivymd.uix.button import MDFlatButton" in labor_tab_source


def test_mobilne_komunikaty_walidacji_sa_centralne_i_zanikaja():
    source = _source("tpof/mobile/app.py")
    shell_source = _source("tpof/mobile/shell.py")
    notice_source = _source("tpof/mobile/widgets/notice.py")

    assert "class CenterNotice" in notice_source
    assert "center_notice=self._factories.center_notice()" in shell_source
    assert "center_notice=CenterNotice" in source
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

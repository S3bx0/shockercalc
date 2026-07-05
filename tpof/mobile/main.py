"""Refrigeration Calc — wersja mobilna (KivyMD).

UI w parytecie z desktopem:
  • TopAppBar z przełącznikiem Dark/Light
  • kaskadowy wybór Kategoria → Produkt
  • masa z przełącznikiem jednostek kg/t
  • paski mocy (schładzanie / zamrożenie / domrażanie) + SUMA
  • opcjonalne zdjęcie produktu z assets/images
  • centralny komunikat dla błędów walidacji

Uruchomienie lokalne (desktop, do testów UI):
    python -m pip install -r requirements-mobile.txt
    python -m tpof.mobile

Build APK:
    buildozer android debug
"""
from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from tpof.core import (
    ZAWORY,
    FreezingInputs,
    Product,
    calculate_decompression_valves,
    calculate_freezing,
    find_product,
    list_categories,
    list_products,
    load_products,
)
from tpof.labor import (
    RATE_CONFIG_FIELDS,
    default_rate_config,
    rate_config_from_values,
)
from tpof.labor import (
    CalculationInput as LaborCalculationInput,
)
from tpof.labor import (
    calculate_cost_breakdown as calculate_labor_cost_breakdown,
)
from tpof.labor import (
    validate_calculation_inputs as validate_labor_inputs,
)
from tpof.mobile import telemetry, theme
from tpof.mobile.android_bridge import _purge_host_arch_fonttools_so, _runtime_font_path
from tpof.mobile.catalog import (
    _mobile_product_names,
    _ordered_mobile_categories,
    _safe_image_path,
    _search_product_names,
)
from tpof.mobile.constants import (
    ABSOLUTE_ZERO_C,
    APP_NAME,
    BRAND_ICE,
    IS_ANDROID,
    STAGE_COLORS,
    SURFACE_DARK,
    TEMP_HIGH_ERROR_C,
    TEMP_HIGH_STRONG_WARNING_C,
    TEMP_HIGH_WARNING_C,
    TEMP_LOW_STRONG_WARNING_C,
    TEMP_LOW_WARNING_C,
)
from tpof.mobile.entitlements import (
    FREE_PRODUCTS_PER_CATEGORY,
    MODULE_VALVES,
    Entitlements,
)
from tpof.mobile.i18n import display_category, translate
from tpof.mobile.layout import clamp, compute_metrics
from tpof.mobile.paths import DATA_PATH
from tpof.mobile.pdf_export import _pdf_output_dir
from tpof.mobile.services.entitlements_ui import _sync_module_ownership
from tpof.mobile.user_data import CustomProductStore, UiPreferences, create_custom_product
from tpof.mobile.validation import _numeric_input_filter

log = logging.getLogger(__name__)

def main() -> None:
    """Punkt wejścia mobilnej aplikacji."""
    try:
        from kivy.clock import Clock
        from kivy.core.window import Window
        from kivy.graphics import Color, Rectangle
        from kivy.metrics import dp
        from kivy.uix.floatlayout import FloatLayout
        from kivy.uix.image import AsyncImage
        from kivymd.app import MDApp
        from kivymd.uix.boxlayout import MDBoxLayout
        from kivymd.uix.button import MDIconButton, MDRaisedButton
        from kivymd.uix.card import MDCard
        from kivymd.uix.label import MDIcon, MDLabel
        from kivymd.uix.menu import MDDropdownMenu
        from kivymd.uix.progressbar import MDProgressBar
        from kivymd.uix.scrollview import MDScrollView
        from kivymd.uix.textfield import MDTextField

        from tpof.mobile.widgets import (
            BottomNavTab,
            BrandToolbar,
            CenterNotice,
            FrostBackground,
            FrostChip,
            StageIconBadge,
            StageMotionIcon,
        )
    except ImportError as exc:  # pragma: no cover
        raise SystemExit(
            "KivyMD nie jest zainstalowane. Uruchom:\n"
            "    python -m pip install -r requirements-mobile.txt"
        ) from exc

    # Rejestracja fontu DejaVuSans (pełen Unicode — subscripty, symbole).
    try:
        from kivy.core.text import LabelBase

        runtime_font = _runtime_font_path()
        if runtime_font is not None:
            LabelBase.register(name="DejaVuSans", fn_regular=str(runtime_font))
            log.info("Zarejestrowano font DejaVuSans z %s", runtime_font)
    except Exception:  # pragma: no cover
        log.exception("Nie udało się zarejestrować fontu DejaVuSans")

    telemetry.install_exception_hook()
    catalog: dict[str, list[Product]] = load_products(DATA_PATH)
    custom_products = CustomProductStore()
    custom_products.merge_into(catalog)
    categories = list_categories(catalog)



    class ShockerCalcApp(MDApp):
        def build(self):
            self.title = APP_NAME
            self.theme_cls.primary_palette = "Blue"
            self.theme_cls.primary_hue = "600"
            self.theme_cls.accent_palette = "Cyan"
            self.theme_cls.theme_style = "Dark"
            try:
                self.theme_cls.material_style = "M3"
            except Exception:  # pragma: no cover - starsze KivyMD
                pass
            Window.clearcolor = SURFACE_DARK

            self._selected_category: str | None = None
            self._selected_product: str | None = None
            self._mass_unit: str = "kg"
            self._cat_menu: MDDropdownMenu | None = None
            self._prod_menu: MDDropdownMenu | None = None
            self._product_dialog = None
            self._product_search_field = None
            self._product_results_list = None
            self._product_dialog_names: list[str] = []
            self._product_dialog_indexes: dict[str, int] = {}
            self._last_results = None
            self._themed_cards = []
            self._language = "pl"
            self._preferences = UiPreferences()
            self._hints_enabled = self._preferences.hints_enabled
            self._unit_system = self._preferences.unit_system
            self._custom_product_dialog = None
            self._privacy_dialog = None
            self._settings_dialog = None
            self._telemetry_dialog = None
            self._labor_rate_dialog = None
            self._labor_rate_fields = {}
            self._validation_bound_fields = set()
            self._native_ad_height_dp = 0
            self._pro_no_ads = False
            self._pro_thanks_shown = False
            self._valve_type = "Maxi Elebar"
            self._valve_input_mode = "K"  # "K" = kubatura, "W" = wymiary
            self._last_valve_results = None
            self._valve_menu: MDDropdownMenu | None = None
            self._labor_use_highways = False
            self._labor_has_additional = False
            self._last_labor_breakdown = None
            self._entitlements = Entitlements()
            self._entitlements.ensure_started()

            self.root_host = FloatLayout()
            with self.root_host.canvas.before:
                self._root_bg_color = Color(*SURFACE_DARK)
                self._root_bg_rect = Rectangle(pos=(0, 0), size=Window.size)
            self.root_host.bind(pos=self._sync_root_background, size=self._sync_root_background)
            self.frost_background = FrostBackground()
            self.root_layout = MDBoxLayout(
                orientation="vertical",
                md_bg_color=(0, 0, 0, 0),
                size_hint=(1, 1),
            )
            self.root_host.add_widget(self.frost_background)
            self.root_host.add_widget(self.root_layout)
            root = self.root_layout

            self.toolbar = self._build_toolbar(dp, MDBoxLayout, MDIcon, MDIconButton, MDLabel)
            root.add_widget(self.toolbar)

            self.scroll = MDScrollView()
            self.content = MDBoxLayout(
                orientation="vertical",
                padding=[dp(16), dp(14), dp(16), dp(18)],
                spacing=dp(14),
                size_hint_y=None,
            )
            content = self.content
            content.bind(minimum_height=content.setter("height"))

            content.add_widget(
                self._build_product_card(dp, MDCard, MDBoxLayout, MDIcon, MDLabel, MDRaisedButton, AsyncImage)
            )
            content.add_widget(self._build_params_card(dp, MDCard, MDBoxLayout, MDLabel, MDTextField, MDRaisedButton))
            self.results_card = self._build_results_card(
                dp, MDCard, MDBoxLayout, MDIcon, MDLabel, MDProgressBar, MDRaisedButton
            )
            content.add_widget(self.results_card)

            self.scroll.add_widget(content)
            self.scroll.size_hint = (1, 1)

            # Własny host zakładek: tło pozostaje widoczne, a dolny pasek nie
            # może już zapadać obszaru treści jak MDBottomNavigation.
            self.tab_content_host = FloatLayout(size_hint=(1, 1))
            self.tab_frost_background = FrostBackground(size_hint=(1, 1))
            self.tab_content_host.add_widget(self.tab_frost_background)
            self.valve_scroll = self._build_valve_tab(
                dp, MDScrollView, MDCard, MDBoxLayout, MDLabel, MDTextField, MDRaisedButton
            )
            self.valve_scroll.size_hint = (1, 1)
            self.labor_scroll = self._build_labor_tab(
                dp, MDScrollView, MDCard, MDBoxLayout, MDLabel, MDTextField, MDRaisedButton
            )
            self.labor_scroll.size_hint = (1, 1)
            self.tab_content_host.add_widget(self.scroll)
            self.tab_content_host.add_widget(self.valve_scroll)
            self.tab_content_host.add_widget(self.labor_scroll)
            root.add_widget(self.tab_content_host)

            self.bottom_nav = self._build_bottom_nav(dp, MDBoxLayout)
            root.add_widget(self.bottom_nav)
            self._active_tab_name = "freezing"
            self._show_tab("freezing", animate=False, report=False)

            root.add_widget(self._build_footer(dp, MDBoxLayout, MDLabel, MDRaisedButton))
            root.add_widget(self._build_ad_slot(dp, MDBoxLayout, MDIcon, MDLabel))
            self.center_notice = CenterNotice()
            self.root_host.add_widget(self.center_notice)
            self._sync_theme_surfaces()
            Window.bind(size=self._apply_responsive_layout)
            self._apply_responsive_layout()
            Clock.schedule_once(lambda *_: self._refresh_pro_status(), 0.8)
            Clock.schedule_once(lambda *_: self._refresh_pro_status(), 3.0)
            Clock.schedule_once(lambda *_: self._refresh_ad_slot_height(), 1.2)
            Clock.schedule_once(lambda *_: self._refresh_ad_slot_height(), 3.5)
            Clock.schedule_once(lambda *_: self._refresh_ad_slot_height(), 7.0)
            Clock.schedule_once(lambda *_: self._refresh_privacy_button(), 3.0)
            Clock.schedule_once(lambda *_: self._refresh_privacy_button(), 8.0)
            Clock.schedule_once(lambda *_: self._refresh_valve_lock_ui(), 1.0)
            Clock.schedule_once(lambda *_: self._refresh_valve_lock_ui(), 4.0)
            Clock.schedule_once(lambda *_: self._apply_hints(), 0.2)
            Clock.schedule_once(lambda *_: self._prompt_telemetry_consent(), 2.0)
            telemetry.log_event("app_started", {"language": self._language})
            return self.root_host

        # --- tekst / stan aplikacji -------------------------------------
        def _sync_root_background(self, *_args):
            if hasattr(self, "_root_bg_rect"):
                self._root_bg_rect.pos = self.root_host.pos
                self._root_bg_rect.size = self.root_host.size

        def _t(self, key: str, **kwargs) -> str:
            return translate(self._language, key, **kwargs)

        def _toggle_language(self):
            self._close_product_dialog()
            self._language = "en" if self._language == "pl" else "pl"
            self._refresh_texts()

        def _toggle_hints(self):
            self._hints_enabled = not self._hints_enabled
            self._preferences.set_hints_enabled(self._hints_enabled)
            self._apply_hints()
            self._apply_responsive_layout()
            self._show_error(self._t("hints_on" if self._hints_enabled else "hints_off"))
            telemetry.log_event("hints_toggled", {"enabled": self._hints_enabled})

        def _hint_field_items(self):
            return [
                (getattr(self, "in_m", None), "hint_mass"),
                (getattr(self, "in_T1", None), "hint_temp_start"),
                (getattr(self, "in_T2", None), "hint_temp_end"),
                (getattr(self, "in_t", None), "hint_time"),
                (getattr(self, "valve_in_V", None), "hint_valve_volume"),
                (getattr(self, "valve_in_L", None), "hint_valve_length"),
                (getattr(self, "valve_in_W", None), "hint_valve_width"),
                (getattr(self, "valve_in_H", None), "hint_valve_height"),
                (getattr(self, "valve_in_tp", None), "hint_valve_temp_before"),
                (getattr(self, "valve_in_tz", None), "hint_valve_temp_after"),
                (getattr(self, "valve_in_n", None), "hint_valve_coolers"),
                (getattr(self, "valve_in_q", None), "hint_valve_flow"),
                (getattr(self, "labor_in_people", None), "hint_labor_people"),
                (getattr(self, "labor_in_days", None), "hint_labor_days"),
                (getattr(self, "labor_in_distance", None), "hint_labor_distance"),
                (getattr(self, "labor_in_lifts", None), "hint_labor_lifts"),
                (getattr(self, "labor_in_containers", None), "hint_labor_containers"),
                (getattr(self, "labor_in_additional", None), "hint_labor_additional"),
            ]

        def _apply_hints(self):
            if hasattr(self, "btn_hints"):
                self.btn_hints.icon = (
                    "lightbulb-on-outline"
                    if self._hints_enabled
                    else "lightbulb-off-outline"
                )
                self.btn_hints.text_color = (
                    BRAND_ICE
                    if self._hints_enabled
                    else (0.93, 0.98, 1.0, 0.94)
                )
            if hasattr(self, "btn_hints_chip"):
                self.btn_hints_chip.set_active(self._hints_enabled)
            if hasattr(self, "lbl_product_hint"):
                self.lbl_product_hint.text = self._t("product_hint")
            for field, hint_key in self._hint_field_items():
                if field is None:
                    continue
                field_id = id(field)
                if field_id not in self._validation_bound_fields:
                    field.bind(text=lambda widget, _value: self._clear_field_error(widget))
                    self._validation_bound_fields.add(field_id)
                if not getattr(field, "error", False):
                    field.helper_text = self._t(hint_key) if self._hints_enabled else ""
                    # KivyMD 1.2.0 nie obsluguje trybu "none". Pusty tekst w
                    # prawidlowym trybie on_focus daje ten sam efekt wizualny.
                    field.helper_text_mode = "on_focus"

        def _clear_field_error(self, field):
            if not getattr(field, "error", False):
                return
            field.error = False
            hint_key = next(
                (key for candidate, key in self._hint_field_items() if candidate is field),
                None,
            )
            field.helper_text = (
                self._t(hint_key) if self._hints_enabled and hint_key else ""
            )
            field.helper_text_mode = "on_focus"

        def _mark_field_error(self, field, message: str | None = None):
            field.error = True
            field.helper_text = message or self._t("field_required")
            field.helper_text_mode = "on_error"

        def _parse_required_field(self, field, name: str) -> float:
            raw = (getattr(field, "text", "") or "").strip()
            if not raw:
                self._mark_field_error(field)
                raise ValueError(self._t("invalid_field", name=name))
            try:
                return float(raw.replace(",", "."))
            except (TypeError, ValueError, AttributeError) as exc:
                self._mark_field_error(field, self._t("invalid_field", name=name))
                raise ValueError(self._t("invalid_field", name=name)) from exc

        def _temperature_warning(self, field_name: str, value: float) -> str | None:
            if value >= TEMP_HIGH_STRONG_WARNING_C:
                return self._t(
                    "temperature_warning_high_strong",
                    field=field_name,
                    value=value,
                )
            if value >= TEMP_HIGH_WARNING_C:
                return self._t(
                    "temperature_warning_high",
                    field=field_name,
                    value=value,
                )
            if value <= TEMP_LOW_STRONG_WARNING_C:
                return (
                    self._t(
                        "temperature_warning_low_strong",
                        field=field_name,
                        value=value,
                    )
                    + " "
                    + self._t("temperature_warning_co2")
                )
            if value <= TEMP_LOW_WARNING_C:
                return self._t(
                    "temperature_warning_low",
                    field=field_name,
                    value=value,
                )
            return None

        def _validate_temperature_input(self, field, field_name: str, value: float) -> str | None:
            if value < ABSOLUTE_ZERO_C:
                message = self._t("temperature_error_absolute", field=field_name)
                self._mark_field_error(field, message)
                raise ValueError(message)
            if value > TEMP_HIGH_ERROR_C:
                message = self._t(
                    "temperature_error_high",
                    field=field_name,
                    limit=TEMP_HIGH_ERROR_C,
                )
                self._mark_field_error(field, message)
                raise ValueError(message)
            return self._temperature_warning(field_name, value)

        def _clear_main_validation(self):
            for line in (
                getattr(self, "category_error_line", None),
                getattr(self, "product_error_line", None),
            ):
                if line is not None:
                    line.opacity = 0
            for field in (
                getattr(self, "in_m", None),
                getattr(self, "in_T1", None),
                getattr(self, "in_T2", None),
                getattr(self, "in_t", None),
            ):
                if field is not None:
                    self._clear_field_error(field)

        def _clear_valve_validation(self):
            for field in (
                getattr(self, "valve_in_V", None),
                getattr(self, "valve_in_L", None),
                getattr(self, "valve_in_W", None),
                getattr(self, "valve_in_H", None),
                getattr(self, "valve_in_tp", None),
                getattr(self, "valve_in_tz", None),
                getattr(self, "valve_in_n", None),
                getattr(self, "valve_in_q", None),
            ):
                if field is not None:
                    self._clear_field_error(field)

        def _total_text(self, total: float | None = None) -> str:
            value = "—" if total is None else f"{total:.2f}"
            return self._t("total_power", value=value)

        def _ad_label_text(self) -> str:
            if self._pro_no_ads:
                return self._t("pro_ads_off")
            return self._t("ad") if IS_ANDROID else self._t("ad_placeholder")

        def _status_footer_text(self) -> str:
            from tpof import __version__ as _app_version

            base = f"{APP_NAME} v{_app_version}  |  Sebastian Milczarek"
            if self._pro_no_ads:
                return f"{base}\n{self._t('pro_unlocked_footer')}"
            if self._entitlements.is_trial_active():
                days = self._entitlements.trial_days_left()
                if days <= 1:
                    return f"{base}\n{self._t('trial_last_day')}"
                return f"{base}\n{self._t('trial_active', days=days)}"
            return f"{base}\n{self._t('trial_expired')}"

        def _screen_dp(self, dp):
            unit = max(float(dp(1)), 1.0)
            return Window.width / unit, Window.height / unit

        def _clamp(self, value: float, min_value: float, max_value: float) -> float:
            return clamp(value, min_value, max_value)

        def _layout_metrics(self, dp):
            width_dp, height_dp = self._screen_dp(dp)
            return compute_metrics(
                dp,
                width_dp,
                height_dp,
                hints_enabled=self._hints_enabled,
                native_ad_height_dp=getattr(self, "_native_ad_height_dp", 0),
            )

        def _apply_responsive_layout(self, *_):
            from kivy.metrics import dp

            m = self._layout_metrics(dp)
            card_padding = [
                m["card_pad_x"],
                m["card_pad_top"],
                m["card_pad_x"],
                m["card_pad_bottom"],
            ]
            if hasattr(self, "content"):
                self.content.padding = [
                    m["content_pad"],
                    m["content_top"],
                    m["content_pad"],
                    m["content_bottom"],
                ]
                self.content.spacing = m["content_spacing"]

            if hasattr(self, "toolbar"):
                self.toolbar.height = m["toolbar_h"]
                self.toolbar.padding = [m["content_pad"], 0, dp(6 if m["compact"] else 8), 0]
            if hasattr(self, "toolbar_brand_chip"):
                self.toolbar_brand_chip.width = m["toolbar_icon_w"]
                self.toolbar_brand_chip.height = m["toolbar_icon_w"]
            if hasattr(self, "toolbar_snowflake"):
                self.toolbar_snowflake.width = m["toolbar_icon_w"]
                self.toolbar_snowflake.icon_size = f'{m["toolbar_icon_sp"]}sp'
            if hasattr(self, "lbl_toolbar_title"):
                self.lbl_toolbar_title.font_size = f'{m["toolbar_title_sp"]}sp'
                self.lbl_toolbar_title.line_height = 0.88
            for chip in (
                getattr(self, "btn_hints_chip", None),
                getattr(self, "btn_lang_chip", None),
                getattr(self, "btn_theme_chip", None),
                getattr(self, "btn_privacy_chip", None),
            ):
                if chip is not None and getattr(chip, "opacity", 1) > 0:
                    chip.width = m["toolbar_btn_w"]
                    chip.height = m["toolbar_btn_w"]
            for btn in (
                getattr(self, "btn_hints", None),
                getattr(self, "btn_lang", None),
                getattr(self, "btn_theme", None),
                getattr(self, "btn_privacy", None),
            ):
                if btn is not None:
                    btn.width = m["toolbar_btn_w"]
                    btn.icon_size = f'{m["toolbar_btn_sp"]}sp'
            if hasattr(self, "btn_privacy"):
                self._refresh_privacy_button()

            if hasattr(self, "tab_content_host"):
                self.tab_content_host.size_hint_y = 1
            if hasattr(self, "bottom_nav"):
                self.bottom_nav.size_hint_y = None
                self.bottom_nav.height = m["bottom_nav_h"]
                self.bottom_nav.padding = [
                    m["content_pad"],
                    dp(3),
                    m["content_pad"],
                    dp(3),
                ]
                self.bottom_nav.spacing = dp(8 if m["compact"] else 10)
                self.bottom_nav.md_bg_color = self._bottom_nav_bg()
            for tab in (
                getattr(self, "bottom_freezing_tab", None),
                getattr(self, "bottom_valves_tab", None),
                getattr(self, "bottom_labor_tab", None),
            ):
                if tab is not None:
                    tab.set_metrics(
                        icon_size=m["bottom_tab_icon"],
                        label_sp=m["bottom_tab_sp"],
                    )

            if hasattr(self, "product_card"):
                self.product_card.padding = card_padding
                self.product_card.spacing = dp(10 if m["compact"] else 12)
                self.product_card.height = m["product_card_h"]
            if hasattr(self, "lbl_product_title"):
                self.lbl_product_title.height = m["title_h"]
                self.lbl_product_title.font_size = f'{m["title_sp"]}sp'
            if hasattr(self, "product_title_row"):
                self.product_title_row.height = m["title_h"]
            if hasattr(self, "btn_add_product"):
                self.btn_add_product.width = m["toolbar_btn_w"]
                self.btn_add_product.icon_size = f'{m["toolbar_btn_sp"]}sp'
            if hasattr(self, "lbl_product_hint"):
                self.lbl_product_hint.height = m["product_hint_h"]
                self.lbl_product_hint.opacity = 1 if self._hints_enabled else 0
                self.lbl_product_hint.font_size = f'{m["caption_sp"]}sp'
            if hasattr(self, "product_body"):
                self.product_body.orientation = "horizontal" if m["product_horizontal"] else "vertical"
                self.product_body.height = m["product_body_h"]
                self.product_body.spacing = m["product_body_spacing"]
            if hasattr(self, "product_controls"):
                self.product_controls.spacing = dp(10 if m["compact"] else 12)
                self.product_controls.size_hint_x = 0.46 if m["product_horizontal"] else 1
                self.product_controls.size_hint_y = 1 if m["product_horizontal"] else None
                self.product_controls.height = m["product_controls_h"]
                self.product_controls.padding = [0, dp(6 if m["compact"] else 8), 0, dp(6 if m["compact"] else 8)]
            if hasattr(self, "image_box"):
                self.image_box.size_hint_x = 0.54 if m["product_horizontal"] else 1
                self.image_box.size_hint_y = 1 if m["product_horizontal"] else None
                self.image_box.height = m["product_image_h"]
            if hasattr(self, "image_placeholder"):
                self.image_placeholder.padding = [
                    0,
                    m["placeholder_top"],
                    0,
                    m["placeholder_bottom"],
                ]
            if hasattr(self, "image_placeholder_icon"):
                self.image_placeholder_icon.font_size = f'{m["placeholder_icon_sp"]}sp'
            if hasattr(self, "image_placeholder_label"):
                self.image_placeholder_label.font_size = f'{m["caption_sp"]}sp'

            for btn in (getattr(self, "btn_category", None), getattr(self, "btn_product", None)):
                if btn is not None:
                    btn.height = m["button_h"]
                    btn.font_size = f'{m["button_sp"]}sp'
            for box in (
                getattr(self, "category_field_box", None),
                getattr(self, "product_field_box", None),
            ):
                if box is not None:
                    box.height = m["button_h"] + dp(2)

            if hasattr(self, "params_card"):
                self.params_card.padding = card_padding
                self.params_card.spacing = m["card_spacing"]
                self.params_card.height = m["params_h"]
            if hasattr(self, "lbl_params_title"):
                self.lbl_params_title.height = m["title_h"]
                self.lbl_params_title.font_size = f'{m["title_sp"]}sp'
            if hasattr(self, "row_mass"):
                self.row_mass.height = m["field_h"] + dp(8)
                self.row_mass.spacing = dp(8 if m["compact"] else 10)
            if hasattr(self, "btn_unit"):
                self.btn_unit.width = m["unit_w"]
                self.btn_unit.height = m["unit_h"]
                self.btn_unit.font_size = f'{m["body_sp"]}sp'
            for field_ in [
                getattr(self, "in_m", None),
                getattr(self, "in_T1", None),
                getattr(self, "in_T2", None),
                getattr(self, "in_t", None),
            ]:
                if field_ is not None:
                    field_.height = m["field_h"]
                    field_.font_size = f'{m["body_sp"]}sp'

            if hasattr(self, "results_card"):
                self.results_card.padding = card_padding
                self.results_card.spacing = m["results_spacing"]
                self.results_card.height = m["results_h"]
            if hasattr(self, "results_title_row"):
                self.results_title_row.height = m["title_h"]
            if hasattr(self, "lbl_results_title"):
                self.lbl_results_title.font_size = f'{m["title_sp"]}sp'
            if hasattr(self, "action_row"):
                self.action_row.height = m["action_h"]
                self.action_row.spacing = dp(6 if m["compact"] else 8)
                self.action_row.padding = [0, dp(8 if m["compact"] else 9), 0, dp(7 if m["compact"] else 8)]
            for btn in [
                getattr(self, "btn_calc", None),
                getattr(self, "btn_pdf", None),
                getattr(self, "btn_clear", None),
            ]:
                if btn is not None:
                    btn.height = m["action_button_h"]
                    btn.font_size = f'{m["action_sp"]}sp'
            if hasattr(self, "lbl_total"):
                self.lbl_total.height = m["total_h"]
                self.lbl_total.font_size = f'{m["total_sp"]}sp'
            for entry in getattr(self, "bars", {}).values():
                entry["row"].height = m["stage_row_h"]
                entry["head"].height = m["stage_head_h"]
                entry["icon_chip"].width = m["stage_icon_w"]
                entry["icon_chip"].height = m["stage_icon_w"]
                if hasattr(entry["icon"], "font_size"):
                    entry["icon"].font_size = f'{m["stage_icon_sp"]}sp'
                entry["name_label"].font_size = f'{m["body_sp"]}sp'
                entry["value_label"].font_size = f'{m["body_sp"]}sp'
            if hasattr(self, "footer_bar"):
                self.footer_bar.height = m["footer_h"]
                self.footer_bar.padding = [m["content_pad"], dp(3), m["content_pad"], dp(3)]
                self.footer_bar.spacing = dp(10 if m["compact"] else 12)
            if hasattr(self, "footer_label"):
                self.footer_label.font_size = f'{m["footer_sp"]}sp'
                self.footer_label.shorten = True
            if hasattr(self, "btn_pro"):
                self.btn_pro.width = m["pro_w"]
                self.btn_pro.height = m["pro_h"]
                self.btn_pro.font_size = f'{m["caption_sp"]}sp'
            if hasattr(self, "ad_slot") and not self._pro_no_ads:
                self.ad_slot.height = m["ad_h"]
                self.ad_slot.padding = [m["content_pad"], dp(2), m["content_pad"], dp(2)]
            if hasattr(self, "ad_label"):
                self.ad_label.font_size = f'{m["caption_sp"]}sp'

        def _refresh_texts(self):
            if hasattr(self, "lbl_toolbar_title"):
                self.lbl_toolbar_title.text = "Refrigeration\nCalc"
            if hasattr(self, "btn_theme"):
                self.btn_theme.icon = "weather-night" if self.theme_cls.theme_style == "Dark" else "weather-sunny"
            if hasattr(self, "lbl_product_title"):
                self.lbl_product_title.text = self._t("product")
            if hasattr(self, "btn_category"):
                self.btn_category.text = (
                    self._display_category(self._selected_category)
                    if self._selected_category
                    else self._t("choose_category")
                )
            if hasattr(self, "btn_product"):
                self.btn_product.text = self._selected_product or self._t("choose_product")
            if hasattr(self, "image_placeholder_label"):
                self.image_placeholder_label.text = self._t("image_placeholder")
            if hasattr(self, "lbl_product_hint"):
                self.lbl_product_hint.text = self._t("product_hint")
            if hasattr(self, "lbl_params_title"):
                self.lbl_params_title.text = self._t("params")
            if hasattr(self, "in_m"):
                self.in_m.hint_text = self._t("mass")
                self.in_T1.hint_text = self._t("temperature_start")
                self.in_T2.hint_text = self._t("temperature_end")
                self.in_t.hint_text = self._t("work_time")
            if hasattr(self, "btn_calc"):
                self.btn_calc.text = self._t("calculate")
                self.btn_clear.text = self._t("clear")
            if hasattr(self, "lbl_results_title"):
                self.lbl_results_title.text = self._t("result")
                for key, label_key in [
                    ("schladzanie", "cooling"),
                    ("zamrozenie", "freezing"),
                    ("domrozenie", "deep_freezing"),
                ]:
                    if key in self.bars:
                        self.bars[key]["name_label"].text = self._t(label_key)
            if self._last_results is not None:
                self._render_results(self._last_results, scroll=False)
            elif hasattr(self, "lbl_total"):
                self.lbl_total.text = self._total_text()
            if hasattr(self, "ad_label"):
                self.ad_label.text = self._ad_label_text()
            if hasattr(self, "bottom_freezing_tab"):
                self.bottom_freezing_tab.set_text(self._t("nav_freezing"))
            if hasattr(self, "bottom_valves_tab"):
                self.bottom_valves_tab.set_text(self._t("nav_valves"))
            if hasattr(self, "bottom_labor_tab"):
                self.bottom_labor_tab.set_text(self._t("nav_labor"))
            if hasattr(self, "labor_lbl_title"):
                self.labor_lbl_title.text = self._t("labor_title")
                self.labor_lbl_hint.text = self._t("labor_hint")
                self.labor_in_people.hint_text = self._t("labor_people")
                self.labor_in_days.hint_text = self._t("labor_days")
                self.labor_in_distance.hint_text = self._t("labor_distance")
                self.labor_in_lifts.hint_text = self._t("labor_lifts")
                self.labor_in_containers.hint_text = self._t("labor_containers")
                self.labor_in_additional.hint_text = self._t("labor_additional")
                self.labor_btn_rates.text = self._t("labor_rates_button")
                self.labor_btn_calc.text = self._t("labor_calculate")
                self.labor_lbl_result.text = self._t("labor_result")
                self._set_labor_highways(self._labor_use_highways)
                self._set_labor_additional_enabled(self._labor_has_additional)
                self._render_labor_results(self._last_labor_breakdown)
            if hasattr(self, "valve_lbl_title"):
                self.valve_lbl_title.text = self._t("valve_title")
                self.valve_btn_mode_k.text = self._t("valve_mode_volume")
                self.valve_btn_mode_w.text = self._t("valve_mode_dims")
                self.valve_in_V.hint_text = self._t("valve_volume")
                self.valve_in_L.hint_text = self._t("valve_length")
                self.valve_in_W.hint_text = self._t("valve_width")
                self.valve_in_H.hint_text = self._t("valve_height")
                self.valve_in_tp.hint_text = self._t("valve_temp_before")
                self.valve_in_tz.hint_text = self._t("valve_temp_after")
                self.valve_in_n.hint_text = self._t("valve_coolers")
                self.valve_in_q.hint_text = self._t("valve_flow_per")
                self.valve_btn_calc.text = self._t("valve_calculate")
                self.valve_lbl_result.text = self._t("valve_result")
                if hasattr(self, "valve_lbl_locked"):
                    self.valve_lbl_locked.text = self._t("valve_locked")
                    self.valve_btn_buy.text = self._t("valve_buy")
                    self.valve_btn_watch.text = self._t("valve_watch_ad")
                if self._last_valve_results is not None:
                    self._render_valve_results(self._last_valve_results)
                else:
                    self.valve_lbl_count.text = self._t("valve_count", value="—")
                    self.valve_lbl_delta.text = self._t("valve_delta_t", value="—")
                    self.valve_lbl_totalflow.text = self._t("valve_total_flow", value="—")
                    self.valve_lbl_flow.text = self._t("valve_flow", value="—")
                    self.valve_lbl_unitflow.text = self._t("valve_unit_flow", value="—")
            self._set_pro_status(self._pro_no_ads)
            self._apply_hints()

        def _display_category(self, category: str | None) -> str:
            return display_category(self._language, category)

        def _menu_bg_color(self):
            return theme.menu_bg_color(self.theme_cls.theme_style == "Dark")

        def _menu_text_color(self):
            return theme.menu_text_color(self.theme_cls.theme_style == "Dark")

        def _menu(self, caller, items, width_mult, max_height, dp, MDDropdownMenu):
            width_dp, height_dp = self._screen_dp(dp)
            desired_width = min(width_mult * 56.0, max(180.0, width_dp - 32.0))
            width_mult = self._clamp(desired_width / 56.0, 2.8, 5.0)
            max_height = min(max_height, dp(max(220.0, height_dp * 0.58)))
            menu = MDDropdownMenu(
                caller=caller,
                items=items,
                width_mult=width_mult,
                max_height=max_height,
            )
            for attr, value in [
                ("background_color", self._menu_bg_color()),
                ("radius", [dp(14), dp(14), dp(14), dp(14)]),
                ("border_margin", dp(14)),
                ("opening_time", 0.12),
                ("position", "bottom"),
                ("ver_growth", "down"),
                ("hor_growth", "right"),
            ]:
                try:
                    setattr(menu, attr, value)
                except Exception:
                    pass
            return menu

        # --- karty -------------------------------------------------------
        def _toolbar_chip_button(
            self,
            dp,
            MDIconButton,
            *,
            icon: str,
            icon_size: str,
            on_release,
            active: bool = False,
            size_dp: int = 44,
        ):
            chip = FrostChip(
                active=active,
                size_hint_x=None,
                size_hint_y=None,
                width=dp(size_dp),
                height=dp(size_dp),
            )
            button = MDIconButton(
                icon=icon,
                size_hint=(1, 1),
                width=dp(size_dp),
                icon_size=icon_size,
                theme_text_color="Custom",
                text_color=BRAND_ICE if active else (0.93, 0.98, 1.0, 0.94),
                on_release=on_release,
            )
            chip.add_widget(button)
            return chip, button

        def _build_toolbar(self, dp, MDBoxLayout, MDIcon, MDIconButton, MDLabel):
            bar = BrandToolbar(
                orientation="horizontal",
                size_hint_y=None,
                height=dp(72),
                padding=[dp(14), 0, dp(8), 0],
                spacing=dp(5),
            )
            self.toolbar_brand_chip = FrostChip(
                active=True,
                size_hint_x=None,
                size_hint_y=None,
                width=dp(44),
                height=dp(44),
            )
            self.toolbar_snowflake = MDIconButton(
                icon="snowflake",
                size_hint=(1, 1),
                width=dp(44),
                icon_size="28sp",
                theme_text_color="Custom",
                text_color=BRAND_ICE,
                on_release=lambda *_: self._open_settings_dialog(),
            )
            self.toolbar_brand_chip.add_widget(self.toolbar_snowflake)
            bar.add_widget(self.toolbar_brand_chip)
            self.lbl_toolbar_title = MDLabel(
                text="Refrigeration\nCalc",
                halign="center",
                valign="middle",
                font_style="Subtitle1",
                font_size="16sp",
                line_height=0.88,
                shorten=False,
                theme_text_color="Custom",
                text_color=(1, 1, 1, 1),
            )
            bar.add_widget(self.lbl_toolbar_title)
            self.btn_hints_chip, self.btn_hints = self._toolbar_chip_button(
                dp,
                MDIconButton,
                icon="lightbulb-on-outline" if self._hints_enabled else "lightbulb-off-outline",
                icon_size="26sp",
                active=self._hints_enabled,
                on_release=lambda *_: self._toggle_hints(),
            )
            self.btn_lang_chip, self.btn_lang = self._toolbar_chip_button(
                dp,
                MDIconButton,
                icon="translate",
                icon_size="28sp",
                on_release=lambda *_: self._toggle_language(),
            )
            self.btn_theme_chip, self.btn_theme = self._toolbar_chip_button(
                dp,
                MDIconButton,
                icon="weather-night",
                icon_size="28sp",
                on_release=lambda *_: self._toggle_theme(),
            )
            bar.add_widget(self.btn_hints_chip)
            bar.add_widget(self.btn_lang_chip)
            bar.add_widget(self.btn_theme_chip)
            self.btn_privacy_chip, self.btn_privacy = self._toolbar_chip_button(
                dp,
                MDIconButton,
                icon="shield-account",
                icon_size="26sp",
                on_release=lambda *_: self._open_privacy_options(),
            )
            bar.add_widget(self.btn_privacy_chip)
            self._refresh_privacy_button()
            return bar

        def _build_bottom_nav(self, dp, MDBoxLayout):
            """Kompaktowy pasek zakladek z lekkimi animacjami ikon."""
            nav = MDBoxLayout(
                orientation="horizontal",
                size_hint_y=None,
                height=dp(70),
                padding=[dp(16), dp(3), dp(16), dp(3)],
                spacing=dp(8),
                md_bg_color=self._bottom_nav_bg(),
            )
            self.bottom_freezing_tab = BottomNavTab(
                name="freezing",
                text=self._t("nav_freezing"),
                mode="snowflake",
                on_select=lambda name: self._show_tab(name),
            )
            self.bottom_valves_tab = BottomNavTab(
                name="valves",
                text=self._t("nav_valves"),
                mode="valve",
                on_select=lambda name: self._show_tab(name),
            )
            self.bottom_labor_tab = BottomNavTab(
                name="labor",
                text=self._t("nav_labor"),
                mode="calculator",
                on_select=lambda name: self._show_tab(name),
            )
            nav.add_widget(self.bottom_freezing_tab)
            nav.add_widget(self.bottom_valves_tab)
            nav.add_widget(self.bottom_labor_tab)
            return nav

        def _card_bg(self):
            return theme.card_bg(self.theme_cls.theme_style == "Dark")

        def _surface_bg(self):
            return theme.surface_bg(self.theme_cls.theme_style == "Dark")

        def _bottom_nav_bg(self):
            return theme.bottom_nav_bg(self.theme_cls.theme_style == "Dark")

        def _footer_bg(self):
            return theme.footer_bg(self.theme_cls.theme_style == "Dark")

        def _ad_slot_bg(self):
            return theme.ad_slot_bg(self.theme_cls.theme_style == "Dark")

        def _style_app_button(self, button, variant: str = "primary"):
            theme.style_app_button(button, variant)

        def _sync_theme_surfaces(self):
            surface = self._surface_bg()
            Window.clearcolor = surface
            if hasattr(self, "_root_bg_color"):
                self._root_bg_color.rgba = surface
            self.root_layout.md_bg_color = (0, 0, 0, 0)
            if hasattr(self, "frost_background"):
                self.frost_background.set_dark(
                    self.theme_cls.theme_style == "Dark"
                )
            if hasattr(self, "tab_frost_background"):
                self.tab_frost_background.set_dark(
                    self.theme_cls.theme_style == "Dark"
                )
            if hasattr(self, "bottom_nav"):
                self.bottom_nav.md_bg_color = self._bottom_nav_bg()
            active_tab = getattr(self, "_active_tab_name", "freezing")
            if hasattr(self, "bottom_freezing_tab"):
                self.bottom_freezing_tab.set_theme_light(
                    self.theme_cls.theme_style != "Dark"
                )
                self.bottom_freezing_tab.set_active(active_tab == "freezing")
            if hasattr(self, "bottom_valves_tab"):
                self.bottom_valves_tab.set_theme_light(
                    self.theme_cls.theme_style != "Dark"
                )
                self.bottom_valves_tab.set_active(active_tab == "valves")
            if hasattr(self, "bottom_labor_tab"):
                self.bottom_labor_tab.set_theme_light(
                    self.theme_cls.theme_style != "Dark"
                )
                self.bottom_labor_tab.set_active(active_tab == "labor")
            for card in self._themed_cards:
                card.md_bg_color = self._card_bg()
            ad_slot = getattr(self, "ad_slot", None)
            if ad_slot is not None:
                ad_slot.md_bg_color = self._ad_slot_bg()
            footer_bar = getattr(self, "footer_bar", None)
            if footer_bar is not None:
                footer_bar.md_bg_color = self._footer_bg()
            if hasattr(self, "btn_unit"):
                self._set_mass_unit(self._mass_unit)
            for button, variant in (
                (getattr(self, "btn_category", None), "primary"),
                (getattr(self, "btn_product", None), "primary"),
                (getattr(self, "btn_calc", None), "primary"),
                (getattr(self, "btn_pdf", None), "ice"),
                (getattr(self, "btn_clear", None), "dark"),
                (getattr(self, "btn_pro", None), "pro"),
                (getattr(self, "valve_btn_buy", None), "pro"),
                (getattr(self, "valve_btn_watch", None), "ice"),
                (getattr(self, "valve_btn_type", None), "primary"),
                (getattr(self, "valve_btn_calc", None), "ice"),
                (getattr(self, "labor_btn_highways", None), "primary" if getattr(self, "_labor_use_highways", False) else "dark"),
                (getattr(self, "labor_btn_additional", None), "primary" if getattr(self, "_labor_has_additional", False) else "dark"),
                (getattr(self, "labor_btn_rates", None), "pro"),
                (getattr(self, "labor_btn_calc", None), "ice"),
            ):
                if button is not None:
                    self._style_app_button(button, variant)
            self._style_valve_mode_buttons()

        def _build_product_card(self, dp, MDCard, MDBoxLayout, MDIcon, MDLabel, MDRaisedButton, AsyncImage):
            from kivymd.uix.button import MDIconButton

            card = MDCard(
                orientation="vertical",
                padding=dp(14),
                spacing=dp(12),
                size_hint_y=None,
                height=dp(322 if self._hints_enabled else 292),
                radius=[16, 16, 16, 16],
                elevation=3,
                md_bg_color=self._card_bg(),
            )
            self.product_card = card
            self._themed_cards.append(card)
            title_row = MDBoxLayout(
                orientation="horizontal", size_hint_y=None, height=dp(30)
            )
            self.product_title_row = title_row
            self.lbl_product_title = MDLabel(
                text=self._t("product"),
                font_style="H6",
            )
            title_row.add_widget(self.lbl_product_title)
            self.btn_add_product = MDIconButton(
                icon="plus-circle-outline",
                size_hint_x=None,
                width=dp(44),
                icon_size="26sp",
                theme_text_color="Custom",
                text_color=(0.18, 0.68, 0.95, 1),
                on_release=lambda *_: self._open_custom_product_dialog(),
            )
            title_row.add_widget(self.btn_add_product)
            card.add_widget(title_row)

            self.lbl_product_hint = MDLabel(
                text=self._t("product_hint"),
                size_hint_y=None,
                height=dp(30 if self._hints_enabled else 0),
                opacity=1 if self._hints_enabled else 0,
                font_style="Caption",
                theme_text_color="Hint",
            )
            card.add_widget(self.lbl_product_hint)

            body = MDBoxLayout(
                orientation="horizontal",
                spacing=dp(14),
                size_hint_y=None,
                height=dp(202),
            )
            self.product_body = body
            controls = MDBoxLayout(
                orientation="vertical",
                spacing=dp(12),
                size_hint_x=0.46,
                padding=[0, dp(8), 0, dp(8)],
            )
            self.product_controls = controls
            self.btn_category = MDRaisedButton(
                text=self._t("choose_category"),
                size_hint_x=1,
                size_hint_y=None,
                height=dp(52),
                font_size="15sp",
                on_release=lambda btn: self._open_category_menu(btn),
            )
            self.category_field_box = MDBoxLayout(
                orientation="vertical", size_hint_y=None, height=dp(54), spacing=0
            )
            self.category_field_box.add_widget(self.btn_category)
            self.category_error_line = MDBoxLayout(
                size_hint_y=None,
                height=dp(2),
                opacity=0,
                md_bg_color=(0.94, 0.20, 0.26, 1),
            )
            self.category_field_box.add_widget(self.category_error_line)
            controls.add_widget(self.category_field_box)

            self.btn_product = MDRaisedButton(
                text=self._t("choose_product"),
                size_hint_x=1,
                size_hint_y=None,
                height=dp(52),
                font_size="15sp",
                disabled=True,
                on_release=lambda btn: self._open_product_menu(btn),
            )
            self.product_field_box = MDBoxLayout(
                orientation="vertical", size_hint_y=None, height=dp(54), spacing=0
            )
            self.product_field_box.add_widget(self.btn_product)
            self.product_error_line = MDBoxLayout(
                size_hint_y=None,
                height=dp(2),
                opacity=0,
                md_bg_color=(0.94, 0.20, 0.26, 1),
            )
            self.product_field_box.add_widget(self.product_error_line)
            controls.add_widget(self.product_field_box)

            body.add_widget(controls)
            self.image_box = MDBoxLayout(
                orientation="vertical",
                size_hint_x=0.54,
                padding=[0, dp(4), 0, dp(4)],
            )
            self.image_placeholder = MDBoxLayout(
                orientation="vertical",
                spacing=dp(2),
                padding=[0, dp(44), 0, dp(28)],
            )
            self.image_placeholder_icon = MDIcon(
                icon="image",
                halign="center",
                font_size="42sp",
                theme_text_color="Hint",
            )
            self.image_placeholder.add_widget(self.image_placeholder_icon)
            self.image_placeholder_label = MDLabel(
                text=self._t("image_placeholder"),
                halign="center",
                font_style="Caption",
                theme_text_color="Hint",
            )
            self.image_placeholder.add_widget(self.image_placeholder_label)
            self.product_image = AsyncImage(
                source="",
                allow_stretch=True,
                keep_ratio=True,
                opacity=0,
            )
            self.image_box.add_widget(self.image_placeholder)
            body.add_widget(self.image_box)
            card.add_widget(body)
            return card

        def _build_params_card(self, dp, MDCard, MDBoxLayout, MDLabel, MDTextField, MDRaisedButton):
            card = MDCard(
                orientation="vertical",
                padding=dp(14),
                spacing=dp(10),
                size_hint_y=None,
                height=dp(360),
                radius=[16, 16, 16, 16],
                elevation=3,
                md_bg_color=self._card_bg(),
            )
            self.params_card = card
            self._themed_cards.append(card)
            self.lbl_params_title = MDLabel(
                text=self._t("params"),
                font_style="H6",
                size_hint_y=None,
                height=dp(30),
            )
            card.add_widget(self.lbl_params_title)

            row_mass = MDBoxLayout(orientation="horizontal", spacing=dp(10), size_hint_y=None, height=dp(68))
            self.row_mass = row_mass
            self.in_m = MDTextField(
                hint_text=self._t("mass"),
                input_filter=_numeric_input_filter,
                size_hint_x=1,
                size_hint_y=None,
                height=dp(60),
            )
            self.btn_unit = MDRaisedButton(
                text=self._mass_unit,
                size_hint_x=None,
                width=dp(72),
                size_hint_y=None,
                height=dp(42),
                font_size="15sp",
                pos_hint={"center_y": 0.5},
                on_release=lambda *_: self._toggle_mass_unit(),
                theme_text_color="Custom",
                text_color=(1, 1, 1, 1),
            )
            row_mass.add_widget(self.in_m)
            row_mass.add_widget(self.btn_unit)
            card.add_widget(row_mass)
            self._set_mass_unit(self._mass_unit)

            self.in_T1 = MDTextField(
                hint_text=self._t("temperature_start"), input_filter=_numeric_input_filter
            )
            self.in_T2 = MDTextField(
                hint_text=self._t("temperature_end"), input_filter=_numeric_input_filter
            )
            self.in_t = MDTextField(
                hint_text=self._t("work_time"), input_filter=_numeric_input_filter
            )
            for w in (self.in_T1, self.in_T2, self.in_t):
                w.size_hint_y = None
                w.height = dp(60)
                card.add_widget(w)
            return card

        def _build_action_button(self, dp, MDBoxLayout, MDRaisedButton):
            wrapper = MDBoxLayout(
                orientation="horizontal",
                size_hint_y=None,
                height=dp(64),
                spacing=dp(8),
                padding=[0, dp(6), 0, dp(6)],
            )
            self.action_row = wrapper
            self.btn_calc = MDRaisedButton(
                text=self._t("calculate"),
                icon="calculator-variant",
                size_hint_x=0.40,
                size_hint_y=None,
                height=dp(48),
                font_size="14sp",
                pos_hint={"center_y": 0.5},
                on_release=lambda *_: self._calculate(),
            )
            wrapper.add_widget(self.btn_calc)
            self.btn_pdf = MDRaisedButton(
                text="PDF",
                icon="file-pdf-box",
                size_hint_x=0.27,
                size_hint_y=None,
                height=dp(48),
                font_size="14sp",
                pos_hint={"center_y": 0.5},
                on_release=lambda *_: self._export_pdf(),
            )
            wrapper.add_widget(self.btn_pdf)
            self.btn_clear = MDRaisedButton(
                text=self._t("clear"),
                icon="broom",
                size_hint_x=0.33,
                size_hint_y=None,
                height=dp(48),
                font_size="14sp",
                md_bg_color=(0.16, 0.19, 0.23, 1),
                pos_hint={"center_y": 0.5},
                on_release=lambda *_: self._reset_inputs(),
                theme_text_color="Custom",
                text_color=(1.0, 0.55, 0.55, 1),
            )
            wrapper.add_widget(self.btn_clear)
            return wrapper

        def _build_results_card(self, dp, MDCard, MDBoxLayout, MDIcon, MDLabel, MDProgressBar, MDRaisedButton):
            card = MDCard(
                orientation="vertical",
                padding=dp(14),
                spacing=dp(8),
                size_hint_y=None,
                height=dp(390),
                radius=[16, 16, 16, 16],
                elevation=3,
                md_bg_color=self._card_bg(),
            )
            self.results_card = card
            self._themed_cards.append(card)
            title_row = MDBoxLayout(orientation="horizontal", size_hint_y=None, height=dp(44), spacing=0)
            self.results_title_row = title_row
            self.lbl_results_title = MDLabel(
                text=self._t("result"),
                font_style="H6",
                valign="middle",
            )
            title_row.add_widget(self.lbl_results_title)
            card.add_widget(title_row)
            card.add_widget(self._build_action_button(dp, MDBoxLayout, MDRaisedButton))

            self.lbl_total = MDLabel(
                text=self._total_text(),
                font_style="H6",
                halign="center",
                size_hint_y=None,
                height=dp(46),
                theme_text_color="Custom",
                text_color=STAGE_COLORS["total"],
            )
            card.add_widget(self.lbl_total)

            self.bars: dict[str, dict] = {}
            for key, label_key, icon in [
                ("schladzanie", "cooling", "thermometer"),
                ("zamrozenie", "freezing", "snowflake"),
                ("domrozenie", "deep_freezing", "thermometer"),
            ]:
                self.bars[key] = self._add_stage_row(
                    card, key, self._t(label_key), icon, dp, MDBoxLayout, MDIcon, MDLabel, MDProgressBar
                )

            return card

        def _add_stage_row(self, parent, key, label, icon, dp, MDBoxLayout, MDIcon, MDLabel, MDProgressBar):
            row = MDBoxLayout(orientation="vertical", size_hint_y=None, height=dp(74), spacing=dp(6))
            head = MDBoxLayout(orientation="horizontal", size_hint_y=None, height=dp(38), spacing=dp(10))
            icon_chip = StageIconBadge(
                accent=STAGE_COLORS[key],
                size_hint_x=None,
                size_hint_y=None,
                width=dp(38),
                height=dp(38),
            )
            icon_widget = StageMotionIcon(
                mode=key,
                accent=STAGE_COLORS[key],
                size_hint=(1, 1),
            )
            icon_chip.add_widget(icon_widget)
            head.add_widget(icon_chip)
            lbl_name = MDLabel(text=label, size_hint_x=0.52)
            lbl_val = MDLabel(text="—", halign="right", size_hint_x=0.4)
            head.add_widget(lbl_name)
            head.add_widget(lbl_val)
            bar = MDProgressBar(value=0, max=100, color=STAGE_COLORS[key])
            row.add_widget(head)
            row.add_widget(bar)
            parent.add_widget(row)
            return {
                "bar": bar,
                "head": head,
                "icon": icon_widget,
                "icon_chip": icon_chip,
                "name_label": lbl_name,
                "row": row,
                "value_label": lbl_val,
            }

        def _build_footer(self, dp, MDBoxLayout, MDLabel, MDRaisedButton):
            footer = MDBoxLayout(
                orientation="horizontal",
                size_hint_y=None,
                height=dp(48),
                padding=[dp(12), dp(4), dp(12), dp(4)],
                spacing=dp(8),
                md_bg_color=self._footer_bg(),
            )
            self.footer_bar = footer
            self.footer_label = MDLabel(
                text=self._status_footer_text(),
                halign="center",
                valign="middle",
                theme_text_color="Hint",
                font_style="Caption",
            )
            self.btn_pro = MDRaisedButton(
                text=self._t("pro_button"),
                size_hint_x=None,
                width=dp(128),
                size_hint_y=None,
                height=dp(30),
                font_size="11sp",
                pos_hint={"center_y": 0.5},
                on_release=lambda *_: self._buy_pro(),
            )
            footer.add_widget(self.btn_pro)
            footer.add_widget(self.footer_label)
            return footer

        def _build_ad_slot(self, dp, MDBoxLayout, MDIcon, MDLabel):
            slot = MDBoxLayout(
                orientation="horizontal",
                size_hint_y=None,
                height=dp(96),
                padding=[dp(16), dp(6), dp(16), dp(6)],
                spacing=dp(8),
                md_bg_color=self._ad_slot_bg(),
            )
            self.ad_slot = slot
            slot.add_widget(
                MDIcon(
                    icon="bullhorn",
                    size_hint_x=None,
                    width=dp(28),
                    halign="center",
                    theme_text_color="Hint",
                )
            )
            self.ad_label = MDLabel(
                text=self._ad_label_text(),
                halign="center",
                font_style="Caption",
                theme_text_color="Hint",
            )
            slot.add_widget(self.ad_label)
            return slot

        # --- karta zaworów dekompresyjnych -------------------------------
        def _build_valve_tab(self, dp, MDScrollView, MDCard, MDBoxLayout, MDLabel, MDTextField, MDRaisedButton):
            scroll = MDScrollView()
            content = MDBoxLayout(
                orientation="vertical",
                padding=[dp(16), dp(16), dp(16), dp(20)],
                spacing=dp(14),
                size_hint_y=None,
            )
            content.bind(minimum_height=content.setter("height"))

            # Karta blokady modułu (płatny) — widoczna tylko gdy moduł zablokowany.
            lock_card = MDCard(
                orientation="vertical",
                padding=dp(14),
                spacing=dp(10),
                size_hint_y=None,
                height=dp(196),
                radius=[16, 16, 16, 16],
                elevation=3,
                md_bg_color=self._card_bg(),
            )
            self._themed_cards.append(lock_card)
            self.valve_lock_card = lock_card

            self.valve_lbl_locked = MDLabel(
                text=self._t("valve_locked"),
                font_style="Subtitle1",
                size_hint_y=None,
                height=dp(64),
                theme_text_color="Secondary",
            )
            lock_card.add_widget(self.valve_lbl_locked)

            self.valve_btn_buy = MDRaisedButton(
                text=self._t("valve_buy"),
                icon="cart",
                size_hint_x=1,
                size_hint_y=None,
                height=dp(50),
                font_size="15sp",
                on_release=lambda *_: self._buy_valve_module(),
            )
            lock_card.add_widget(self.valve_btn_buy)

            self.valve_btn_watch = MDRaisedButton(
                text=self._t("valve_watch_ad"),
                icon="play-circle-outline",
                size_hint_x=1,
                size_hint_y=None,
                height=dp(50),
                font_size="15sp",
                on_release=lambda *_: self._offer_reward_ad(),
            )
            lock_card.add_widget(self.valve_btn_watch)
            content.add_widget(lock_card)

            # Karta danych wejściowych.
            card = MDCard(
                orientation="vertical",
                padding=dp(14),
                spacing=dp(10),
                size_hint_y=None,
                radius=[16, 16, 16, 16],
                elevation=3,
                md_bg_color=self._card_bg(),
            )
            card.bind(minimum_height=card.setter("height"))
            self._themed_cards.append(card)
            self.valve_card = card

            self.valve_lbl_title = MDLabel(
                text=self._t("valve_title"),
                font_style="H6",
                size_hint_y=None,
                height=dp(36),
            )
            card.add_widget(self.valve_lbl_title)

            self.valve_btn_type = MDRaisedButton(
                text=self._valve_type,
                size_hint_x=1,
                size_hint_y=None,
                height=dp(52),
                font_size="15sp",
                on_release=lambda btn: self._open_valve_type_menu(btn),
            )
            card.add_widget(self.valve_btn_type)

            # Przełącznik trybu objętości: Kubatura / Wymiary.
            mode_box = MDBoxLayout(
                orientation="horizontal",
                spacing=dp(8),
                size_hint_y=None,
                height=dp(44),
            )
            self.valve_btn_mode_k = MDRaisedButton(
                text=self._t("valve_mode_volume"),
                size_hint_x=0.5,
                size_hint_y=None,
                height=dp(44),
                font_size="13sp",
                on_release=lambda *_: self._set_valve_mode("K"),
            )
            self.valve_btn_mode_w = MDRaisedButton(
                text=self._t("valve_mode_dims"),
                size_hint_x=0.5,
                size_hint_y=None,
                height=dp(44),
                font_size="13sp",
                on_release=lambda *_: self._set_valve_mode("W"),
            )
            mode_box.add_widget(self.valve_btn_mode_k)
            mode_box.add_widget(self.valve_btn_mode_w)
            card.add_widget(mode_box)

            # Pole objętości (tryb Kubatura).
            self.valve_in_V = MDTextField(
                hint_text=self._t("valve_volume"), input_filter=_numeric_input_filter
            )
            self.valve_in_V.size_hint_y = None
            self.valve_in_V.height = dp(60)
            self.valve_vol_box = MDBoxLayout(
                orientation="vertical", size_hint_y=None, height=dp(60)
            )
            self.valve_vol_box.add_widget(self.valve_in_V)
            card.add_widget(self.valve_vol_box)

            # Pola wymiarów (tryb Wymiary): objętość = L × Sz × W.
            self.valve_in_L = MDTextField(
                hint_text=self._t("valve_length"), input_filter=_numeric_input_filter
            )
            self.valve_in_W = MDTextField(
                hint_text=self._t("valve_width"), input_filter=_numeric_input_filter
            )
            self.valve_in_H = MDTextField(
                hint_text=self._t("valve_height"), input_filter=_numeric_input_filter
            )
            self.valve_dim_box = MDBoxLayout(
                orientation="vertical", size_hint_y=None, height=dp(180)
            )
            for w in (self.valve_in_L, self.valve_in_W, self.valve_in_H):
                w.size_hint_y = None
                w.height = dp(60)
                self.valve_dim_box.add_widget(w)
            card.add_widget(self.valve_dim_box)

            # Temperatury, ilość chłodnic, przepływ na 1 chłodnicę.
            self.valve_in_tp = MDTextField(
                hint_text=self._t("valve_temp_before"), input_filter=_numeric_input_filter
            )
            self.valve_in_tz = MDTextField(
                hint_text=self._t("valve_temp_after"), input_filter=_numeric_input_filter
            )
            self.valve_in_n = MDTextField(hint_text=self._t("valve_coolers"), input_filter="int")
            self.valve_in_q = MDTextField(
                hint_text=self._t("valve_flow_per"), input_filter=_numeric_input_filter
            )
            for w in (self.valve_in_tp, self.valve_in_tz, self.valve_in_n, self.valve_in_q):
                w.size_hint_y = None
                w.height = dp(60)
                card.add_widget(w)

            self.valve_btn_calc = MDRaisedButton(
                text=self._t("valve_calculate"),
                icon="calculator-variant",
                size_hint_x=1,
                size_hint_y=None,
                height=dp(50),
                font_size="15sp",
                on_release=lambda *_: self._calculate_valves(),
            )
            card.add_widget(self.valve_btn_calc)
            content.add_widget(card)
            self._set_valve_mode(self._valve_input_mode)

            # Karta wyniku.
            res_card = MDCard(
                orientation="vertical",
                padding=dp(14),
                spacing=dp(8),
                size_hint_y=None,
                radius=[16, 16, 16, 16],
                elevation=3,
                md_bg_color=self._card_bg(),
            )
            res_card.bind(minimum_height=res_card.setter("height"))
            self._themed_cards.append(res_card)
            self.valve_result_card = res_card

            self.valve_lbl_result = MDLabel(
                text=self._t("valve_result"),
                font_style="H6",
                size_hint_y=None,
                height=dp(36),
            )
            res_card.add_widget(self.valve_lbl_result)

            self.valve_lbl_count = MDLabel(
                text=self._t("valve_count", value="—"),
                font_style="H6",
                halign="center",
                size_hint_y=None,
                height=dp(42),
                theme_text_color="Custom",
                text_color=STAGE_COLORS["total"],
            )
            res_card.add_widget(self.valve_lbl_count)

            self.valve_lbl_delta = MDLabel(
                text=self._t("valve_delta_t", value="—"),
                size_hint_y=None,
                height=dp(30),
                theme_text_color="Secondary",
            )
            self.valve_lbl_totalflow = MDLabel(
                text=self._t("valve_total_flow", value="—"),
                size_hint_y=None,
                height=dp(30),
                theme_text_color="Secondary",
            )
            self.valve_lbl_flow = MDLabel(
                text=self._t("valve_flow", value="—"),
                size_hint_y=None,
                height=dp(30),
                theme_text_color="Secondary",
            )
            self.valve_lbl_unitflow = MDLabel(
                text=self._t("valve_unit_flow", value="—"),
                size_hint_y=None,
                height=dp(30),
                theme_text_color="Secondary",
            )
            res_card.add_widget(self.valve_lbl_delta)
            res_card.add_widget(self.valve_lbl_totalflow)
            res_card.add_widget(self.valve_lbl_flow)
            res_card.add_widget(self.valve_lbl_unitflow)
            content.add_widget(res_card)

            scroll.add_widget(content)
            return scroll

        def _build_labor_tab(self, dp, MDScrollView, MDCard, MDBoxLayout, MDLabel, MDTextField, MDRaisedButton):
            scroll = MDScrollView()
            content = MDBoxLayout(
                orientation="vertical",
                padding=[dp(16), dp(14), dp(16), dp(18)],
                spacing=dp(14),
                size_hint_y=None,
            )
            content.bind(minimum_height=content.setter("height"))

            card = MDCard(
                orientation="vertical",
                padding=dp(14),
                spacing=dp(10),
                size_hint_y=None,
                radius=[16, 16, 16, 16],
                elevation=3,
                md_bg_color=self._card_bg(),
            )
            card.bind(minimum_height=card.setter("height"))
            self._themed_cards.append(card)
            self.labor_card = card

            self.labor_lbl_title = MDLabel(
                text=self._t("labor_title"),
                font_style="H6",
                size_hint_y=None,
                height=dp(36),
            )
            card.add_widget(self.labor_lbl_title)

            self.labor_lbl_hint = MDLabel(
                text=self._t("labor_hint"),
                font_style="Caption",
                theme_text_color="Hint",
                size_hint_y=None,
                height=dp(38),
            )
            card.add_widget(self.labor_lbl_hint)

            self.labor_in_people = MDTextField(
                hint_text=self._t("labor_people"), input_filter="int"
            )
            self.labor_in_days = MDTextField(
                hint_text=self._t("labor_days"), input_filter="int"
            )
            self.labor_in_distance = MDTextField(
                hint_text=self._t("labor_distance"), input_filter="int"
            )
            self.labor_in_lifts = MDTextField(
                hint_text=self._t("labor_lifts"), input_filter="int"
            )
            self.labor_in_containers = MDTextField(
                hint_text=self._t("labor_containers"), input_filter="int"
            )
            for field in (
                self.labor_in_people,
                self.labor_in_days,
                self.labor_in_distance,
                self.labor_in_lifts,
                self.labor_in_containers,
            ):
                field.size_hint_y = None
                field.height = dp(60)
                card.add_widget(field)

            toggle_row = MDBoxLayout(
                orientation="horizontal",
                spacing=dp(8),
                size_hint_y=None,
                height=dp(46),
            )
            self.labor_btn_highways = MDRaisedButton(
                text=self._t("labor_highways_off"),
                size_hint_x=0.5,
                size_hint_y=None,
                height=dp(44),
                font_size="13sp",
                on_release=lambda *_: self._toggle_labor_highways(),
            )
            self.labor_btn_additional = MDRaisedButton(
                text=self._t("labor_additional_off"),
                size_hint_x=0.5,
                size_hint_y=None,
                height=dp(44),
                font_size="13sp",
                on_release=lambda *_: self._toggle_labor_additional(),
            )
            toggle_row.add_widget(self.labor_btn_highways)
            toggle_row.add_widget(self.labor_btn_additional)
            card.add_widget(toggle_row)

            self.labor_in_additional = MDTextField(
                hint_text=self._t("labor_additional"), input_filter=_numeric_input_filter
            )
            self.labor_in_additional.size_hint_y = None
            self.labor_in_additional.height = dp(60)
            self.labor_additional_box = MDBoxLayout(
                orientation="vertical", size_hint_y=None, height=0
            )
            self.labor_additional_box.add_widget(self.labor_in_additional)
            card.add_widget(self.labor_additional_box)

            self.labor_btn_calc = MDRaisedButton(
                text=self._t("labor_calculate"),
                icon="calculator-variant",
                size_hint_x=0.64,
                size_hint_y=None,
                height=dp(50),
                font_size="15sp",
                on_release=lambda *_: self._calculate_labor(),
            )
            self.labor_btn_rates = MDRaisedButton(
                text=self._t("labor_rates_button"),
                icon="tune-variant",
                size_hint_x=0.36,
                size_hint_y=None,
                height=dp(50),
                font_size="13sp",
                on_release=lambda *_: self._open_labor_rates_dialog(),
            )
            action_row = MDBoxLayout(
                orientation="horizontal",
                spacing=dp(8),
                size_hint_y=None,
                height=dp(52),
            )
            action_row.add_widget(self.labor_btn_rates)
            action_row.add_widget(self.labor_btn_calc)
            card.add_widget(action_row)
            content.add_widget(card)

            result_card = MDCard(
                orientation="vertical",
                padding=dp(14),
                spacing=dp(8),
                size_hint_y=None,
                radius=[16, 16, 16, 16],
                elevation=3,
                md_bg_color=self._card_bg(),
            )
            result_card.bind(minimum_height=result_card.setter("height"))
            self._themed_cards.append(result_card)
            self.labor_result_card = result_card

            self.labor_lbl_result = MDLabel(
                text=self._t("labor_result"),
                font_style="H6",
                size_hint_y=None,
                height=dp(36),
            )
            result_card.add_widget(self.labor_lbl_result)
            self.labor_lbl_total = MDLabel(
                text=self._t("labor_total_cost", value="—"),
                font_style="H6",
                halign="center",
                size_hint_y=None,
                height=dp(44),
                theme_text_color="Custom",
                text_color=STAGE_COLORS["total"],
            )
            result_card.add_widget(self.labor_lbl_total)

            self.labor_result_labels = {}
            for attr, key in (
                ("labor_cost", "labor_labor_cost"),
                ("travel_cost", "labor_travel_cost"),
                ("lift_cost", "labor_lift_cost"),
                ("container_cost", "labor_container_cost"),
                ("hotel_cost", "labor_hotel_cost"),
                ("allowance_cost", "labor_allowance_cost"),
                ("regenerative_meal_cost", "labor_meal_cost"),
                ("additional_costs_value", "labor_additional_costs"),
            ):
                label = MDLabel(
                    text=self._t(key, value="—"),
                    size_hint_y=None,
                    height=dp(28),
                    theme_text_color="Secondary",
                )
                self.labor_result_labels[attr] = (label, key)
                result_card.add_widget(label)
            self.labor_lbl_mode = MDLabel(
                text=self._t("labor_travel_mode", value="—"),
                size_hint_y=None,
                height=dp(28),
                theme_text_color="Secondary",
            )
            self.labor_lbl_details = MDLabel(
                text=self._t("labor_travel_details", trips="—", toll_days="—", nights="—"),
                size_hint_y=None,
                height=dp(32),
                theme_text_color="Hint",
                font_style="Caption",
            )
            result_card.add_widget(self.labor_lbl_mode)
            result_card.add_widget(self.labor_lbl_details)
            content.add_widget(result_card)

            scroll.add_widget(content)
            self._set_labor_highways(False)
            self._set_labor_additional_enabled(False)
            self._render_labor_results(None)
            return scroll

        def _set_labor_highways(self, enabled: bool):
            self._labor_use_highways = bool(enabled)
            if hasattr(self, "labor_btn_highways"):
                self.labor_btn_highways.text = self._t(
                    "labor_highways_on" if self._labor_use_highways else "labor_highways_off"
                )
                self._style_app_button(
                    self.labor_btn_highways,
                    "primary" if self._labor_use_highways else "dark",
                )

        def _toggle_labor_highways(self):
            self._set_labor_highways(not self._labor_use_highways)

        def _set_labor_additional_enabled(self, enabled: bool):
            from kivy.metrics import dp

            self._labor_has_additional = bool(enabled)
            if hasattr(self, "labor_btn_additional"):
                self.labor_btn_additional.text = self._t(
                    "labor_additional_on"
                    if self._labor_has_additional
                    else "labor_additional_off"
                )
                self._style_app_button(
                    self.labor_btn_additional,
                    "primary" if self._labor_has_additional else "dark",
                )
            if hasattr(self, "labor_additional_box"):
                self.labor_additional_box.height = dp(60) if self._labor_has_additional else 0
                self.labor_additional_box.opacity = 1 if self._labor_has_additional else 0
                self.labor_additional_box.disabled = not self._labor_has_additional
            if hasattr(self, "labor_in_additional") and not self._labor_has_additional:
                self.labor_in_additional.text = ""
                self._clear_field_error(self.labor_in_additional)

        def _toggle_labor_additional(self):
            self._set_labor_additional_enabled(not self._labor_has_additional)

        def _clear_labor_validation(self):
            for field in (
                getattr(self, "labor_in_people", None),
                getattr(self, "labor_in_days", None),
                getattr(self, "labor_in_distance", None),
                getattr(self, "labor_in_lifts", None),
                getattr(self, "labor_in_containers", None),
                getattr(self, "labor_in_additional", None),
            ):
                if field is not None:
                    self._clear_field_error(field)

        def _parse_labor_int(
            self,
            field,
            name_key: str,
            *,
            min_value: int,
            allow_zero: bool,
            default_empty: int | None = None,
        ) -> int:
            raw = (getattr(field, "text", "") or "").strip()
            if not raw and default_empty is not None:
                return default_empty
            if not raw:
                self._mark_field_error(field)
                raise ValueError(self._t("invalid_field", name=self._t(name_key)))
            try:
                value = int(raw)
            except (TypeError, ValueError) as exc:
                self._mark_field_error(field, self._t("invalid_field", name=self._t(name_key)))
                raise ValueError(self._t("invalid_field", name=self._t(name_key))) from exc
            if value < min_value or (not allow_zero and value == 0):
                message = self._t("invalid_field", name=self._t(name_key))
                self._mark_field_error(field, message)
                raise ValueError(message)
            return value

        def _parse_labor_decimal(self, field, name_key: str) -> Decimal:
            raw = (getattr(field, "text", "") or "").strip()
            if not raw:
                self._mark_field_error(field)
                raise ValueError(self._t("invalid_field", name=self._t(name_key)))
            try:
                value = Decimal(raw.replace(",", "."))
            except Exception as exc:
                self._mark_field_error(field, self._t("invalid_field", name=self._t(name_key)))
                raise ValueError(self._t("invalid_field", name=self._t(name_key))) from exc
            if value < 0:
                message = self._t("invalid_field", name=self._t(name_key))
                self._mark_field_error(field, message)
                raise ValueError(message)
            return value

        def _format_labor_money(self, value) -> str:
            if value is None:
                return "—"
            amount = Decimal(str(value)).quantize(Decimal("0.01"))
            text = f"{amount:,.2f}"
            return text.replace(",", " ").replace(".", ",") if self._language == "pl" else text

        def _labor_travel_mode_text(self, mode: str) -> str:
            if self._language == "pl":
                return mode
            if mode == "Dojazd dzienny":
                return "Daily travel"
            if mode == "Delegacja tygodniowa":
                return "Weekly delegation"
            return mode

        def _render_labor_results(self, breakdown):
            dash = "—"
            if not hasattr(self, "labor_lbl_total"):
                return
            self.labor_lbl_total.text = self._t(
                "labor_total_cost",
                value=dash if breakdown is None else self._format_labor_money(breakdown.total_cost),
            )
            for attr, (label, key) in getattr(self, "labor_result_labels", {}).items():
                value = dash if breakdown is None else self._format_labor_money(getattr(breakdown, attr))
                label.text = self._t(key, value=value)
            if hasattr(self, "labor_lbl_mode"):
                self.labor_lbl_mode.text = self._t(
                    "labor_travel_mode",
                    value=dash if breakdown is None else self._labor_travel_mode_text(breakdown.travel_mode),
                )
            if hasattr(self, "labor_lbl_details"):
                self.labor_lbl_details.text = self._t(
                    "labor_travel_details",
                    trips=dash if breakdown is None else breakdown.travel_round_trips,
                    toll_days=dash if breakdown is None else breakdown.highway_toll_days,
                    nights=dash if breakdown is None else breakdown.hotel_nights,
                )

        def _labor_rate_config(self):
            try:
                return rate_config_from_values(self._preferences.labor_rate_values)
            except ValueError:
                self._preferences.reset_labor_rate_values()
                return default_rate_config()

        def _close_labor_rates_dialog(self):
            dialog = getattr(self, "_labor_rate_dialog", None)
            if dialog is not None:
                dialog.dismiss()
                self._labor_rate_dialog = None

        def _labor_rate_text_values(self):
            values = self._preferences.labor_rate_values
            return {key: str(values.get(key, "")) for key in RATE_CONFIG_FIELDS}

        def _open_labor_rates_dialog(self):
            if not self._pro_no_ads:
                self._show_error(self._t("labor_rates_pro_required"))
                return
            self._close_labor_rates_dialog()
            try:
                from kivy.metrics import dp
                from kivy.uix.scrollview import ScrollView
                from kivymd.uix.boxlayout import MDBoxLayout
                from kivymd.uix.button import MDFlatButton, MDRaisedButton
                from kivymd.uix.dialog import MDDialog
                from kivymd.uix.label import MDLabel
                from kivymd.uix.textfield import MDTextField

                outer = MDBoxLayout(
                    orientation="vertical",
                    spacing=dp(8),
                    size_hint_y=None,
                    height=dp(540),
                )
                outer.add_widget(
                    MDLabel(
                        text=self._t("labor_rates_intro"),
                        theme_text_color="Hint",
                        font_style="Caption",
                        adaptive_height=True,
                    )
                )
                scroll = ScrollView()
                form = MDBoxLayout(
                    orientation="vertical",
                    spacing=dp(8),
                    padding=[0, dp(4), dp(8), dp(8)],
                    size_hint_y=None,
                )
                form.bind(minimum_height=form.setter("height"))
                self._labor_rate_fields = {}
                values = self._labor_rate_text_values()
                for key in RATE_CONFIG_FIELDS:
                    field = MDTextField(
                        hint_text=self._t(f"labor_rate_{key}"),
                        text=values.get(key, ""),
                        input_filter="int" if key == "workdays_per_week" else _numeric_input_filter,
                        size_hint_y=None,
                        height=dp(62),
                    )
                    field.bind(
                        text=lambda widget, _value: self._clear_field_error(widget)
                    )
                    self._labor_rate_fields[key] = field
                    form.add_widget(field)
                scroll.add_widget(form)
                outer.add_widget(scroll)

                self._labor_rate_dialog = MDDialog(
                    title=self._t("labor_rates_title"),
                    type="custom",
                    content_cls=outer,
                    buttons=[
                        MDFlatButton(
                            text=self._t("labor_rates_factory"),
                            on_release=lambda *_: self._reset_labor_rates(),
                        ),
                        MDFlatButton(
                            text=self._t("cancel"),
                            on_release=lambda *_: self._close_labor_rates_dialog(),
                        ),
                        MDRaisedButton(
                            text=self._t("save"),
                            on_release=lambda *_: self._save_labor_rates(),
                        ),
                    ],
                )
                self._labor_rate_dialog.open()
                telemetry.log_event("settings_opened", {"section": "labor_rates"})
            except Exception as exc:
                telemetry.record_exception(exc, "open_labor_rates")
                log.exception("Formularz stawek robocizny")
                self._show_error(self._t("calc_error", error=exc))

        def _invalidate_labor_results(self):
            self._last_labor_breakdown = None
            self._render_labor_results(None)

        def _mark_labor_rate_errors(self, message: str):
            fields = getattr(self, "_labor_rate_fields", {})
            marked = False
            for key, field in fields.items():
                if key in message:
                    self._mark_field_error(field)
                    marked = True
            if not marked:
                for field in fields.values():
                    self._mark_field_error(field)

        def _save_labor_rates(self):
            fields = getattr(self, "_labor_rate_fields", {})
            values = {key: field.text for key, field in fields.items()}
            try:
                self._preferences.set_labor_rate_values(values)
            except ValueError as exc:
                message = str(exc)
                self._mark_labor_rate_errors(message)
                self._show_error(self._t("labor_rates_invalid", message=message))
                return
            self._invalidate_labor_results()
            self._close_labor_rates_dialog()
            self._show_error(self._t("labor_rates_saved"))
            telemetry.log_event("settings_saved", {"section": "labor_rates"})

        def _reset_labor_rates(self):
            self._preferences.reset_labor_rate_values()
            values = self._labor_rate_text_values()
            for key, field in getattr(self, "_labor_rate_fields", {}).items():
                field.text = values.get(key, "")
                self._clear_field_error(field)
            self._invalidate_labor_results()
            self._show_error(self._t("labor_rates_reset"))
            telemetry.log_event("settings_reset", {"section": "labor_rates"})

        def _calculate_labor(self):
            from kivy.metrics import dp

            self._clear_labor_validation()
            try:
                people = self._parse_labor_int(
                    self.labor_in_people, "labor_people", min_value=1, allow_zero=False
                )
                days = self._parse_labor_int(
                    self.labor_in_days, "labor_days", min_value=1, allow_zero=False
                )
                distance = self._parse_labor_int(
                    self.labor_in_distance, "labor_distance", min_value=0, allow_zero=True
                )
                lifts = self._parse_labor_int(
                    self.labor_in_lifts,
                    "labor_lifts",
                    min_value=0,
                    allow_zero=True,
                    default_empty=0,
                )
                containers = self._parse_labor_int(
                    self.labor_in_containers,
                    "labor_containers",
                    min_value=0,
                    allow_zero=True,
                    default_empty=0,
                )
                additional = (
                    self._parse_labor_decimal(self.labor_in_additional, "labor_additional")
                    if self._labor_has_additional
                    else Decimal("0")
                )
                errors = validate_labor_inputs(
                    people,
                    days,
                    distance,
                    lifts,
                    containers,
                    self._labor_has_additional,
                    additional,
                )
                if errors:
                    raise ValueError(errors[0])
                telemetry.log_event(
                    "calculation_started",
                    {"calculator": "labor", "screen": self._active_tab_name},
                )
                breakdown = calculate_labor_cost_breakdown(
                    LaborCalculationInput(
                        number_of_people=people,
                        number_of_days=days,
                        distance_km_one_way=distance,
                        use_highways=self._labor_use_highways,
                        number_of_lifts=lifts,
                        number_of_containers=containers,
                        additional_costs_value=additional,
                    ),
                    self._labor_rate_config(),
                )
                self._last_labor_breakdown = breakdown
                self._render_labor_results(breakdown)
                telemetry.log_event(
                    "calculation_finished",
                    {
                        "calculator": "labor",
                        "travel_mode": breakdown.travel_mode,
                        "has_additional": self._labor_has_additional,
                    },
                )
                if hasattr(self, "labor_scroll") and hasattr(self, "labor_result_card"):
                    self.labor_scroll.scroll_to(self.labor_result_card, padding=dp(12), animate=True)
            except ValueError as exc:
                self._show_error(self._t("labor_validation_error", message=str(exc)))
                telemetry.log_event(
                    "calculation_error",
                    {"calculator": "labor", "error": str(exc)[:120]},
                )
            except Exception as exc:  # pragma: no cover - UI safeguard
                log.exception("Błąd obliczeń robocizny")
                self._show_error(self._t("calc_error", error=exc))

        def _set_valve_mode(self, mode: str):
            """Przełącza tryb wprowadzania objętości: Kubatura ("K") / Wymiary ("W")."""
            from kivy.metrics import dp

            self._valve_input_mode = "W" if mode == "W" else "K"
            k = self._valve_input_mode == "K"
            if hasattr(self, "valve_vol_box"):
                self.valve_vol_box.height = dp(60) if k else 0
                self.valve_vol_box.opacity = 1 if k else 0
                self.valve_vol_box.disabled = not k
                self.valve_dim_box.height = 0 if k else dp(180)
                self.valve_dim_box.opacity = 0 if k else 1
                self.valve_dim_box.disabled = k
            self._style_valve_mode_buttons()

        def _style_valve_mode_buttons(self):
            k = getattr(self, "_valve_input_mode", "K") == "K"
            if hasattr(self, "valve_btn_mode_k"):
                self._style_app_button(self.valve_btn_mode_k, "ice" if k else "muted")
                self._style_app_button(self.valve_btn_mode_w, "muted" if k else "ice")

        def _open_valve_type_menu(self, caller):
            from kivy.metrics import dp
            from kivymd.uix.menu import MDDropdownMenu

            item_height = dp(46 if self._layout_metrics(dp)["compact"] else 52)
            items = [
                {
                    "text": name,
                    "viewclass": "OneLineListItem",
                    "height": item_height,
                    "theme_text_color": "Custom",
                    "text_color": self._menu_text_color(),
                    "on_release": lambda n=name: self._pick_valve_type(n),
                }
                for name in ZAWORY
            ]
            self._valve_menu = self._menu(caller, items, 4.4, dp(300), dp, MDDropdownMenu)
            self._valve_menu.open()

        def _pick_valve_type(self, name: str):
            self._valve_type = name
            self.valve_btn_type.text = name
            if self._valve_menu:
                self._valve_menu.dismiss()
            if self._last_valve_results is not None:
                self._calculate_valves()

        def _calculate_valves(self):
            if not self._valve_module_available():
                self._refresh_valve_lock_ui()
                return
            self._clear_valve_validation()
            telemetry.log_event("calculation_started", {"calculator": "valves"})
            try:
                if self._valve_input_mode == "W":
                    L = self._parse_required_field(
                        self.valve_in_L, self._t("valve_length")
                    )
                    Wd = self._parse_required_field(
                        self.valve_in_W, self._t("valve_width")
                    )
                    H = self._parse_required_field(
                        self.valve_in_H, self._t("valve_height")
                    )
                    V = L * Wd * H
                else:
                    V = self._parse_required_field(
                        self.valve_in_V, self._t("valve_volume")
                    )
                tp = self._parse_required_field(
                    self.valve_in_tp, self._t("valve_temp_before")
                )
                tz = self._parse_required_field(
                    self.valve_in_tz, self._t("valve_temp_after")
                )
                n_value = self._parse_required_field(
                    self.valve_in_n, self._t("valve_coolers")
                )
                if not float(n_value).is_integer():
                    self._mark_field_error(
                        self.valve_in_n,
                        self._t("invalid_field", name=self._t("valve_coolers")),
                    )
                    raise ValueError(
                        self._t("invalid_field", name=self._t("valve_coolers"))
                    )
                n = int(n_value)
                if n < 1:
                    self._mark_field_error(
                        self.valve_in_n, self._t("valve_coolers_min")
                    )
                    raise ValueError(self._t("valve_coolers_min"))
                q = self._parse_required_field(
                    self.valve_in_q, self._t("valve_flow_per")
                )
                if q <= 0:
                    self._mark_field_error(
                        self.valve_in_q, self._t("valve_flow_positive")
                    )
                    raise ValueError(self._t("valve_flow_positive"))
                # Całkowity przepływ = przepływ na 1 chłodnicę × liczba chłodnic.
                F_total = q * n
                results = calculate_decompression_valves(V, tp, tz, F_total, self._valve_type)
                self._last_valve_results = results
                self._last_valve_total_flow = F_total
                self._render_valve_results(results)
                telemetry.log_event(
                    "calculation_finished", {"calculator": "valves"}
                )
            except ValueError as exc:
                self._show_error(str(exc))
            except Exception as exc:  # pragma: no cover - UI feedback
                telemetry.record_exception(exc, "calculate_valves")
                log.exception("Obliczenia zaworów")
                self._show_error(self._t("calc_error", error=exc))

        def _valve_module_available(self) -> bool:
            """Zwraca True gdy wolno wykonać przeliczenie zaworów.

            Kolejność: trial/PRO-nie-dotyczy/kupiony moduł -> dostęp;
            w przeciwnym razie próba odblokowania jednym tokenem (1 przeliczenie).
            """
            self._refresh_module_valves_status()
            if self._entitlements.has_module(MODULE_VALVES, self._pro_no_ads):
                return True
            # Dolicz tokeny zdobyte za reklamy i spróbuj odblokować jedno przeliczenie.
            self._credit_pending_reward_tokens()
            if self._entitlements.try_unlock_module_with_token(
                MODULE_VALVES, self._pro_no_ads
            ):
                return True
            self._show_error(self._t("valve_locked_hint"))
            return False

        def _refresh_module_valves_status(self):
            """Synchronizuje własność modułu zaworów z warstwą Android (Billing)."""
            if not IS_ANDROID:
                return
            try:
                owned = bool(self._android_activity().isModuleValvesOwned())
            except Exception:  # pragma: no cover - Android only
                log.debug("Nie udało się odczytać statusu modułu zaworów", exc_info=True)
                return
            _sync_module_ownership(self._entitlements, MODULE_VALVES, owned)

        def _refresh_valve_lock_ui(self):
            """Pokazuje/ukrywa kartę blokady modułu zaworów."""
            card = getattr(self, "valve_lock_card", None)
            if card is None:
                return
            self._refresh_module_valves_status()
            locked = not self._entitlements.has_module(MODULE_VALVES, self._pro_no_ads)
            from kivy.metrics import dp

            card.height = dp(196) if locked else 0
            card.opacity = 1 if locked else 0
            card.disabled = not locked

        def _buy_valve_module(self):
            if self._entitlements.has_module(MODULE_VALVES, self._pro_no_ads):
                return
            if not IS_ANDROID:
                self._show_error(self._t("pro_google_play_only"))
                return
            try:
                self._android_activity().launchModulePurchase()
                for delay in (1.0, 4.0, 10.0):
                    Clock.schedule_once(
                        lambda *_: self._after_valve_purchase(), delay
                    )
            except Exception:  # pragma: no cover - Android only
                log.exception("Zakup modułu zaworów")
                self._show_error(self._t("valve_purchase_unavailable"))

        def _after_valve_purchase(self):
            was_locked = not self._entitlements.has_module(
                MODULE_VALVES, self._pro_no_ads
            )
            self._refresh_module_valves_status()
            self._refresh_valve_lock_ui()
            if was_locked and self._entitlements.has_module(
                MODULE_VALVES, self._pro_no_ads
            ):
                self._show_error(self._t("valve_unlocked_thanks"))

        def _render_valve_results(self, results):
            self.valve_lbl_count.text = self._t("valve_count", value=results.ilosc_zaworow)
            self.valve_lbl_delta.text = self._t("valve_delta_t", value=f"{results.delta_T:.2f}")
            total = getattr(self, "_last_valve_total_flow", None)
            self.valve_lbl_totalflow.text = self._t(
                "valve_total_flow", value=("—" if total is None else f"{total:.1f}")
            )
            self.valve_lbl_flow.text = self._t("valve_flow", value=f"{results.Q:.1f}")
            self.valve_lbl_unitflow.text = self._t("valve_unit_flow", value=results.przeplyw_zaworu)

        def _on_tab_switch(self, *args):
            """Zgodność z dawnym callbackiem dolnej nawigacji."""
            name = None
            for a in args:
                if isinstance(a, str) and a in ("freezing", "valves", "labor"):
                    name = a
                    break
                item_name = getattr(a, "name", None)
                if item_name in ("freezing", "valves", "labor"):
                    name = item_name
                    break
            if name is None:
                return
            self._show_tab(name)

        def _show_tab(self, name: str, *, animate: bool = True, report: bool = True):
            """Przelacza widoczna karte bez ruszania wysokosci dolnego paska."""
            if name not in ("freezing", "valves", "labor"):
                return
            self._active_tab_name = name
            tab_widgets = {
                "freezing": getattr(self, "scroll", None),
                "valves": getattr(self, "valve_scroll", None),
                "labor": getattr(self, "labor_scroll", None),
            }
            for tab_name, widget in tab_widgets.items():
                self._set_tab_visibility(widget, tab_name == name)
            self._raise_tab_widget(tab_widgets.get(name))
            if hasattr(self, "bottom_freezing_tab"):
                self.bottom_freezing_tab.set_active(name == "freezing")
            if hasattr(self, "bottom_valves_tab"):
                self.bottom_valves_tab.set_active(name == "valves")
            if hasattr(self, "bottom_labor_tab"):
                self.bottom_labor_tab.set_active(name == "labor")
            if report:
                self._set_active_ad_tab(name)
                telemetry.set_screen(name)
            if animate:
                self._animate_bottom_tab(name)
            if name == "valves":
                self._refresh_valve_lock_ui()
            # Hidden tabs are disabled to avoid touch interception. After a
            # theme switch they need a fresh pass once re-enabled, otherwise
            # KivyMD can keep disabled/dark colors until app restart.
            self._sync_theme_surfaces()
            Clock.schedule_once(lambda *_: self._sync_theme_surfaces(), 0)

        def _set_tab_visibility(self, widget, active: bool):
            """Ukryta zakladka nie moze zostawac niewidzialna warstwa dotykowa."""
            if widget is None:
                return
            if active:
                widget.size_hint = (1, 1)
                widget.pos_hint = {"x": 0, "y": 0}
                widget.opacity = 1
                widget.disabled = False
            else:
                widget.opacity = 0
                widget.disabled = True
                widget.size_hint = (None, None)
                widget.size = (0, 0)
                widget.pos = (0, 0)
                widget.pos_hint = {}

        def _raise_tab_widget(self, widget):
            host = getattr(self, "tab_content_host", None)
            if host is None or widget is None or widget.parent is not host:
                return
            host.remove_widget(widget)
            host.add_widget(widget)

        def _animate_bottom_tab(self, name: str):
            """Lekka reakcja zakładki bez kosztownych animacji layoutu."""
            try:
                tab = {
                    "freezing": self.bottom_freezing_tab,
                    "valves": self.bottom_valves_tab,
                    "labor": self.bottom_labor_tab,
                }[name]
                tab.play()
            except Exception:
                log.debug("Animacja zakładki nie powiodła się", exc_info=True)

        def _set_active_ad_tab(self, tab: str):
            if not IS_ANDROID:
                return
            try:
                self._android_activity().setActiveAdTab(tab)
            except Exception:  # pragma: no cover - Android only
                log.debug("setActiveAdTab nie powiodło się", exc_info=True)

        def _show_product_image(self, img_path: str | None) -> None:
            self.image_box.clear_widgets()
            if img_path:
                self.product_image.source = img_path
                self.product_image.opacity = 1
                self.image_box.add_widget(self.product_image)
                return
            self.product_image.source = ""
            self.product_image.opacity = 0
            self.image_box.add_widget(self.image_placeholder)

        def _android_activity(self):
            from jnius import autoclass, cast

            activity = autoclass("org.kivy.android.PythonActivity").mActivity
            # pyjnius opakowuje mActivity jako bazowy PythonActivity, przez co metody
            # naszej podklasy są niewidoczne -> rzutujemy na właściwą aktywność.
            try:
                return cast(
                    "pl.smilczarek.refrigerationcalc.RefrigerationCalcActivity",
                    activity,
                )
            except Exception:  # pragma: no cover - Android only
                return activity

        def _refresh_pro_status(self, announce: bool = False):
            if not IS_ANDROID:
                self._set_pro_status(False)
                return
            try:
                activity = self._android_activity()
                was_active = self._pro_no_ads
                active = bool(activity.isProNoAdsActive())
                self._set_pro_status(active)
                self._refresh_ad_slot_height()
                if (
                    announce
                    and active
                    and not was_active
                    and not self._pro_thanks_shown
                ):
                    self._pro_thanks_shown = True
                    self._show_error(self._t("pro_thanks"))
            except Exception:  # pragma: no cover - Android only
                log.debug("Nie udało się odczytać statusu PRO", exc_info=True)

        def _refresh_ad_slot_height(self):
            if not IS_ANDROID or self._pro_no_ads:
                return
            try:
                height_dp = int(self._android_activity().getBannerHeightDp())
            except Exception:  # pragma: no cover - Android only
                log.debug("Nie udało się odczytać wysokości banera", exc_info=True)
                return
            if height_dp <= 0 or height_dp == self._native_ad_height_dp:
                return
            self._native_ad_height_dp = height_dp
            self._apply_responsive_layout()

        def _set_pro_status(self, active: bool):
            from kivy.metrics import dp

            self._pro_no_ads = active
            ad_height = self._layout_metrics(dp)["ad_h"]
            if hasattr(self, "btn_pro"):
                self.btn_pro.disabled = active
                self.btn_pro.text = self._t("pro_active") if active else self._t("pro_button")
            if hasattr(self, "ad_label"):
                self.ad_label.text = self._ad_label_text()
            if hasattr(self, "ad_slot"):
                self.ad_slot.height = 0 if active else ad_height
                self.ad_slot.opacity = 0 if active else 1
                self.ad_slot.disabled = active
            if hasattr(self, "footer_label"):
                self.footer_label.text = self._status_footer_text()
            if hasattr(self, "btn_add_product"):
                self.btn_add_product.opacity = 1.0 if active else 0.72

        def _buy_pro(self):
            if self._pro_no_ads:
                return
            if not IS_ANDROID:
                self._show_error(self._t("pro_google_play_only"))
                return
            try:
                telemetry.log_event("pro_purchase_started")
                self._android_activity().launchProPurchase()
                Clock.schedule_once(lambda *_: self._refresh_pro_status(announce=True), 1.0)
                Clock.schedule_once(lambda *_: self._refresh_pro_status(announce=True), 4.0)
                Clock.schedule_once(lambda *_: self._refresh_pro_status(announce=True), 10.0)
            except Exception as exc:  # pragma: no cover - Android only
                telemetry.record_exception(exc, "buy_pro")
                log.exception("Zakup PRO")
                self._show_error(self._t("pro_unavailable"))

        def _credit_pending_reward_tokens(self):
            """Dolicza tokeny zdobyte za reklamy rewarded (most z warstwy Android)."""
            if not IS_ANDROID:
                return
            try:
                pending = int(self._android_activity().consumePendingRewardTokens())
            except Exception:  # pragma: no cover - Android only
                log.debug("Nie udało się odczytać tokenów reward", exc_info=True)
                return
            for _ in range(max(0, pending)):
                self._entitlements.grant_reward_for_ad()

        def _offer_reward_ad(self):
            """Blokada freemium: proponuje obejrzenie reklamy za 1 token."""
            if not IS_ANDROID:
                self._show_error(self._t("product_locked"))
                return
            if not self._entitlements.can_watch_ad():
                self._show_error(self._t("ad_limit_reached"))
                return
            try:
                activity = self._android_activity()
                if not bool(activity.isRewardedAdReady()):
                    self._show_error(self._t("ad_not_ready"))
                    return
                activity.showRewardedAd()
                self._show_error(self._t("watch_ad_for_token"))
                # Po zamknięciu reklamy dolicz token i odśwież status.
                Clock.schedule_once(
                    lambda *_: self._credit_pending_reward_tokens(), 1.0
                )
                Clock.schedule_once(
                    lambda *_: self._after_reward_ad(), 3.0
                )
            except Exception:  # pragma: no cover - Android only
                log.exception("Reklama rewarded")
                self._show_error(self._t("pro_unavailable"))

        def _after_reward_ad(self):
            self._credit_pending_reward_tokens()
            if self._entitlements.reward_tokens() > 0:
                self._show_error(self._t("ad_thanks"))
            self._refresh_valve_lock_ui()

        def _refresh_privacy_button(self):
            """Pokazuje wspolne ustawienia UMP i dobrowolnej telemetrii."""
            btn = getattr(self, "btn_privacy", None)
            if btn is None:
                return
            ad_options_required = False
            if IS_ANDROID:
                try:
                    ad_options_required = bool(
                        self._android_activity().isPrivacyOptionsRequired()
                    )
                except Exception:  # pragma: no cover - Android only
                    log.debug("Nie udało się sprawdzić opcji prywatności", exc_info=True)
            visible = ad_options_required or telemetry.is_available()
            btn.disabled = not visible
            btn.opacity = 1 if visible else 0
            chip = getattr(self, "btn_privacy_chip", None)
            from kivy.metrics import dp

            try:
                target_width = self._layout_metrics(dp)["toolbar_btn_w"]
            except Exception:
                target_width = dp(48)
            btn.width = target_width if visible else 0
            if chip is not None:
                chip.disabled = not visible
                chip.opacity = 1 if visible else 0
                chip.width = target_width if visible else 0
                chip.height = target_width

        def _prompt_telemetry_consent(self):
            if not telemetry.is_available() or telemetry.has_preference():
                self._refresh_privacy_button()
                return
            try:
                from kivymd.uix.button import MDFlatButton, MDRaisedButton
                from kivymd.uix.dialog import MDDialog

                self._telemetry_dialog = MDDialog(
                    title=self._t("telemetry_title"),
                    text=self._t("telemetry_text"),
                    buttons=[
                        MDFlatButton(
                            text=self._t("telemetry_not_now"),
                            on_release=lambda *_: self._set_telemetry_consent(False),
                        ),
                        MDRaisedButton(
                            text=self._t("telemetry_enable"),
                            on_release=lambda *_: self._set_telemetry_consent(True),
                        ),
                    ],
                )
                self._telemetry_dialog.open()
            except Exception:
                log.exception("Nie udało się pokazać zgody Firebase")

        def _set_telemetry_consent(self, enabled: bool):
            telemetry.set_enabled(enabled)
            dialog = getattr(self, "_telemetry_dialog", None)
            if dialog is not None:
                dialog.dismiss()
                self._telemetry_dialog = None
            self._refresh_privacy_button()
            if enabled:
                telemetry.log_event("telemetry_enabled")

        def _close_settings_dialog(self):
            dialog = getattr(self, "_settings_dialog", None)
            if dialog is not None:
                dialog.dismiss()
                self._settings_dialog = None

        def _set_unit_system(self, unit_system: str):
            # TODO: Implement full Imperial/US input and output conversion before enabling.
            if str(unit_system).casefold() == "imperial":
                self._show_error(self._t("units_imperial_disabled"))
                return
            self._unit_system = "metric"
            self._preferences.set_unit_system("metric")
            self._show_error(self._t("units_metric_active"))

        def _open_settings_dialog(self):
            """Menu ustawień pod lewą śnieżynką; gotowe na kolejne sekcje."""
            self._close_product_dialog()
            try:
                from kivy.metrics import dp
                from kivymd.uix.boxlayout import MDBoxLayout
                from kivymd.uix.button import MDFlatButton, MDRaisedButton
                from kivymd.uix.dialog import MDDialog
                from kivymd.uix.label import MDLabel

                content = MDBoxLayout(
                    orientation="vertical",
                    spacing=dp(10),
                    adaptive_height=True,
                )
                content.add_widget(
                    MDLabel(
                        text=self._t("settings_intro"),
                        theme_text_color="Hint",
                        font_style="Body2",
                        adaptive_height=True,
                    )
                )
                content.add_widget(
                    MDLabel(
                        text=self._t("units_title"),
                        theme_text_color="Custom",
                        text_color=BRAND_ICE,
                        font_style="Subtitle1",
                        adaptive_height=True,
                    )
                )
                content.add_widget(
                    MDLabel(
                        text=self._t("units_metric_active"),
                        theme_text_color="Custom",
                        text_color=(0.85, 0.98, 1.0, 1),
                        font_style="Body2",
                        adaptive_height=True,
                    )
                )
                content.add_widget(
                    MDLabel(
                        text=self._t("units_imperial_disabled"),
                        theme_text_color="Hint",
                        font_style="Caption",
                        adaptive_height=True,
                    )
                )
                metric_row = MDBoxLayout(
                    orientation="horizontal",
                    size_hint_y=None,
                    height=dp(42),
                )
                metric_button = MDRaisedButton(
                    text=self._t("units_metric"),
                    size_hint_x=1,
                    on_release=lambda *_: self._set_unit_system("metric"),
                )
                self._style_app_button(metric_button, "ice")
                metric_row.add_widget(metric_button)
                content.add_widget(metric_row)
                imperial_row = MDBoxLayout(
                    orientation="horizontal",
                    size_hint_y=None,
                    height=dp(42),
                )
                imperial_button = MDFlatButton(
                    text=self._t("units_imperial"),
                    size_hint_x=1,
                    disabled=True,
                )
                imperial_row.add_widget(imperial_button)
                content.add_widget(imperial_row)
                self._settings_dialog = MDDialog(
                    title=self._t("settings_title"),
                    type="custom",
                    content_cls=content,
                    buttons=[
                        MDFlatButton(
                            text=self._t("close"),
                            on_release=lambda *_: self._close_settings_dialog(),
                        ),
                    ],
                )
                self._settings_dialog.open()
                telemetry.log_event("settings_opened", {"section": "general"})
            except Exception:
                log.exception("Ustawienia aplikacji")

        def _close_privacy_dialog(self):
            dialog = getattr(self, "_privacy_dialog", None)
            if dialog is not None:
                dialog.dismiss()
                self._privacy_dialog = None

        def _open_privacy_options(self):
            """Otwiera ustawienia telemetrii i, gdy trzeba, zgody reklamowej."""
            if not IS_ANDROID:
                return
            try:
                from kivymd.uix.button import MDFlatButton, MDRaisedButton
                from kivymd.uix.dialog import MDDialog

                analytics_available = telemetry.is_available()
                enabled = telemetry.is_enabled()
                text = self._t("telemetry_on" if enabled else "telemetry_off")
                buttons = []
                if analytics_available:
                    buttons.append(
                        MDRaisedButton(
                            text=self._t(
                                "telemetry_disable" if enabled else "telemetry_enable"
                            ),
                            on_release=lambda *_: self._change_telemetry_from_settings(
                                not enabled
                            ),
                        )
                    )
                if bool(self._android_activity().isPrivacyOptionsRequired()):
                    buttons.append(
                        MDFlatButton(
                            text=self._t("ad_privacy"),
                            on_release=lambda *_: self._open_ad_privacy_options(),
                        )
                    )
                buttons.append(
                    MDFlatButton(
                        text=self._t("close"),
                        on_release=lambda *_: self._close_privacy_dialog(),
                    )
                )
                self._privacy_dialog = MDDialog(
                    title=self._t("privacy_title"),
                    text=text,
                    buttons=buttons,
                )
                self._privacy_dialog.open()
                telemetry.log_event("settings_opened", {"section": "privacy"})
            except Exception:  # pragma: no cover - Android only
                log.exception("Ustawienia prywatności")

        def _change_telemetry_from_settings(self, enabled: bool):
            telemetry.set_enabled(enabled)
            self._close_privacy_dialog()
            if enabled:
                telemetry.log_event("telemetry_enabled")

        def _open_ad_privacy_options(self):
            self._close_privacy_dialog()
            try:
                self._android_activity().showPrivacyOptionsForm()
            except Exception:  # pragma: no cover - Android only
                log.exception("Formularz prywatności reklam")

        def _open_custom_product_dialog(self):
            if not self._pro_no_ads:
                self._show_error(self._t("custom_product_pro"))
                return
            limit = max(1, telemetry.remote_int("custom_products_limit", 250))
            if custom_products.count() >= limit:
                self._show_error(self._t("custom_product_limit", limit=limit))
                return
            try:
                from kivy.metrics import dp
                from kivy.uix.scrollview import ScrollView
                from kivymd.uix.boxlayout import MDBoxLayout
                from kivymd.uix.button import MDFlatButton, MDRaisedButton
                from kivymd.uix.dialog import MDDialog
                from kivymd.uix.textfield import MDTextField

                outer = MDBoxLayout(
                    orientation="vertical",
                    size_hint_y=None,
                    height=dp(520),
                )
                scroll = ScrollView()
                form = MDBoxLayout(
                    orientation="vertical",
                    spacing=dp(8),
                    padding=[0, dp(4), dp(8), dp(8)],
                    size_hint_y=None,
                )
                form.bind(minimum_height=form.setter("height"))
                field_specs = [
                    ("nazwa", "custom_name", None, ""),
                    (
                        "kategoria",
                        "custom_category",
                        None,
                        self._selected_category or "",
                    ),
                    ("wilgotnosc", "custom_moisture", _numeric_input_filter, ""),
                    ("t_zam", "custom_tzam", _numeric_input_filter, ""),
                    ("c1", "custom_c1", _numeric_input_filter, ""),
                    ("c2", "custom_c2", _numeric_input_filter, ""),
                    ("l1", "custom_l1", _numeric_input_filter, ""),
                    ("bialko", "custom_protein", _numeric_input_filter, ""),
                    ("tluszcz", "custom_fat", _numeric_input_filter, ""),
                    ("weglowodany", "custom_carbs", _numeric_input_filter, ""),
                    ("blonnik", "custom_fiber", _numeric_input_filter, ""),
                    ("popiol", "custom_ash", _numeric_input_filter, ""),
                ]
                self._custom_product_fields = {}
                for key, label_key, input_filter, value in field_specs:
                    field = MDTextField(
                        hint_text=self._t(label_key),
                        text=value,
                        input_filter=input_filter,
                        size_hint_y=None,
                        height=dp(62),
                    )
                    field.bind(
                        text=lambda widget, _value: self._clear_field_error(widget)
                    )
                    self._custom_product_fields[key] = field
                    form.add_widget(field)
                scroll.add_widget(form)
                outer.add_widget(scroll)

                self._custom_product_dialog = MDDialog(
                    title=self._t("custom_product_title"),
                    type="custom",
                    content_cls=outer,
                    buttons=[
                        MDFlatButton(
                            text=self._t("cancel"),
                            on_release=lambda *_: self._close_custom_product_dialog(),
                        ),
                        MDRaisedButton(
                            text=self._t("save"),
                            on_release=lambda *_: self._save_custom_product(),
                        ),
                    ],
                )
                self._custom_product_dialog.open()
                telemetry.log_event("settings_opened", {"section": "custom_product"})
            except Exception as exc:
                telemetry.record_exception(exc, "open_custom_product")
                log.exception("Formularz własnego produktu")
                self._show_error(self._t("calc_error", error=exc))

        def _close_custom_product_dialog(self):
            dialog = getattr(self, "_custom_product_dialog", None)
            if dialog is not None:
                dialog.dismiss()
                self._custom_product_dialog = None

        def _save_custom_product(self):
            fields = getattr(self, "_custom_product_fields", {})
            values = {key: field.text for key, field in fields.items()}
            try:
                product = create_custom_product(values)
                custom_products.upsert(product)
            except ValueError as exc:
                field = fields.get(str(exc))
                if field is not None:
                    self._mark_field_error(field, self._t("custom_required"))
                self._show_error(self._t("custom_required"))
                return
            except OSError as exc:
                telemetry.record_exception(exc, "save_custom_product")
                self._show_error(self._t("calc_error", error=exc))
                return

            custom_products.merge_into(catalog)
            categories[:] = list_categories(catalog)
            self._selected_category = product.kategoria
            self._selected_product = product.nazwa
            self._preferences.add_recent_product(product.kategoria, product.nazwa)
            self.btn_category.text = self._display_category(product.kategoria)
            self.btn_product.text = product.nazwa
            self.btn_product.disabled = False
            self.category_error_line.opacity = 0
            self.product_error_line.opacity = 0
            self._show_product_image(None)
            self._close_custom_product_dialog()
            self._show_error(self._t("custom_product_saved"))
            telemetry.log_event("custom_product_saved")

        def _open_category_menu(self, caller):
            from kivy.metrics import dp
            from kivymd.uix.menu import MDDropdownMenu

            item_height = dp(46 if self._layout_metrics(dp)["compact"] else 52)
            featured, remaining = _ordered_mobile_categories(
                categories, self._display_category
            )
            ordered = featured + remaining
            items = [
                {
                    "text": self._display_category(cat),
                    "viewclass": "OneLineListItem",
                    "height": item_height,
                    "theme_text_color": "Custom",
                    "text_color": self._menu_text_color(),
                    "on_release": lambda c=cat: self._pick_category(c),
                }
                for cat in ordered
            ]
            if featured and remaining:
                items.insert(
                    len(featured),
                    {
                        "viewclass": "MDSeparator",
                        "height": dp(1),
                        "color": self.theme_cls.divider_color,
                    },
                )
            self._cat_menu = self._menu(caller, items, 3.7, dp(390), dp, MDDropdownMenu)
            self._cat_menu.open()

        def _pick_category(self, category: str):
            self._selected_category = category
            self._selected_product = None
            self.btn_category.text = self._display_category(category)
            self.btn_product.text = self._t("choose_product")
            self.btn_product.disabled = False
            self.category_error_line.opacity = 0
            self.product_error_line.opacity = 0
            self._show_product_image(None)
            if self._cat_menu:
                self._cat_menu.dismiss()

        def _open_product_menu(self, caller):
            from kivy.metrics import dp
            from kivy.uix.scrollview import ScrollView
            from kivymd.uix.boxlayout import MDBoxLayout
            from kivymd.uix.button import MDFlatButton
            from kivymd.uix.dialog import MDDialog
            from kivymd.uix.list import MDList
            from kivymd.uix.textfield import MDTextField

            if not self._selected_category:
                return
            self._close_product_dialog()
            self._product_dialog_names = _mobile_product_names(
                catalog, self._selected_category
            )
            self._product_dialog_indexes = {
                name: index for index, name in enumerate(self._product_dialog_names)
            }

            outer = MDBoxLayout(
                orientation="vertical",
                spacing=dp(8),
                size_hint_y=None,
                height=min(dp(520), max(dp(340), Window.height * 0.66)),
            )
            self._product_search_field = MDTextField(
                hint_text=self._t("search_products"),
                icon_right="magnify",
                mode="rectangle",
                size_hint_y=None,
                height=dp(58),
            )
            outer.add_widget(self._product_search_field)
            results_scroll = ScrollView(do_scroll_x=False)
            self._product_results_list = MDList()
            results_scroll.add_widget(self._product_results_list)
            outer.add_widget(results_scroll)

            self._product_dialog = MDDialog(
                title=self._t("product_picker_title"),
                type="custom",
                content_cls=outer,
                buttons=[
                    MDFlatButton(
                        text=self._t("close"),
                        on_release=lambda *_: self._close_product_dialog(),
                    )
                ],
            )
            self._product_search_field.bind(
                text=lambda _field, value: self._refresh_product_search_results(value)
            )
            self._refresh_product_search_results("")
            self._product_dialog.open()

        def _add_product_search_item(self, name: str, item_height) -> None:
            from kivymd.uix.list import OneLineListItem

            index = self._product_dialog_indexes.get(name, 10**9)
            unlocked = self._entitlements.is_unlocked(self._pro_no_ads)
            allowed = unlocked or index < FREE_PRODUCTS_PER_CATEGORY
            item = OneLineListItem(
                text=name if allowed else f"{name}{self._t('locked_suffix')}",
                height=item_height,
                theme_text_color="Custom",
                text_color=(
                    self._menu_text_color()
                    if allowed
                    else (0.55, 0.58, 0.62, 1)
                ),
                on_release=(
                    (lambda *_args, n=name: self._pick_product(n))
                    if allowed
                    else (lambda *_args: self._on_locked_product())
                ),
            )
            self._product_results_list.add_widget(item)

        def _add_product_search_heading(self, text: str, dp) -> None:
            from kivymd.uix.label import MDLabel

            self._product_results_list.add_widget(
                MDLabel(
                    text=text,
                    size_hint_y=None,
                    height=dp(34),
                    font_style="Caption",
                    theme_text_color="Secondary",
                    padding=(dp(12), 0),
                )
            )

        def _refresh_product_search_results(self, query: str) -> None:
            from kivy.metrics import dp

            if self._product_results_list is None:
                return
            self._product_results_list.clear_widgets()
            names = _search_product_names(self._product_dialog_names, query)
            item_height = dp(46 if self._layout_metrics(dp)["compact"] else 52)
            if not names:
                self._add_product_search_heading(self._t("no_products_found"), dp)
                return

            if not str(query or "").strip():
                recent = self._preferences.recent_products_for_category(
                    self._selected_category or "",
                    self._product_dialog_names,
                )[:4]
                if recent:
                    self._add_product_search_heading(self._t("recent_products"), dp)
                    for name in recent:
                        self._add_product_search_item(name, item_height)
                    self._add_product_search_heading(self._t("all_products"), dp)

            for name in names:
                self._add_product_search_item(name, item_height)

        def _close_product_dialog(self) -> None:
            dialog = getattr(self, "_product_dialog", None)
            if dialog is not None:
                dialog.dismiss()
            self._product_dialog = None
            self._product_search_field = None
            self._product_results_list = None

        def _on_locked_product(self):
            if self._prod_menu:
                self._prod_menu.dismiss()
            self._close_product_dialog()
            self._show_error(self._t("product_locked"))

        def _pick_product(self, name: str):
            self._selected_product = name
            self._preferences.add_recent_product(
                self._selected_category or "", name
            )
            self.btn_product.text = name
            self.product_error_line.opacity = 0
            img = _safe_image_path(name)
            self._show_product_image(img)
            if self._prod_menu:
                self._prod_menu.dismiss()
            self._close_product_dialog()

        # --- akcje -------------------------------------------------------
        def _toggle_mass_unit(self):
            self._set_mass_unit("t" if self._mass_unit == "kg" else "kg")

        def _set_mass_unit(self, unit: str):
            self._mass_unit = "t" if unit == "t" else "kg"
            if hasattr(self, "btn_unit"):
                self.btn_unit.text = self._mass_unit
                self._style_app_button(self.btn_unit, "ice")

        def _toggle_theme(self):
            self._close_product_dialog()
            is_dark = self.theme_cls.theme_style == "Dark"
            self.theme_cls.theme_style = "Light" if is_dark else "Dark"
            self._sync_theme_surfaces()
            Clock.schedule_once(lambda *_: self._sync_theme_surfaces(), 0)
            if hasattr(self, "btn_theme"):
                self.btn_theme.icon = "weather-night" if self.theme_cls.theme_style == "Dark" else "weather-sunny"

        def _reset_inputs(self):
            for field_ in (self.in_m, self.in_T1, self.in_T2, self.in_t):
                field_.text = ""
            self.lbl_total.text = self._total_text()
            for entry in self.bars.values():
                entry["bar"].value = 0
                entry["value_label"].text = "—"
            self._last_results = None
            self._clear_main_validation()

        def _build_pdf_bytes(self) -> bytes | None:
            """Buduje PDF bez ujawniania źródłowych właściwości produktu."""
            runtime_font = _runtime_font_path()
            if runtime_font is not None:
                try:
                    from tpof.core.pdf_report import build_pdf

                    img_path = _safe_image_path(self._last_results.produkt.nazwa)
                    return build_pdf(
                        self._last_results,
                        font_path=runtime_font,
                        product_image_path=Path(img_path) if img_path else None,
                        watermark_image_path=None,
                    )
                except ImportError:
                    pass
            try:
                _purge_host_arch_fonttools_so()
                from tpof.core.pdf_report_mobile import build_pdf_simple
            except ImportError:
                return None
            return build_pdf_simple(self._last_results, font_path=runtime_font)

        def _export_pdf(self):
            if self._last_results is None:
                self._show_error(self._t("pdf_first"))
                return
            try:
                pdf_bytes = self._build_pdf_bytes()
                if pdf_bytes is None:
                    self._show_error(self._t("pdf_unavailable"))
                    return
                out_dir = _pdf_output_dir()
                out_dir.mkdir(parents=True, exist_ok=True)
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                nazwa = self._last_results.produkt.nazwa.replace(" ", "_")
                out_path = out_dir / f"RefrigerationCalc_{nazwa}_{ts}.pdf"
                out_path.write_bytes(pdf_bytes)
                telemetry.log_event("pdf_generated", {"calculator": "freezing"})
                if IS_ANDROID:
                    try:
                        self._android_activity().shareFile(
                            str(out_path),
                            "application/pdf",
                            self._t("pdf_share_subject"),
                            self._t("pdf_share_text"),
                        )
                        telemetry.log_event(
                            "report_shared", {"calculator": "freezing"}
                        )
                    except Exception:  # pragma: no cover - Android only
                        log.exception("Udostępnianie PDF")
                        self._show_error(self._t("saved", path=out_path))
                else:
                    self._show_error(self._t("saved", path=out_path))
            except Exception as exc:  # pragma: no cover - UI feedback
                telemetry.record_exception(exc, "export_pdf")
                log.exception("Eksport PDF")
                self._show_error(self._t("pdf_error", error=exc))

        def _show_error(self, message: str):
            notice = getattr(self, "center_notice", None)
            if notice is not None:
                try:
                    notice.show(message)
                    return
                except Exception:
                    log.debug("Centralny komunikat nie powiodl sie", exc_info=True)
            try:
                from kivymd.uix.snackbar import Snackbar

                Snackbar(text=message, duration=3).open()
            except Exception:  # pragma: no cover
                log.warning("Snackbar fail: %s", message)

        def _parse_float(self, raw: str, name: str) -> float:
            try:
                return float((raw or "").replace(",", "."))
            except (TypeError, ValueError, AttributeError) as exc:
                raise ValueError(self._t("invalid_field", name=name)) from exc

        def _parse_int(self, raw: str, name: str) -> int:
            value = self._parse_float(raw, name)
            if not float(value).is_integer():
                raise ValueError(self._t("invalid_field", name=name))
            return int(value)

        def _calculate(self):
            self._clear_main_validation()
            telemetry.log_event("calculation_started", {"calculator": "freezing"})
            try:
                if not self._selected_category:
                    self.category_error_line.opacity = 1
                    self.product_error_line.opacity = 1
                    self.scroll.scroll_y = 1
                    self._show_error(self._t("pick_product_error"))
                    return
                if not self._selected_product:
                    self.product_error_line.opacity = 1
                    self.scroll.scroll_y = 1
                    self._show_error(self._t("pick_product_error"))
                    return
                product = find_product(catalog, self._selected_category, self._selected_product)
                if product is None:
                    self.product_error_line.opacity = 1
                    self._show_error(self._t("missing_product_error"))
                    return

                # Freemium: po wygaśnięciu triala (bez PRO) liczymy tylko dozwolone produkty.
                if not self._entitlements.is_unlocked(self._pro_no_ads):
                    products = list_products(catalog, self._selected_category)
                    try:
                        idx = products.index(self._selected_product)
                    except ValueError:
                        idx = FREE_PRODUCTS_PER_CATEGORY
                    if not self._entitlements.is_product_allowed(idx, self._pro_no_ads):
                        # Najpierw dolicz tokeny zdobyte za obejrzane reklamy.
                        self._credit_pending_reward_tokens()
                        # Spróbuj odblokować to przeliczenie jednym tokenem.
                        if not self._entitlements.try_unlock_product_with_token(
                            idx, self._pro_no_ads
                        ):
                            self._offer_reward_ad()
                            return

                masa = self._parse_required_field(self.in_m, self._t("field_mass"))
                if masa <= 0:
                    self._mark_field_error(
                        self.in_m,
                        self._t("invalid_field", name=self._t("field_mass")),
                    )
                    raise ValueError(
                        self._t("invalid_field", name=self._t("field_mass"))
                    )
                if self._mass_unit == "t":
                    masa *= 1000.0
                T1 = self._parse_required_field(
                    self.in_T1, self._t("field_temp_start")
                )
                T2 = self._parse_required_field(
                    self.in_T2, self._t("field_temp_end")
                )
                warnings = [
                    message
                    for message in (
                        self._validate_temperature_input(
                            self.in_T1, self._t("field_temp_start"), T1
                        ),
                        self._validate_temperature_input(
                            self.in_T2, self._t("field_temp_end"), T2
                        ),
                    )
                    if message
                ]
                if warnings:
                    self._show_error(warnings[0])
                czas = self._parse_required_field(self.in_t, self._t("field_time"))
                if czas <= 0:
                    self._mark_field_error(
                        self.in_t,
                        self._t("invalid_field", name=self._t("field_time")),
                    )
                    raise ValueError(
                        self._t("invalid_field", name=self._t("field_time"))
                    )

                inputs = FreezingInputs(masa_kg=masa, T_pocz_C=T1, T_konc_C=T2, czas_h=czas)
                results = calculate_freezing(inputs, product)
                self._last_results = results
                self._render_results(results)
                telemetry.log_event(
                    "calculation_finished",
                    {
                        "calculator": "freezing",
                        "mass_unit": self._mass_unit,
                        "custom_product": custom_products.contains(
                            product.kategoria, product.nazwa
                        ),
                    },
                )
            except ValueError as exc:
                self._show_error(str(exc))
            except Exception as exc:  # pragma: no cover
                telemetry.record_exception(exc, "calculate_freezing")
                log.exception("Błąd obliczeń")
                self._show_error(self._t("calc_error", error=exc))

        def _render_results(self, results, scroll=True):
            total = results.P_total_kW or 0.0
            self.lbl_total.text = self._total_text(total)

            stages = {
                "schladzanie": results.P_schladzanie_kW,
                "zamrozenie": results.P_zamrozenie_kW,
                "domrozenie": results.P_domrozenie_kW,
            }
            for key, value in stages.items():
                pct = (value / total * 100.0) if total > 0 else 0.0
                self.bars[key]["bar"].value = pct
                self.bars[key]["value_label"].text = f"{value:.2f} kW ({pct:.0f}%)"

            # Auto-scroll do wyników po obliczeniu — żeby nie chowały się pod akcjami.
            if scroll:
                try:
                    self.scroll.scroll_to(self.results_card, padding=dp(12), animate=True)
                except Exception:  # pragma: no cover
                    pass

    ShockerCalcApp().run()


if __name__ == "__main__":
    main()

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
from pathlib import Path

from tpof.core import (
    Product,
    list_categories,
    list_products,
    load_products,
)
from tpof.mobile import telemetry, theme
from tpof.mobile.android_bridge import _purge_host_arch_fonttools_so, _runtime_font_path
from tpof.mobile.catalog import _safe_image_path
from tpof.mobile.constants import (
    APP_NAME,
    BRAND_ICE,
    IS_ANDROID,
    STAGE_COLORS,
    SURFACE_DARK,
)
from tpof.mobile.dialogs.custom_product import CustomProductDialogController
from tpof.mobile.dialogs.labor_rates import LaborRatesDialogController
from tpof.mobile.dialogs.legal import LegalDialogController
from tpof.mobile.dialogs.settings import SettingsDialogController
from tpof.mobile.entitlements import (
    FREE_PRODUCTS_PER_CATEGORY,
    MODULE_VALVES,
    Entitlements,
)
from tpof.mobile.i18n import display_category, translate
from tpof.mobile.layout import clamp, compute_metrics
from tpof.mobile.navigation import TabNavigationController
from tpof.mobile.paths import DATA_PATH, PROJECT_ROOT
from tpof.mobile.pdf_export import _pdf_output_dir
from tpof.mobile.services.entitlements_ui import _sync_module_ownership
from tpof.mobile.services.monetization import ProMonetizationController
from tpof.mobile.settings_state import SettingsStateController
from tpof.mobile.tabs.freezing import FreezingTabController
from tpof.mobile.tabs.labor import LaborTabController
from tpof.mobile.tabs.valves import ValvesTabController
from tpof.mobile.user_data import CustomProductStore, UiPreferences
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
        from kivymd.app import MDApp
        from kivymd.uix.boxlayout import MDBoxLayout
        from kivymd.uix.button import MDIconButton, MDRaisedButton
        from kivymd.uix.label import MDIcon, MDLabel

        from tpof.mobile.widgets import (
            BottomNavTab,
            BrandToolbar,
            CenterNotice,
            FrostBackground,
            FrostChip,
            LaborPieChart,
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
            try:
                Window.softinput_mode = "below_target"
            except Exception:  # pragma: no cover
                log.debug("Could not set soft keyboard mode.", exc_info=True)

            self._themed_cards = []
            self._language = "pl"
            self._preferences = UiPreferences()
            self._hints_enabled = self._preferences.hints_enabled
            self._privacy_dialog = None
            self._telemetry_dialog = None
            self._validation_bound_fields = set()
            self._native_ad_height_dp = 0
            self._pro_no_ads = False
            self._entitlements = Entitlements()
            self._entitlements.ensure_started()
            self._legal_dialog_controller = LegalDialogController(
                translate=self._t,
                project_root=PROJECT_ROOT,
            )
            self._settings_state = SettingsStateController(
                preferences=self._preferences,
                translate=self._t,
                refresh_settings_ui=lambda: self._settings_dialog_controller.refresh(),
                convert_labor_currency=lambda currency: (
                    self._labor_tab_controller.convert_additional_field_currency(
                        currency
                    )
                ),
                refresh_labor_results=lambda: (
                    self._labor_tab_controller.refresh_results()
                ),
                show_message=self._show_error,
                schedule_once=Clock.schedule_once,
            )
            self._custom_product_dialog_controller = CustomProductDialogController(
                translate=self._t,
                is_pro=lambda: self._pro_no_ads,
                get_product_limit=lambda: telemetry.remote_int(
                    "custom_products_limit",
                    250,
                ),
                store=custom_products,
                catalog=catalog,
                categories=categories,
                get_selected_category=lambda: (
                    self._freezing_tab_controller.selected_category
                ),
                select_saved_product=lambda product: (
                    self._freezing_tab_controller.select_saved_product(product)
                ),
                numeric_input_filter=_numeric_input_filter,
                clear_field_error=self._clear_field_error,
                mark_field_error=self._mark_field_error,
                show_message=self._show_error,
                log_event=telemetry.log_event,
                record_exception=telemetry.record_exception,
            )
            self._settings_dialog_controller = SettingsDialogController(
                translate=self._t,
                style_button=self._style_app_button,
                card_bg=self._card_bg,
                get_display_currency=lambda: self._settings_state.display_currency,
                get_exchange_rates=lambda: self._settings_state.exchange_rates,
                get_language=lambda: self._language,
                get_auto_update=lambda: self._settings_state.currency_auto_update,
                get_status_text=self._settings_state.status_text,
                on_set_unit_system=self._settings_state.set_unit_system,
                on_set_display_currency=self._settings_state.set_display_currency,
                on_toggle_auto_update=self._settings_state.toggle_currency_auto_update,
                on_open_legal=self._open_legal_dialog,
            )
            self._labor_rates_dialog_controller = LaborRatesDialogController(
                translate=self._t,
                get_values=lambda: self._preferences.labor_rate_values,
                save_values=self._preferences.set_labor_rate_values,
                reset_values=self._preferences.reset_labor_rate_values,
                clear_field_error=self._clear_field_error,
                mark_field_error=self._mark_field_error,
                numeric_input_filter=_numeric_input_filter,
                invalidate_results=lambda: self._labor_tab_controller.invalidate_results(),
                show_message=self._show_error,
                on_opened=lambda: telemetry.log_event(
                    "settings_opened", {"section": "labor_rates"}
                ),
                on_saved=lambda: telemetry.log_event(
                    "settings_saved", {"section": "labor_rates"}
                ),
                on_reset=lambda: telemetry.log_event(
                    "settings_reset", {"section": "labor_rates"}
                ),
                report_exception=telemetry.record_exception,
            )
            self._labor_tab_controller = LaborTabController(
                translate=self._t,
                get_language=lambda: self._language,
                get_display_currency=lambda: self._settings_state.display_currency,
                get_exchange_rates=lambda: self._settings_state.exchange_rates,
                get_rate_values=lambda: self._preferences.labor_rate_values,
                reset_rate_values=self._preferences.reset_labor_rate_values,
                is_pro=lambda: self._pro_no_ads,
                open_rates_dialog=lambda: self._labor_rates_dialog_controller.open(),
                card_bg=self._card_bg,
                total_color=STAGE_COLORS["total"],
                chart_factory=LaborPieChart,
                numeric_input_filter=_numeric_input_filter,
                register_themed_card=self._themed_cards.append,
                bind_keyboard_scroll=self._bind_keyboard_scroll,
                style_button=self._style_app_button,
                clear_field_error=self._clear_field_error,
                mark_field_error=self._mark_field_error,
                show_message=self._show_error,
                log_event=telemetry.log_event,
                get_active_tab=lambda: getattr(
                    self,
                    "_active_tab_name",
                    "labor",
                ),
                is_dark=lambda: self.theme_cls.theme_style == "Dark",
            )
            self._valves_tab_controller = ValvesTabController(
                translate=self._t,
                card_bg=self._card_bg,
                total_color=STAGE_COLORS["total"],
                numeric_input_filter=_numeric_input_filter,
                register_themed_card=self._themed_cards.append,
                bind_keyboard_scroll=self._bind_keyboard_scroll,
                style_button=self._style_app_button,
                clear_field_error=self._clear_field_error,
                mark_field_error=self._mark_field_error,
                show_message=self._show_error,
                log_event=telemetry.log_event,
                record_exception=telemetry.record_exception,
                can_calculate=self._valve_module_available,
                on_access_denied=self._refresh_valve_lock_ui,
                on_buy=self._buy_valve_module,
                on_watch=self._offer_reward_ad,
                menu_factory=self._menu,
                is_compact=lambda: bool(self._layout_metrics(dp)["compact"]),
                menu_text_color=self._menu_text_color,
            )
            self._freezing_tab_controller = FreezingTabController(
                catalog=catalog,
                categories=categories,
                translate=self._t,
                display_category=self._display_category,
                card_bg=self._card_bg,
                total_color=STAGE_COLORS["total"],
                numeric_input_filter=_numeric_input_filter,
                register_themed_card=self._themed_cards.append,
                bind_keyboard_scroll=self._bind_keyboard_scroll,
                style_button=self._style_app_button,
                clear_field_error=self._clear_field_error,
                mark_field_error=self._mark_field_error,
                show_message=self._show_error,
                log_event=telemetry.log_event,
                record_exception=telemetry.record_exception,
                ensure_product_access=self._ensure_freezing_product_access,
                is_product_selectable=lambda index: (
                    self._entitlements.is_unlocked(self._pro_no_ads)
                    or index < FREE_PRODUCTS_PER_CATEGORY
                ),
                recent_products=(
                    self._preferences.recent_products_for_category
                ),
                add_recent_product=self._preferences.add_recent_product,
                is_custom_product=custom_products.contains,
                resolve_product_image=_safe_image_path,
                on_add_custom_product=self._custom_product_dialog_controller.open,
                on_export_pdf=self._export_pdf,
                menu_factory=self._menu,
                is_compact=lambda: bool(
                    self._layout_metrics(dp)["compact"]
                ),
                menu_text_color=self._menu_text_color,
                divider_color=lambda: self.theme_cls.divider_color,
                hints_enabled=lambda: self._hints_enabled,
            )
            self._monetization = ProMonetizationController(
                is_android=IS_ANDROID,
                translate=self._t,
                get_android_activity=self._android_activity,
                schedule_once=Clock.schedule_once,
                on_state_changed=self._apply_pro_ui_state,
                refresh_ad_slot_height=self._refresh_ad_slot_height,
                show_message=self._show_error,
                log_event=telemetry.log_event,
                record_exception=telemetry.record_exception,
            )

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

            # Własny host zakładek: tło pozostaje widoczne, a dolny pasek nie
            # może już zapadać obszaru treści jak MDBottomNavigation.
            self.tab_content_host = FloatLayout(size_hint=(1, 1))
            self.tab_frost_background = FrostBackground(size_hint=(1, 1))
            self.tab_content_host.add_widget(self.tab_frost_background)
            freezing_scroll = self._freezing_tab_controller.build().scroll
            freezing_scroll.size_hint = (1, 1)
            valve_scroll = self._valves_tab_controller.build().scroll
            valve_scroll.size_hint = (1, 1)
            labor_scroll = self._labor_tab_controller.build().scroll
            labor_scroll.size_hint = (1, 1)
            self.tab_content_host.add_widget(freezing_scroll)
            self.tab_content_host.add_widget(valve_scroll)
            self.tab_content_host.add_widget(labor_scroll)
            root.add_widget(self.tab_content_host)

            self.bottom_nav = self._build_bottom_nav(dp, MDBoxLayout)
            root.add_widget(self.bottom_nav)
            self._active_tab_name = "freezing"
            self._navigation_controller = TabNavigationController(
                get_tab_widgets=lambda: {
                    "freezing": self._freezing_tab_controller.scroll,
                    "valves": self._valves_tab_controller.scroll,
                    "labor": self._labor_tab_controller.scroll,
                },
                get_nav_tabs=lambda: {
                    "freezing": self.bottom_freezing_tab,
                    "valves": self.bottom_valves_tab,
                    "labor": self.bottom_labor_tab,
                },
                get_host=lambda: self.tab_content_host,
                set_active_name=lambda name: setattr(self, "_active_tab_name", name),
                report_tab=self._report_tab,
                on_tab_enter=lambda name: (
                    self._refresh_valve_lock_ui() if name == "valves" else None
                ),
                refresh_theme=self._sync_theme_surfaces,
                schedule_once=Clock.schedule_once,
                logger=log,
            )
            self._show_tab("freezing", animate=False, report=False)

            root.add_widget(self._build_footer(dp, MDBoxLayout, MDLabel, MDRaisedButton))
            root.add_widget(self._build_ad_slot(dp, MDBoxLayout, MDIcon, MDLabel))
            self.center_notice = CenterNotice()
            self.root_host.add_widget(self.center_notice)
            self._sync_theme_surfaces()
            Window.bind(size=self._apply_responsive_layout)
            self._apply_responsive_layout()
            self._monetization.start()
            Clock.schedule_once(lambda *_: self._refresh_ad_slot_height(), 1.2)
            Clock.schedule_once(lambda *_: self._refresh_ad_slot_height(), 3.5)
            Clock.schedule_once(lambda *_: self._refresh_ad_slot_height(), 7.0)
            Clock.schedule_once(lambda *_: self._refresh_privacy_button(), 3.0)
            Clock.schedule_once(lambda *_: self._refresh_privacy_button(), 8.0)
            Clock.schedule_once(lambda *_: self._refresh_valve_lock_ui(), 1.0)
            Clock.schedule_once(lambda *_: self._refresh_valve_lock_ui(), 4.0)
            Clock.schedule_once(lambda *_: self._apply_hints(), 0.2)
            Clock.schedule_once(lambda *_: self._prompt_telemetry_consent(), 2.0)
            Clock.schedule_once(
                lambda *_: self._settings_state.refresh_exchange_rates_async(),
                1.0,
            )
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
            self._freezing_tab_controller.close_product_dialog()
            self._language = "en" if self._language == "pl" else "pl"
            self._refresh_texts()
            self._settings_state.refresh_ui()

        def _toggle_hints(self):
            self._hints_enabled = not self._hints_enabled
            self._preferences.set_hints_enabled(self._hints_enabled)
            self._apply_hints()
            self._apply_responsive_layout()
            self._show_error(self._t("hints_on" if self._hints_enabled else "hints_off"))
            telemetry.log_event("hints_toggled", {"enabled": self._hints_enabled})

        def _hint_field_items(self):
            items = list(self._freezing_tab_controller.hint_field_items())
            items.extend(self._valves_tab_controller.hint_field_items())
            items.extend(self._labor_tab_controller.hint_field_items())
            return items

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
            self._freezing_tab_controller.refresh_texts()
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

        def _bind_keyboard_scroll(self, fields, scroll):
            if scroll is None:
                return
            for field in fields:
                if field is None:
                    continue
                field.bind(
                    focus=lambda widget, focused, _scroll=scroll: self._on_input_focus(
                        widget, focused, _scroll
                    )
                )

        def _on_input_focus(self, field, focused, scroll):
            if not focused or scroll is None:
                return
            Clock.schedule_once(lambda *_: self._scroll_input_into_view(field, scroll), 0.08)
            Clock.schedule_once(lambda *_: self._scroll_input_into_view(field, scroll), 0.35)

        def _scroll_input_into_view(self, field, scroll):
            try:
                scroll.scroll_to(field, padding=dp(150), animate=True)
            except TypeError:
                try:
                    scroll.scroll_to(field)
                except Exception:
                    log.debug("Could not scroll focused field above keyboard.", exc_info=True)
            except Exception:
                log.debug("Could not scroll focused field above keyboard.", exc_info=True)

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
            self._freezing_tab_controller.apply_layout(m)
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
            self._freezing_tab_controller.refresh_texts()
            if hasattr(self, "ad_label"):
                self.ad_label.text = self._ad_label_text()
            if hasattr(self, "bottom_freezing_tab"):
                self.bottom_freezing_tab.set_text(self._t("nav_freezing"))
            if hasattr(self, "bottom_valves_tab"):
                self.bottom_valves_tab.set_text(self._t("nav_valves"))
            if hasattr(self, "bottom_labor_tab"):
                self.bottom_labor_tab.set_text(self._t("nav_labor"))
            self._labor_tab_controller.refresh_texts()
            self._valves_tab_controller.refresh_texts()
            self._monetization.refresh_label()
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
            self._freezing_tab_controller.apply_theme()
            self._labor_tab_controller.apply_theme()
            self._valves_tab_controller.apply_theme()
            ad_slot = getattr(self, "ad_slot", None)
            if ad_slot is not None:
                ad_slot.md_bg_color = self._ad_slot_bg()
            footer_bar = getattr(self, "footer_bar", None)
            if footer_bar is not None:
                footer_bar.md_bg_color = self._footer_bg()
            for button, variant in (
                (getattr(self, "btn_pro", None), "pro"),
            ):
                if button is not None:
                    self._style_app_button(button, variant)

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
                text=self._monetization.button_text(),
                size_hint_x=None,
                width=dp(128),
                size_hint_y=None,
                height=dp(30),
                font_size="11sp",
                pos_hint={"center_y": 0.5},
                on_release=lambda *_: self._monetization.buy(),
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

        def _ensure_freezing_product_access(
            self,
            category: str,
            product_name: str,
        ) -> bool:
            """Consume a reward token when the selected product is locked."""

            if self._entitlements.is_unlocked(self._pro_no_ads):
                return True
            products = list_products(catalog, category)
            try:
                index = products.index(product_name)
            except ValueError:
                index = FREE_PRODUCTS_PER_CATEGORY
            if self._entitlements.is_product_allowed(
                index,
                self._pro_no_ads,
            ):
                return True
            self._credit_pending_reward_tokens()
            if self._entitlements.try_unlock_product_with_token(
                index,
                self._pro_no_ads,
            ):
                return True
            self._offer_reward_ad()
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
            self._refresh_module_valves_status()
            locked = not self._entitlements.has_module(MODULE_VALVES, self._pro_no_ads)
            self._valves_tab_controller.refresh_lock_ui(locked)

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

        def _on_tab_switch(self, *args):
            """Zgodność z dawnym callbackiem dolnej nawigacji."""
            return self._navigation_controller.handle_legacy_switch(*args)

        def _show_tab(self, name: str, *, animate: bool = True, report: bool = True):
            """Przelacza widoczna karte bez ruszania wysokosci dolnego paska."""
            return self._navigation_controller.show(
                name,
                animate=animate,
                report=report,
            )

        def _report_tab(self, name: str):
            self._set_active_ad_tab(name)
            telemetry.set_screen(name)

        def _set_active_ad_tab(self, tab: str):
            if not IS_ANDROID:
                return
            try:
                self._android_activity().setActiveAdTab(tab)
            except Exception:  # pragma: no cover - Android only
                log.debug("setActiveAdTab nie powiodło się", exc_info=True)

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

        def _apply_pro_ui_state(self, active: bool, button_text: str):
            from kivy.metrics import dp

            self._pro_no_ads = active
            ad_height = self._layout_metrics(dp)["ad_h"]
            if hasattr(self, "btn_pro"):
                self.btn_pro.disabled = active
                self.btn_pro.text = button_text
            if hasattr(self, "ad_label"):
                self.ad_label.text = self._ad_label_text()
            if hasattr(self, "ad_slot"):
                self.ad_slot.height = 0 if active else ad_height
                self.ad_slot.opacity = 0 if active else 1
                self.ad_slot.disabled = active
            if hasattr(self, "footer_label"):
                self.footer_label.text = self._status_footer_text()
            self._freezing_tab_controller.set_custom_product_available(active)
            self._refresh_valve_lock_ui()

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
            self._settings_dialog_controller.close()

        def _open_settings_dialog(self):
            self._freezing_tab_controller.close_product_dialog()
            if self._settings_dialog_controller.open():
                telemetry.log_event("settings_opened", {"section": "general"})

        def _open_legal_dialog(self):
            self._close_settings_dialog()
            if self._legal_dialog_controller.open():
                telemetry.log_event("settings_opened", {"section": "legal"})

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

        def _toggle_theme(self):
            self._freezing_tab_controller.close_product_dialog()
            is_dark = self.theme_cls.theme_style == "Dark"
            self.theme_cls.theme_style = "Light" if is_dark else "Dark"
            self._sync_theme_surfaces()
            Clock.schedule_once(lambda *_: self._sync_theme_surfaces(), 0)
            if hasattr(self, "btn_theme"):
                self.btn_theme.icon = "weather-night" if self.theme_cls.theme_style == "Dark" else "weather-sunny"

        def _build_pdf_bytes(self) -> bytes | None:
            """Buduje PDF bez ujawniania źródłowych właściwości produktu."""
            results = self._freezing_tab_controller.last_results
            if results is None:
                return None
            runtime_font = _runtime_font_path()
            if runtime_font is not None:
                try:
                    from tpof.core.pdf_report import build_pdf

                    img_path = _safe_image_path(results.produkt.nazwa)
                    return build_pdf(
                        results,
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
            return build_pdf_simple(results, font_path=runtime_font)

        def _export_pdf(self):
            results = self._freezing_tab_controller.last_results
            if results is None:
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
                nazwa = results.produkt.nazwa.replace(" ", "_")
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

    ShockerCalcApp().run()


if __name__ == "__main__":
    main()

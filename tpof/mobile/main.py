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
from tpof.mobile import telemetry
from tpof.mobile.android_bridge import _purge_host_arch_fonttools_so, _runtime_font_path
from tpof.mobile.catalog import _safe_image_path
from tpof.mobile.constants import (
    APP_NAME,
    IS_ANDROID,
    STAGE_COLORS,
    SURFACE_DARK,
)
from tpof.mobile.dialogs.custom_product import CustomProductDialogController
from tpof.mobile.dialogs.labor_rates import LaborRatesDialogController
from tpof.mobile.dialogs.legal import LegalDialogController
from tpof.mobile.dialogs.privacy import PrivacyDialogController
from tpof.mobile.dialogs.settings import SettingsDialogController
from tpof.mobile.entitlements import (
    FREE_PRODUCTS_PER_CATEGORY,
    MODULE_VALVES,
    Entitlements,
)
from tpof.mobile.form_interactions import FormInteractionController, FormInteractionView
from tpof.mobile.layout import (
    ResponsiveLayoutController,
    ResponsiveLayoutView,
    clamp,
)
from tpof.mobile.localization import LocalizationController, LocalizationView
from tpof.mobile.navigation import TabNavigationController
from tpof.mobile.paths import DATA_PATH, PROJECT_ROOT
from tpof.mobile.pdf_export import _pdf_output_dir
from tpof.mobile.services.entitlements_ui import _sync_module_ownership
from tpof.mobile.services.monetization import ProMonetizationController
from tpof.mobile.settings_state import SettingsStateController
from tpof.mobile.shell import (
    MobileShellBuilder,
    MobileShellCallbacks,
    MobileShellFactories,
)
from tpof.mobile.tabs.freezing import FreezingTabController
from tpof.mobile.tabs.labor import LaborTabController
from tpof.mobile.tabs.valves import ValvesTabController
from tpof.mobile.theme import ThemeSyncController, ThemeSyncView
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
            self._preferences = UiPreferences()
            self._native_ad_height_dp = 0
            self._pro_no_ads = False
            self._entitlements = Entitlements()
            self._entitlements.ensure_started()
            self._localization = LocalizationController(
                initial_language="pl",
                is_android=IS_ANDROID,
                is_dark=lambda: self.theme_cls.theme_style == "Dark",
                is_pro_no_ads=lambda: self._pro_no_ads,
                is_trial_active=self._entitlements.is_trial_active,
                trial_days_left=self._entitlements.trial_days_left,
                close_product_dialog=lambda: (
                    self._freezing_tab_controller.close_product_dialog()
                ),
                refresh_settings_ui=lambda: self._settings_state.refresh_ui(),
                refresh_callbacks=(
                    lambda: self._freezing_tab_controller.refresh_texts(),
                    lambda: self._labor_tab_controller.refresh_texts(),
                    lambda: self._valves_tab_controller.refresh_texts(),
                    lambda: self._monetization.refresh_label(),
                    lambda: self._form_interactions.apply(),
                ),
            )
            self._t = self._localization.translate
            self._form_interactions = FormInteractionController(
                hints_enabled=self._preferences.hints_enabled,
                set_hints_enabled=self._preferences.set_hints_enabled,
                translate=self._t,
                get_hint_field_items=lambda: (
                    *self._freezing_tab_controller.hint_field_items(),
                    *self._valves_tab_controller.hint_field_items(),
                    *self._labor_tab_controller.hint_field_items(),
                ),
                refresh_freezing_texts=lambda: (
                    self._freezing_tab_controller.refresh_texts()
                ),
                apply_responsive_layout=lambda: self._responsive_controller.apply(),
                show_message=self._show_error,
                log_event=telemetry.log_event,
                schedule_once=Clock.schedule_once,
                dp=dp,
            )
            self._theme_controller = ThemeSyncController(
                is_dark=lambda: self.theme_cls.theme_style == "Dark",
                set_dark=lambda dark: setattr(
                    self.theme_cls,
                    "theme_style",
                    "Dark" if dark else "Light",
                ),
                get_active_tab=lambda: getattr(
                    self,
                    "_active_tab_name",
                    "freezing",
                ),
                get_themed_cards=lambda: self._themed_cards,
                apply_tab_themes=(
                    lambda: self._freezing_tab_controller.apply_theme(),
                    lambda: self._labor_tab_controller.apply_theme(),
                    lambda: self._valves_tab_controller.apply_theme(),
                ),
                close_product_dialog=lambda: (
                    self._freezing_tab_controller.close_product_dialog()
                ),
                schedule_once=Clock.schedule_once,
            )
            self._responsive_controller = ResponsiveLayoutController(
                dp=dp,
                get_screen_size=lambda: (Window.width, Window.height),
                hints_enabled=lambda: self._form_interactions.hints_enabled,
                native_ad_height_dp=lambda: self._native_ad_height_dp,
                pro_no_ads=lambda: self._pro_no_ads,
                bottom_nav_bg=self._theme_controller.bottom_nav_bg,
                refresh_privacy_button=self._refresh_privacy_button,
                apply_freezing_layout=lambda metrics: (
                    self._freezing_tab_controller.apply_layout(metrics)
                ),
            )
            self._legal_dialog_controller = LegalDialogController(
                translate=self._t,
                project_root=PROJECT_ROOT,
            )
            self._privacy_dialog_controller = PrivacyDialogController(
                translate=self._t,
                is_android=IS_ANDROID,
                telemetry_available=telemetry.is_available,
                telemetry_has_preference=telemetry.has_preference,
                telemetry_enabled=telemetry.is_enabled,
                set_telemetry_enabled=telemetry.set_enabled,
                privacy_options_required=lambda: bool(
                    self._android_activity().isPrivacyOptionsRequired()
                ),
                show_privacy_options_form=lambda: (
                    self._android_activity().showPrivacyOptionsForm()
                ),
                refresh_button=self._refresh_privacy_button,
                log_event=telemetry.log_event,
                record_exception=telemetry.record_exception,
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
                clear_field_error=self._form_interactions.clear_field_error,
                mark_field_error=self._form_interactions.mark_field_error,
                show_message=self._show_error,
                log_event=telemetry.log_event,
                record_exception=telemetry.record_exception,
            )
            self._settings_dialog_controller = SettingsDialogController(
                translate=self._t,
                style_button=self._theme_controller.style_button,
                card_bg=self._theme_controller.card_bg,
                get_display_currency=lambda: self._settings_state.display_currency,
                get_exchange_rates=lambda: self._settings_state.exchange_rates,
                get_language=lambda: self._localization.language,
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
                clear_field_error=self._form_interactions.clear_field_error,
                mark_field_error=self._form_interactions.mark_field_error,
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
                get_language=lambda: self._localization.language,
                get_display_currency=lambda: self._settings_state.display_currency,
                get_exchange_rates=lambda: self._settings_state.exchange_rates,
                get_rate_values=lambda: self._preferences.labor_rate_values,
                reset_rate_values=self._preferences.reset_labor_rate_values,
                is_pro=lambda: self._pro_no_ads,
                open_rates_dialog=lambda: self._labor_rates_dialog_controller.open(),
                card_bg=self._theme_controller.card_bg,
                total_color=STAGE_COLORS["total"],
                chart_factory=LaborPieChart,
                numeric_input_filter=_numeric_input_filter,
                register_themed_card=self._themed_cards.append,
                bind_keyboard_scroll=self._form_interactions.bind_keyboard_scroll,
                style_button=self._theme_controller.style_button,
                clear_field_error=self._form_interactions.clear_field_error,
                mark_field_error=self._form_interactions.mark_field_error,
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
                card_bg=self._theme_controller.card_bg,
                total_color=STAGE_COLORS["total"],
                numeric_input_filter=_numeric_input_filter,
                register_themed_card=self._themed_cards.append,
                bind_keyboard_scroll=self._form_interactions.bind_keyboard_scroll,
                style_button=self._theme_controller.style_button,
                clear_field_error=self._form_interactions.clear_field_error,
                mark_field_error=self._form_interactions.mark_field_error,
                show_message=self._show_error,
                log_event=telemetry.log_event,
                record_exception=telemetry.record_exception,
                can_calculate=self._valve_module_available,
                on_access_denied=self._refresh_valve_lock_ui,
                on_buy=self._buy_valve_module,
                on_watch=self._offer_reward_ad,
                menu_factory=self._menu,
                is_compact=lambda: bool(
                    self._responsive_controller.metrics()["compact"]
                ),
                menu_text_color=self._theme_controller.menu_text_color,
            )
            self._freezing_tab_controller = FreezingTabController(
                catalog=catalog,
                categories=categories,
                translate=self._t,
                display_category=self._localization.display_category,
                card_bg=self._theme_controller.card_bg,
                total_color=STAGE_COLORS["total"],
                numeric_input_filter=_numeric_input_filter,
                register_themed_card=self._themed_cards.append,
                bind_keyboard_scroll=self._form_interactions.bind_keyboard_scroll,
                style_button=self._theme_controller.style_button,
                clear_field_error=self._form_interactions.clear_field_error,
                mark_field_error=self._form_interactions.mark_field_error,
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
                    self._responsive_controller.metrics()["compact"]
                ),
                menu_text_color=self._theme_controller.menu_text_color,
                divider_color=lambda: self.theme_cls.divider_color,
                hints_enabled=lambda: self._form_interactions.hints_enabled,
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
            self._shell_builder = MobileShellBuilder(
                dp=dp,
                factories=MobileShellFactories(
                    box_layout=MDBoxLayout,
                    icon=MDIcon,
                    icon_button=MDIconButton,
                    label=MDLabel,
                    raised_button=MDRaisedButton,
                    brand_toolbar=BrandToolbar,
                    frost_chip=FrostChip,
                    bottom_nav_tab=BottomNavTab,
                    center_notice=CenterNotice,
                ),
                callbacks=MobileShellCallbacks(
                    translate=self._t,
                    hints_enabled=lambda: self._form_interactions.hints_enabled,
                    on_toggle_hints=self._form_interactions.toggle,
                    on_toggle_language=self._localization.toggle,
                    on_toggle_theme=self._theme_controller.toggle,
                    on_open_privacy=self._privacy_dialog_controller.open,
                    on_open_settings=self._open_settings_dialog,
                    on_select_tab=self._show_tab,
                    bottom_nav_bg=self._theme_controller.bottom_nav_bg,
                    footer_bg=self._theme_controller.footer_bg,
                    ad_slot_bg=self._theme_controller.ad_slot_bg,
                    footer_text=self._localization.footer_text,
                    pro_button_text=self._monetization.button_text,
                    on_buy_pro=self._monetization.buy,
                    ad_label_text=self._localization.ad_label_text,
                ),
            )
            self._shell_view = self._shell_builder.build()
            self._shell_view.install_on(self)
            self._localization.attach(LocalizationView.from_shell(self))
            self._form_interactions.attach(FormInteractionView.from_shell(self))
            self._refresh_privacy_button()

            self.root_host = FloatLayout()
            with self.root_host.canvas.before:
                self._root_bg_color = Color(*SURFACE_DARK)
                self._root_bg_rect = Rectangle(pos=(0, 0), size=Window.size)
            self.root_host.bind(
                pos=self._responsive_controller.sync_root_background,
                size=self._responsive_controller.sync_root_background,
            )
            self.frost_background = FrostBackground()
            self.root_layout = MDBoxLayout(
                orientation="vertical",
                md_bg_color=(0, 0, 0, 0),
                size_hint=(1, 1),
            )
            self.root_host.add_widget(self.frost_background)
            self.root_host.add_widget(self.root_layout)
            root = self.root_layout

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
                refresh_theme=self._theme_controller.apply,
                schedule_once=Clock.schedule_once,
                logger=log,
            )
            self._show_tab("freezing", animate=False, report=False)

            root.add_widget(self.footer_bar)
            root.add_widget(self.ad_slot)
            self.root_host.add_widget(self.center_notice)
            self._responsive_controller.attach(
                ResponsiveLayoutView.from_shell(self)
            )
            self._responsive_controller.sync_root_background()
            self._theme_controller.attach(
                ThemeSyncView.from_shell(
                    self,
                    set_window_clearcolor=lambda color: setattr(
                        Window,
                        "clearcolor",
                        color,
                    ),
                )
            )
            self._theme_controller.apply()
            Window.bind(size=self._responsive_controller.apply)
            self._responsive_controller.apply()
            self._monetization.start()
            Clock.schedule_once(lambda *_: self._refresh_ad_slot_height(), 1.2)
            Clock.schedule_once(lambda *_: self._refresh_ad_slot_height(), 3.5)
            Clock.schedule_once(lambda *_: self._refresh_ad_slot_height(), 7.0)
            Clock.schedule_once(lambda *_: self._refresh_privacy_button(), 3.0)
            Clock.schedule_once(lambda *_: self._refresh_privacy_button(), 8.0)
            Clock.schedule_once(lambda *_: self._refresh_valve_lock_ui(), 1.0)
            Clock.schedule_once(lambda *_: self._refresh_valve_lock_ui(), 4.0)
            Clock.schedule_once(lambda *_: self._form_interactions.apply(), 0.2)
            Clock.schedule_once(
                lambda *_: self._privacy_dialog_controller.prompt_telemetry_consent(),
                2.0,
            )
            Clock.schedule_once(
                lambda *_: self._settings_state.refresh_exchange_rates_async(),
                1.0,
            )
            telemetry.log_event(
                "app_started",
                {"language": self._localization.language},
            )
            return self.root_host

        def _menu(self, caller, items, width_mult, max_height, dp, MDDropdownMenu):
            width_dp, height_dp = self._responsive_controller.screen_dp()
            desired_width = min(width_mult * 56.0, max(180.0, width_dp - 32.0))
            width_mult = clamp(desired_width / 56.0, 2.8, 5.0)
            max_height = min(max_height, dp(max(220.0, height_dp * 0.58)))
            menu = MDDropdownMenu(
                caller=caller,
                items=items,
                width_mult=width_mult,
                max_height=max_height,
            )
            for attr, value in [
                ("background_color", self._theme_controller.menu_bg_color()),
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
            self._responsive_controller.apply()

        def _apply_pro_ui_state(self, active: bool, button_text: str):
            self._pro_no_ads = active
            ad_height = self._responsive_controller.metrics()["ad_h"]
            if hasattr(self, "btn_pro"):
                self.btn_pro.disabled = active
                self.btn_pro.text = button_text
            if hasattr(self, "ad_label"):
                self.ad_label.text = self._localization.ad_label_text()
            if hasattr(self, "ad_slot"):
                self.ad_slot.height = 0 if active else ad_height
                self.ad_slot.opacity = 0 if active else 1
                self.ad_slot.disabled = active
            if hasattr(self, "footer_label"):
                self.footer_label.text = self._localization.footer_text()
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
            visible = self._privacy_dialog_controller.options_available()
            btn.disabled = not visible
            btn.opacity = 1 if visible else 0
            chip = getattr(self, "btn_privacy_chip", None)
            from kivy.metrics import dp

            try:
                target_width = self._responsive_controller.metrics()["toolbar_btn_w"]
            except Exception:
                target_width = dp(48)
            btn.width = target_width if visible else 0
            if chip is not None:
                chip.disabled = not visible
                chip.opacity = 1 if visible else 0
                chip.width = target_width if visible else 0
                chip.height = target_width

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

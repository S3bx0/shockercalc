"""Składanie stanu i kontrolerów aplikacji mobilnej.

Moduł celowo nie importuje Kivy, KivyMD ani PyJNIus. Runtime UI jest
przekazywany przez ``ShockerCalcApp`` jako mały zestaw zależności.
"""
from __future__ import annotations

from tpof.core import list_products
from tpof.mobile import telemetry
from tpof.mobile.android_bridge import AndroidActivityBridge
from tpof.mobile.catalog import _safe_image_path
from tpof.mobile.constants import IS_ANDROID, STAGE_COLORS
from tpof.mobile.dialogs.custom_product import CustomProductDialogController
from tpof.mobile.dialogs.labor_rates import LaborRatesDialogController
from tpof.mobile.dialogs.legal import LegalDialogController
from tpof.mobile.dialogs.privacy import (
    PrivacyDialogController,
    PrivacyToolbarController,
)
from tpof.mobile.dialogs.settings import SettingsDialogController
from tpof.mobile.entitlements import FREE_PRODUCTS_PER_CATEGORY, Entitlements
from tpof.mobile.form_interactions import FormInteractionController
from tpof.mobile.layout import ResponsiveLayoutController
from tpof.mobile.localization import LocalizationController
from tpof.mobile.paths import PROJECT_ROOT
from tpof.mobile.pdf_export import PdfExportController
from tpof.mobile.services.monetization import ProMonetizationController
from tpof.mobile.services.rewarded_access import RewardedAccessController
from tpof.mobile.settings_state import SettingsStateController
from tpof.mobile.tabs.freezing import FreezingTabController
from tpof.mobile.tabs.labor import LaborTabController
from tpof.mobile.tabs.valves import ValvesTabController
from tpof.mobile.theme import ThemeSyncController
from tpof.mobile.user_data import UiPreferences
from tpof.mobile.validation import _numeric_input_filter


class AppControllerCompositionMixin:
    """Instaluje stan i kontrolery na instancji ``ShockerCalcApp``."""

    def compose_controllers(
        self,
        *,
        catalog,
        custom_products,
        categories,
        clock,
        dp,
        window,
        chart_factory,
    ):
        self._themed_cards = []
        self._preferences = UiPreferences()
        self._native_ad_height_dp = 0
        self._pro_no_ads = False
        self._entitlements = Entitlements()
        self._entitlements.ensure_started()
        self._android = AndroidActivityBridge(is_android=IS_ANDROID)
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
            schedule_once=clock.schedule_once,
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
            schedule_once=clock.schedule_once,
        )
        self._responsive_controller = ResponsiveLayoutController(
            dp=dp,
            get_screen_size=lambda: (window.width, window.height),
            hints_enabled=lambda: self._form_interactions.hints_enabled,
            native_ad_height_dp=lambda: self._native_ad_height_dp,
            pro_no_ads=lambda: self._pro_no_ads,
            bottom_nav_bg=self._theme_controller.bottom_nav_bg,
            refresh_privacy_button=lambda: (
                self._privacy_toolbar_controller.refresh()
            ),
            apply_freezing_layout=lambda metrics: (
                self._freezing_tab_controller.apply_layout(metrics)
            ),
        )
        self._privacy_toolbar_controller = PrivacyToolbarController(
            options_available=lambda: (
                self._privacy_dialog_controller.options_available()
            ),
            get_button=lambda: getattr(self, "btn_privacy", None),
            get_chip=lambda: getattr(self, "btn_privacy_chip", None),
            get_target_width=lambda: self._responsive_controller.metrics()[
                "toolbar_btn_w"
            ],
            get_fallback_width=lambda: dp(48),
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
            privacy_options_required=self._android.privacy_options_required,
            show_privacy_options_form=self._android.show_privacy_options_form,
            refresh_button=self._privacy_toolbar_controller.refresh,
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
            schedule_once=clock.schedule_once,
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
            invalidate_results=lambda: (
                self._labor_tab_controller.invalidate_results()
            ),
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
            chart_factory=chart_factory,
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
        self._rewarded_access = RewardedAccessController(
            is_android=IS_ANDROID,
            entitlements=self._entitlements,
            translate=self._t,
            get_pro_no_ads=lambda: self._pro_no_ads,
            get_products=lambda category: list_products(catalog, category),
            get_android_activity=self._android.activity,
            schedule_once=clock.schedule_once,
            refresh_valve_lock_view=lambda locked: (
                self._valves_tab_controller.refresh_lock_ui(locked)
            ),
            show_message=self._show_error,
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
            can_calculate=self._rewarded_access.valve_module_available,
            on_access_denied=self._rewarded_access.refresh_valve_lock_ui,
            on_buy=self._rewarded_access.buy_valve_module,
            on_watch=self._rewarded_access.offer_reward_ad,
            menu_factory=self._menu,
            is_compact=lambda: bool(
                self._responsive_controller.metrics()["compact"]
            ),
            menu_text_color=self._theme_controller.menu_text_color,
        )
        self._pdf_export = PdfExportController(
            get_results=lambda: self._freezing_tab_controller.last_results,
            translate=self._t,
            show_message=self._show_error,
            share_file=self._android.share_file,
            log_event=telemetry.log_event,
            record_exception=telemetry.record_exception,
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
            ensure_product_access=self._rewarded_access.ensure_product_access,
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
            on_export_pdf=self._pdf_export.export,
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
            get_android_activity=self._android.activity,
            schedule_once=clock.schedule_once,
            on_state_changed=self._apply_pro_ui_state,
            refresh_ad_slot_height=self._refresh_ad_slot_height,
            show_message=self._show_error,
            log_event=telemetry.log_event,
            record_exception=telemetry.record_exception,
        )

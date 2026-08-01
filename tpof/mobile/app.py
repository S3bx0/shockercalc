"""Composition root aplikacji mobilnej Refrigeration Calc (KivyMD).

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

from tpof.core import (
    Product,
    list_categories,
    load_products,
)
from tpof.mobile import telemetry
from tpof.mobile.android_bridge import (
    _runtime_font_path,
)
from tpof.mobile.app_controllers import AppControllerCompositionMixin
from tpof.mobile.constants import (
    APP_NAME,
    SURFACE_DARK,
)
from tpof.mobile.form_interactions import FormInteractionView
from tpof.mobile.layout import (
    ResponsiveLayoutView,
    clamp,
)
from tpof.mobile.localization import LocalizationView
from tpof.mobile.navigation import TabNavigationController
from tpof.mobile.paths import DATA_PATH
from tpof.mobile.shell import (
    MobileShellBuilder,
    MobileShellCallbacks,
    MobileShellFactories,
)
from tpof.mobile.theme import ThemeSyncView
from tpof.mobile.user_data import CustomProductStore

log = logging.getLogger(__name__)

def _create_app_class():
    """Zbuduj klasę aplikacji po załadowaniu opcjonalnego runtime KivyMD."""
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



    class ShockerCalcApp(AppControllerCompositionMixin, MDApp):
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

            self.compose_controllers(
                catalog=catalog,
                custom_products=custom_products,
                categories=categories,
                clock=Clock,
                dp=dp,
                window=Window,
                chart_factory=LaborPieChart,
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
            self._privacy_toolbar_controller.refresh()

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
                    self._rewarded_access.refresh_valve_lock_ui()
                    if name == "valves"
                    else None
                ),
                refresh_theme=self._theme_controller.apply,
                schedule_once=Clock.schedule_once,
                logger=log,
            )
            self._show_tab("freezing", animate=False, report=False)
            Clock.schedule_once(
                lambda *_: self._app_shortcuts.consume_pending(),
                0,
            )

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
            Clock.schedule_once(self._privacy_toolbar_controller.refresh, 3.0)
            Clock.schedule_once(self._privacy_toolbar_controller.refresh, 8.0)
            Clock.schedule_once(
                lambda *_: self._rewarded_access.refresh_valve_lock_ui(),
                1.0,
            )
            Clock.schedule_once(
                lambda *_: self._rewarded_access.refresh_valve_lock_ui(),
                4.0,
            )
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

        def _on_tab_switch(self, *args):
            """Zgodność z dawnym callbackiem dolnej nawigacji."""
            return self._navigation_controller.handle_legacy_switch(*args)

        def on_resume(self):
            """Consume a shortcut delivered while the Android task was paused."""

            shortcuts = getattr(self, "_app_shortcuts", None)
            if shortcuts is not None:
                shortcuts.consume_pending()

        def _show_tab(self, name: str, *, animate: bool = True, report: bool = True):
            """Przelacza widoczna karte bez ruszania wysokosci dolnego paska."""
            return self._navigation_controller.show(
                name,
                animate=animate,
                report=report,
            )

        def _report_tab(self, name: str):
            self._android.set_active_ad_tab(name)
            telemetry.set_screen(name)

        def _refresh_ad_slot_height(self):
            height_dp = self._android.resolved_banner_height(
                self._pro_no_ads, self._native_ad_height_dp
            )
            if height_dp == self._native_ad_height_dp:
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
            self._rewarded_access.refresh_valve_lock_ui()

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

    return ShockerCalcApp


ShockerCalcApp = _create_app_class()

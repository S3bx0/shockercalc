"""Refrigeration Calc — wersja mobilna (KivyMD).

UI w parytecie z desktopem:
  • TopAppBar z przełącznikiem Dark/Light
  • kaskadowy wybór Kategoria → Produkt
  • masa z przełącznikiem jednostek kg/t
  • paski mocy (schładzanie / zamrożenie / domrażanie) + SUMA
  • tabela właściwości produktu
  • opcjonalne zdjęcie produktu z assets/images
  • Snackbar dla błędów walidacji

Uruchomienie lokalne (desktop, do testów UI):
    python -m pip install -r requirements-mobile.txt
    python -m tpof.mobile

Build APK:
    buildozer android debug
"""
from __future__ import annotations

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

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
from tpof.mobile.entitlements import FREE_PRODUCTS_PER_CATEGORY, TRIAL_DAYS, Entitlements
from tpof.mobile.paths import DATA_PATH, FONT_PATH, IMAGES_DIR, WATERMARK_PATH

log = logging.getLogger(__name__)

STAGE_COLORS = {
    "schladzanie": (0.10, 0.48, 0.71, 1),
    "zamrozenie": (0.42, 0.37, 0.86, 1),
    "domrozenie": (0.00, 0.67, 0.74, 1),
    "total": (0.05, 0.62, 0.42, 1),
}

APP_NAME = "Refrigeration Calc"
ADMOB_APP_ID = "ca-app-pub-7481054652344026~2716191071"
ADMOB_BANNER_AD_UNIT_ID = "ca-app-pub-7481054652344026/5599859341"
ADMOB_TEST_BANNER_AD_UNIT_ID = "ca-app-pub-3940256099942544/9214589741"
PRO_PRODUCT_ID = "pro_no_ads"

IS_ANDROID = "ANDROID_ARGUMENT" in os.environ
CARD_BG_DARK = (0.09, 0.13, 0.17, 1)
CARD_BG_LIGHT = (0.96, 0.98, 1.0, 1)
SURFACE_DARK = (0.05, 0.08, 0.11, 1)
SURFACE_LIGHT = (0.93, 0.96, 0.98, 1)

_FONTTOOLS_SO_PURGED = False


def _purge_host_arch_fonttools_so() -> None:
    """Usuwa host-arch (.so) rozszerzenia fonttools z rozpakowanego bundla.

    Na Androidzie p4a instaluje fonttools hostowym pipem, więc skompilowane
    rozszerzenia Cython (np. ``fontTools/misc/bezierTools.so``) są dla x86_64,
    a nie arm64 -> ``dlopen`` pada przy generowaniu PDF. Katalog
    ``_python_bundle`` jest rozpakowany do zapisywalnego ``files/app/...``,
    więc kasujemy te ``.so`` w runtime — fonttools wraca do czystego Pythona.
    """
    global _FONTTOOLS_SO_PURGED
    if _FONTTOOLS_SO_PURGED or not IS_ANDROID:
        return
    _FONTTOOLS_SO_PURGED = True

    import sys

    roots: List[str] = []
    try:
        import fontTools  # noqa: WPS433 - pakiet __init__ jest czysto-pythonowy

        roots.extend(getattr(fontTools, "__path__", []) or [])
    except Exception:  # pragma: no cover - Android only
        pass
    for entry in sys.path:
        candidate = os.path.join(entry, "fontTools")
        if os.path.isdir(candidate):
            roots.append(candidate)

    seen = set()
    for root in roots:
        root = os.path.abspath(root)
        if root in seen or not os.path.isdir(root):
            continue
        seen.add(root)
        for dirpath, _dirnames, filenames in os.walk(root):
            for name in filenames:
                if name.endswith(".so"):
                    try:
                        os.remove(os.path.join(dirpath, name))
                        log.warning("Usunieto host-arch fonttools .so: %s", name)
                    except OSError as exc:  # pragma: no cover - Android only
                        log.warning("Nie usunieto %s: %s", name, exc)


I18N = {
    "pl": {
        "product": "Produkt",
        "choose_category": "Wybierz kategorię",
        "choose_product": "Wybierz produkt",
        "image_placeholder": "Zdjęcie produktu pojawi się po wyborze",
        "params": "Parametry",
        "mass": "Masa",
        "temperature_start": "Temperatura początkowa [°C]",
        "temperature_end": "Temperatura końcowa [°C]",
        "work_time": "Czas pracy [h]",
        "calculate": "Oblicz",
        "clear": "Wyczyść",
        "result": "Wynik",
        "total_power": "Suma mocy: {value} kW",
        "cooling": "Schładzanie",
        "freezing": "Zamrożenie",
        "deep_freezing": "Domrażanie",
        "product_properties": "Właściwości produktu",
        "category": "Kategoria:",
        "water": "Woda [%]:",
        "ad": "Reklama",
        "ad_placeholder": "Miejsce na baner AdMob",
        "pro_active": "PRO",
        "pro_ads_off": "PRO: reklamy wyłączone",
        "pro_google_play_only": "Zakup PRO działa tylko w wersji z Google Play.",
        "pro_unavailable": "Zakup PRO jest chwilowo niedostępny.",
        "pick_product_error": "Wybierz kategorię i produkt.",
        "missing_product_error": "Nie znaleziono produktu w bazie.",
        "pdf_first": "Najpierw wykonaj obliczenia.",
        "pdf_unavailable": "Eksport PDF niedostępny w wersji mobilnej. Użyj wersji desktopowej.",
        "saved": "Zapisano: {path}",
        "pdf_error": "Błąd PDF: {error}",
        "pdf_share_subject": "Refrigeration Calc — wyniki obliczeń",
        "pdf_share_text": "W załączniku raport PDF z obliczeń mocy chłodniczej.",
        "calc_error": "Błąd: {error}",
        "invalid_field": "Nieprawidłowa wartość pola: {name}",
        "field_mass": "masa",
        "field_temp_start": "temperatura początkowa",
        "field_temp_end": "temperatura końcowa",
        "field_time": "czas",
        "estimated": "  (szacowane)",
        "trial_active": "Wersja próbna: pozostało {days} dni",
        "trial_last_day": "Wersja próbna: ostatni dzień",
        "trial_expired": "Wersja darmowa • 1 produkt z listy",
        "pro_unlocked_footer": "PRO • pełen dostęp",
        "locked_suffix": "  — PRO",
        "product_locked": "Ten produkt jest dostępny w PRO. W wersji darmowej masz 1 produkt z każdej listy.",
        "trial_expired_info": "Okres próbny dobiegł końca. Kup PRO, aby odblokować wszystkie produkty.",
        "watch_ad_for_token": "Obejrzyj reklamę, aby wykonać 1 bezpłatne przeliczenie tego produktu.",
        "ad_token_earned": "Masz token! Naciśnij Oblicz, aby wykonać bezpłatne przeliczenie.",
        "ad_thanks": "Dziękujemy za obejrzenie reklamy! Masz 1 bezpłatne przeliczenie.",
        "pro_thanks": "Dziękujemy za zakup PRO! Reklamy wyłączone, pełen dostęp odblokowany.",
        "ad_not_ready": "Reklama jeszcze się ładuje. Spróbuj za chwilę.",
        "ad_limit_reached": "Dzienny limit reklam wyczerpany. Kup PRO, aby liczyć bez ograniczeń.",
        "nav_freezing": "Chłodnicze",
        "nav_valves": "Zawory",
        "valve_title": "Zawory dekompresyjne",
        "valve_type": "Typ zaworu",
        "valve_volume": "Objętość komory [m³]",
        "valve_temp_before": "Temp. przed dekompresją [°C]",
        "valve_temp_after": "Temp. po dekompresji [°C]",
        "valve_factor": "Współczynnik częstości F [1/h]",
        "valve_calculate": "Oblicz zawory",
        "valve_result": "Wynik",
        "valve_delta_t": "Tempo zmian ΔT: {value} °C/min",
        "valve_flow": "Wymagany przepływ Q: {value} l/min",
        "valve_unit_flow": "Przepływ zaworu: {value} l/min",
        "valve_count": "Liczba zaworów: {value}",
    },
    "en": {
        "product": "Product",
        "choose_category": "Choose category",
        "choose_product": "Choose product",
        "image_placeholder": "Product image appears after selection",
        "params": "Parameters",
        "mass": "Mass",
        "temperature_start": "Initial temperature [°C]",
        "temperature_end": "Final temperature [°C]",
        "work_time": "Run time [h]",
        "calculate": "Calculate",
        "clear": "Clear",
        "result": "Result",
        "total_power": "Total power: {value} kW",
        "cooling": "Cooling",
        "freezing": "Freezing",
        "deep_freezing": "Deep freezing",
        "product_properties": "Product properties",
        "category": "Category:",
        "water": "Water [%]:",
        "ad": "Ad",
        "ad_placeholder": "AdMob banner area",
        "pro_active": "PRO",
        "pro_ads_off": "PRO: ads disabled",
        "pro_google_play_only": "PRO purchase works only in the Google Play build.",
        "pro_unavailable": "PRO purchase is temporarily unavailable.",
        "pick_product_error": "Choose a category and product.",
        "missing_product_error": "Product was not found in the database.",
        "pdf_first": "Calculate first.",
        "pdf_unavailable": "PDF export is unavailable in the mobile build. Use the desktop version.",
        "saved": "Saved: {path}",
        "pdf_error": "PDF error: {error}",
        "pdf_share_subject": "Refrigeration Calc — calculation results",
        "pdf_share_text": "Attached is the PDF report from the cooling power calculation.",
        "calc_error": "Error: {error}",
        "invalid_field": "Invalid value in field: {name}",
        "field_mass": "mass",
        "field_temp_start": "initial temperature",
        "field_temp_end": "final temperature",
        "field_time": "time",
        "estimated": "  (estimated)",
        "trial_active": "Trial: {days} days left",
        "trial_last_day": "Trial: last day",
        "trial_expired": "Free version • 1 product per list",
        "pro_unlocked_footer": "PRO • full access",
        "locked_suffix": "  — PRO",
        "product_locked": "This product is available in PRO. The free version allows 1 product per list.",
        "trial_expired_info": "The trial has ended. Buy PRO to unlock all products.",
        "watch_ad_for_token": "Watch an ad to run 1 free calculation for this product.",
        "ad_token_earned": "Token granted! Tap Calculate to run your free calculation.",
        "ad_thanks": "Thanks for watching the ad! You have 1 free calculation.",
        "pro_thanks": "Thank you for buying PRO! Ads disabled, full access unlocked.",
        "ad_not_ready": "The ad is still loading. Try again in a moment.",
        "ad_limit_reached": "Daily ad limit reached. Buy PRO to calculate without limits.",
        "nav_freezing": "Cooling",
        "nav_valves": "Valves",
        "valve_title": "Decompression valves",
        "valve_type": "Valve type",
        "valve_volume": "Chamber volume [m³]",
        "valve_temp_before": "Temp. before decompression [°C]",
        "valve_temp_after": "Temp. after decompression [°C]",
        "valve_factor": "Frequency factor F [1/h]",
        "valve_calculate": "Calculate valves",
        "valve_result": "Result",
        "valve_delta_t": "Change rate ΔT: {value} °C/min",
        "valve_flow": "Required flow Q: {value} l/min",
        "valve_unit_flow": "Valve flow: {value} l/min",
        "valve_count": "Number of valves: {value}",
    },
}

CATEGORY_LABELS_EN = {
    "warzywa": "vegetables",
    "owoce": "fruit",
    "ryby": "fish",
    "owoce_morza": "seafood",
    "wołowina": "beef",
    "wieprzowina": "pork",
    "kiełbasy": "sausages",
    "drób": "poultry",
    "jajka": "eggs",
    "jagnięcina": "lamb",
    "nabial": "dairy",
    "sery": "cheese",
    "śmietana": "cream",
    "lody": "ice cream",
    "mleko": "milk",
    "orzechy": "nuts",
    "słodycze": "sweets",
    "soki_i_napoje": "juices and drinks",
    "różne": "miscellaneous",
}


def _safe_image_path(nazwa: str) -> Optional[str]:
    """Zwraca ścieżkę do .webp/.png/.jpg dla produktu albo None."""
    for ext in (".webp", ".png", ".jpg", ".jpeg"):
        candidate = IMAGES_DIR / f"{nazwa}{ext}"
        if candidate.exists():
            return str(candidate)
    return None


def _pdf_output_dir() -> Path:
    """Zwraca katalog do zapisu PDF — Android Downloads albo cwd."""
    # Android: użyj public Downloads, gdy aplikacja ma uprawnienia
    if "ANDROID_ARGUMENT" in os.environ:
        for candidate in ("/sdcard/Download", "/storage/emulated/0/Download"):
            p = Path(candidate)
            if p.exists() and os.access(p, os.W_OK):
                return p
        # fallback: prywatny katalog aplikacji
        return Path(os.environ.get("ANDROID_PRIVATE", os.getcwd()))
    return Path.cwd()


def main() -> None:
    """Punkt wejścia mobilnej aplikacji."""
    try:
        from kivy.clock import Clock
        from kivy.core.window import Window
        from kivy.metrics import dp
        from kivy.uix.image import AsyncImage
        from kivymd.app import MDApp
        from kivymd.uix.bottomnavigation import (
            MDBottomNavigation,
            MDBottomNavigationItem,
        )
        from kivymd.uix.boxlayout import MDBoxLayout
        from kivymd.uix.button import MDIconButton, MDRaisedButton
        from kivymd.uix.card import MDCard
        from kivymd.uix.gridlayout import MDGridLayout
        from kivymd.uix.label import MDIcon, MDLabel
        from kivymd.uix.menu import MDDropdownMenu
        from kivymd.uix.progressbar import MDProgressBar
        from kivymd.uix.scrollview import MDScrollView
        from kivymd.uix.textfield import MDTextField
    except ImportError as exc:  # pragma: no cover
        raise SystemExit(
            "KivyMD nie jest zainstalowane. Uruchom:\n"
            "    python -m pip install -r requirements-mobile.txt"
        ) from exc

    # Rejestracja fontu DejaVuSans (pełen Unicode — subscripty, symbole)
    # — działa zarówno na desktopie jak i na Androidzie (font jest w assets/).
    try:
        from kivy.core.text import LabelBase

        if FONT_PATH.exists():
            LabelBase.register(name="DejaVuSans", fn_regular=str(FONT_PATH))
            log.info("Zarejestrowano font DejaVuSans z %s", FONT_PATH)
    except Exception:  # pragma: no cover
        log.exception("Nie udało się zarejestrować fontu DejaVuSans")

    catalog: Dict[str, List[Product]] = load_products(DATA_PATH)
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

            self._selected_category: Optional[str] = None
            self._selected_product: Optional[str] = None
            self._mass_unit: str = "kg"
            self._cat_menu: Optional[MDDropdownMenu] = None
            self._prod_menu: Optional[MDDropdownMenu] = None
            self._last_results = None
            self._themed_cards = []
            self._language = "pl"
            self._native_ad_height_dp = 0
            self._pro_no_ads = False
            self._pro_thanks_shown = False
            self._valve_type = "Maxi Elebar"
            self._last_valve_results = None
            self._valve_menu: Optional[MDDropdownMenu] = None
            self._entitlements = Entitlements()
            self._entitlements.ensure_started()

            self.root_layout = MDBoxLayout(orientation="vertical", md_bg_color=SURFACE_DARK)
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
                dp, MDCard, MDBoxLayout, MDIcon, MDLabel, MDProgressBar, MDGridLayout, MDRaisedButton
            )
            content.add_widget(self.results_card)

            self.scroll.add_widget(content)

            # Dolna nawigacja w stylu Danfoss Ref Tools: zakładka chłodnicza + zawory.
            self.bottom_nav = MDBottomNavigation()
            try:
                self.bottom_nav.bind(on_switch_tabs=self._on_tab_switch)
            except Exception:  # pragma: no cover - zależne od wersji KivyMD
                log.debug("Nie udało się podpiąć on_switch_tabs", exc_info=True)
            self.tab_freezing = MDBottomNavigationItem(
                name="freezing", text=self._t("nav_freezing"), icon="snowflake"
            )
            self.tab_freezing.add_widget(self.scroll)
            self.bottom_nav.add_widget(self.tab_freezing)
            self.tab_valves = MDBottomNavigationItem(
                name="valves", text=self._t("nav_valves"), icon="valve"
            )
            self.tab_valves.add_widget(
                self._build_valve_tab(
                    dp, MDScrollView, MDCard, MDBoxLayout, MDLabel, MDTextField, MDRaisedButton
                )
            )
            self.bottom_nav.add_widget(self.tab_valves)
            root.add_widget(self.bottom_nav)

            root.add_widget(self._build_footer(dp, MDBoxLayout, MDLabel, MDRaisedButton))
            root.add_widget(self._build_ad_slot(dp, MDBoxLayout, MDIcon, MDLabel))
            Window.bind(size=self._apply_responsive_layout)
            self._apply_responsive_layout()
            Clock.schedule_once(lambda *_: self._refresh_pro_status(), 0.8)
            Clock.schedule_once(lambda *_: self._refresh_pro_status(), 3.0)
            Clock.schedule_once(lambda *_: self._refresh_ad_slot_height(), 1.2)
            Clock.schedule_once(lambda *_: self._refresh_ad_slot_height(), 3.5)
            Clock.schedule_once(lambda *_: self._refresh_ad_slot_height(), 7.0)
            Clock.schedule_once(lambda *_: self._refresh_privacy_button(), 3.0)
            Clock.schedule_once(lambda *_: self._refresh_privacy_button(), 8.0)
            return root

        # --- tekst / stan aplikacji -------------------------------------
        def _t(self, key: str, **kwargs) -> str:
            text = I18N.get(self._language, I18N["pl"]).get(key, I18N["pl"].get(key, key))
            return text.format(**kwargs) if kwargs else text

        def _toggle_language(self):
            self._language = "en" if self._language == "pl" else "pl"
            self._refresh_texts()

        def _total_text(self, total: Optional[float] = None) -> str:
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
            return max(min_value, min(max_value, value))

        def _layout_metrics(self, dp):
            width_dp, height_dp = self._screen_dp(dp)
            narrow = width_dp < 360
            compact = width_dp < 400
            short = height_dp < 720
            text_scale = self._clamp(width_dp / 412.0, 0.88, 1.06)
            product_horizontal = width_dp >= 370

            card_pad = 10 if narrow else 12 if compact else 14
            card_pad_x = card_pad
            card_pad_top = card_pad + (8 if compact else 10)
            card_pad_bottom = card_pad + (5 if compact else 6)
            content_pad = 10 if narrow else 14 if compact else 16
            stage_row_h = 56 if compact or short else 62
            props_row_h = 22 if compact or short else 24
            props_title_h = 24 if compact or short else 26
            action_h = 64 if compact else 68
            title_h = 42 if compact else 46
            total_h = 44 if compact else 50
            result_space = 8 if compact or short else 10
            field_h = 54 if compact or short else 60
            card_spacing = 10 if compact else 12
            native_ad_h = getattr(self, "_native_ad_height_dp", 0)
            reserved_ad_h = max(92 if compact else 100, native_ad_h + 18 if native_ad_h else 0)
            result_h = (
                card_pad_top
                + card_pad_bottom
                + title_h
                + action_h
                + total_h
                + (stage_row_h * 3)
                + props_title_h
                + (props_row_h * 6)
                + (result_space * 7)
            )
            params_h = (
                card_pad_top
                + card_pad_bottom
                + title_h
                + (field_h + 8)
                + (field_h * 3)
                + (card_spacing * 4)
            )

            if product_horizontal:
                product_body_h = 180 if compact else 202
                product_card_h = product_body_h + title_h + card_pad_top + card_pad_bottom + 12
                product_controls_h = product_body_h
                product_image_h = product_body_h
            else:
                product_controls_h = 116
                product_image_h = 162
                product_body_h = product_controls_h + product_image_h + 12
                product_card_h = product_body_h + title_h + card_pad_top + card_pad_bottom + 12

            return {
                "width_dp": width_dp,
                "height_dp": height_dp,
                "narrow": narrow,
                "compact": compact,
                "short": short,
                "text_scale": text_scale,
                "product_horizontal": product_horizontal,
                "content_pad": dp(content_pad),
                "content_top": dp(18 if compact else 20),
                "content_bottom": dp(26 if compact else 30),
                "content_spacing": dp(14 if compact or short else 16),
                "card_pad": dp(card_pad),
                "card_pad_x": dp(card_pad_x),
                "card_pad_top": dp(card_pad_top),
                "card_pad_bottom": dp(card_pad_bottom),
                "card_spacing": dp(card_spacing),
                "toolbar_h": dp(62 if narrow else 66 if compact else 72),
                "toolbar_icon_w": dp(36 if narrow else 40 if compact else 44),
                "toolbar_btn_w": dp(42 if narrow else 46 if compact else 48),
                "toolbar_icon_sp": 26 if compact else 30,
                "toolbar_btn_sp": 24 if compact else 28,
                "toolbar_title_sp": int(18 * text_scale) if narrow else int(20 * text_scale) if compact else 22,
                "title_h": dp(title_h),
                "title_sp": int(20 * text_scale),
                "body_sp": int(15 * text_scale),
                "caption_sp": int(12 * text_scale),
                "button_h": dp(46 if compact else 52),
                "button_sp": int(14 * text_scale),
                "field_h": dp(field_h),
                "params_h": dp(params_h),
                "product_card_h": dp(product_card_h),
                "product_body_h": dp(product_body_h),
                "product_controls_h": dp(product_controls_h),
                "product_image_h": dp(product_image_h),
                "product_body_spacing": dp(12 if compact else 14),
                "placeholder_top": dp(32 if compact else 44),
                "placeholder_bottom": dp(20 if compact else 28),
                "placeholder_icon_sp": 36 if compact else 42,
                "action_h": dp(action_h),
                "action_button_h": dp(44 if compact else 48),
                "action_sp": int(13 * text_scale) if compact else int(14 * text_scale),
                "results_h": dp(result_h),
                "results_spacing": dp(result_space),
                "total_h": dp(total_h),
                "total_sp": int(20 * text_scale),
                "stage_row_h": dp(stage_row_h),
                "stage_head_h": dp(26 if compact else 28),
                "stage_icon_w": dp(24 if compact else 28),
                "stage_icon_sp": 24 if compact else 28,
                "props_title_h": dp(props_title_h),
                "props_row_h": dp(props_row_h),
                "unit_w": dp(64 if compact else 72),
                "unit_h": dp(38 if compact else 42),
                "footer_h": dp(48 if compact else 54),
                "footer_sp": int(11 * text_scale),
                "pro_w": dp(64 if compact else 72),
                "pro_h": dp(24 if compact else 26),
                "ad_h": dp(reserved_ad_h),
            }

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
            if hasattr(self, "toolbar_snowflake"):
                self.toolbar_snowflake.width = m["toolbar_icon_w"]
                self.toolbar_snowflake.font_size = f'{m["toolbar_icon_sp"]}sp'
            if hasattr(self, "lbl_toolbar_title"):
                self.lbl_toolbar_title.font_size = f'{m["toolbar_title_sp"]}sp'
            for btn in (getattr(self, "btn_lang", None), getattr(self, "btn_theme", None)):
                if btn is not None:
                    btn.width = m["toolbar_btn_w"]
                    btn.icon_size = f'{m["toolbar_btn_sp"]}sp'

            if hasattr(self, "product_card"):
                self.product_card.padding = card_padding
                self.product_card.spacing = dp(10 if m["compact"] else 12)
                self.product_card.height = m["product_card_h"]
            if hasattr(self, "lbl_product_title"):
                self.lbl_product_title.height = m["title_h"]
                self.lbl_product_title.font_size = f'{m["title_sp"]}sp'
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
                entry["icon"].width = m["stage_icon_w"]
                entry["icon"].font_size = f'{m["stage_icon_sp"]}sp'
                entry["name_label"].font_size = f'{m["body_sp"]}sp'
                entry["value_label"].font_size = f'{m["body_sp"]}sp'
            if hasattr(self, "lbl_props_title"):
                self.lbl_props_title.height = m["props_title_h"]
                self.lbl_props_title.font_size = f'{m["body_sp"]}sp'
            if hasattr(self, "props_grid"):
                self.props_grid.row_default_height = m["props_row_h"]

            if hasattr(self, "footer_bar"):
                self.footer_bar.height = m["footer_h"]
                self.footer_bar.padding = [m["content_pad"], dp(4), m["content_pad"], dp(4)]
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
            if hasattr(self, "ad_label"):
                self.ad_label.font_size = f'{m["caption_sp"]}sp'

        def _refresh_texts(self):
            if hasattr(self, "lbl_toolbar_title"):
                self.lbl_toolbar_title.text = APP_NAME
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
                self.lbl_props_title.text = self._t("product_properties")
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
            if hasattr(self, "tab_freezing"):
                self.tab_freezing.text = self._t("nav_freezing")
            if hasattr(self, "tab_valves"):
                self.tab_valves.text = self._t("nav_valves")
            if hasattr(self, "valve_lbl_title"):
                self.valve_lbl_title.text = self._t("valve_title")
                self.valve_in_V.hint_text = self._t("valve_volume")
                self.valve_in_tp.hint_text = self._t("valve_temp_before")
                self.valve_in_tz.hint_text = self._t("valve_temp_after")
                self.valve_in_F.hint_text = self._t("valve_factor")
                self.valve_btn_calc.text = self._t("valve_calculate")
                self.valve_lbl_result.text = self._t("valve_result")
                if self._last_valve_results is not None:
                    self._render_valve_results(self._last_valve_results)
                else:
                    self.valve_lbl_count.text = self._t("valve_count", value="—")
                    self.valve_lbl_delta.text = self._t("valve_delta_t", value="—")
                    self.valve_lbl_flow.text = self._t("valve_flow", value="—")
                    self.valve_lbl_unitflow.text = self._t("valve_unit_flow", value="—")
            self._set_pro_status(self._pro_no_ads)

        def _display_category(self, category: Optional[str]) -> str:
            if not category:
                return ""
            if self._language == "en":
                return CATEGORY_LABELS_EN.get(category, category.replace("_", " "))
            return category.replace("_", " ")

        def _menu_bg_color(self):
            return (
                (0.10, 0.14, 0.18, 1)
                if self.theme_cls.theme_style == "Dark"
                else (0.91, 0.96, 1.0, 1)
            )

        def _menu_text_color(self):
            return (
                (0.94, 0.97, 1.0, 1)
                if self.theme_cls.theme_style == "Dark"
                else (0.12, 0.14, 0.16, 1)
            )

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
        def _build_toolbar(self, dp, MDBoxLayout, MDIcon, MDIconButton, MDLabel):
            bar = MDBoxLayout(
                orientation="horizontal",
                size_hint_y=None,
                height=dp(72),
                padding=[dp(14), 0, dp(8), 0],
                spacing=dp(2),
                md_bg_color=(0.12, 0.55, 0.86, 1),
            )
            self.toolbar_snowflake = MDIcon(
                icon="snowflake",
                size_hint_x=None,
                width=dp(44),
                halign="center",
                valign="middle",
                font_size="30sp",
                theme_text_color="Custom",
                text_color=(1, 1, 1, 1),
            )
            bar.add_widget(self.toolbar_snowflake)
            self.lbl_toolbar_title = MDLabel(
                text=APP_NAME,
                halign="center",
                valign="middle",
                font_style="H6",
                font_size="22sp",
                shorten=True,
                theme_text_color="Custom",
                text_color=(1, 1, 1, 1),
            )
            bar.add_widget(self.lbl_toolbar_title)
            self.btn_lang = MDIconButton(
                icon="translate",
                size_hint_x=None,
                width=dp(48),
                icon_size="28sp",
                theme_text_color="Custom",
                text_color=(1, 1, 1, 1),
                on_release=lambda *_: self._toggle_language(),
            )
            self.btn_theme = MDIconButton(
                icon="weather-night",
                size_hint_x=None,
                width=dp(48),
                icon_size="28sp",
                theme_text_color="Custom",
                text_color=(1, 1, 1, 1),
                on_release=lambda *_: self._toggle_theme(),
            )
            bar.add_widget(self.btn_lang)
            bar.add_widget(self.btn_theme)
            self.btn_privacy = MDIconButton(
                icon="shield-account",
                size_hint_x=None,
                width=dp(48),
                icon_size="26sp",
                theme_text_color="Custom",
                text_color=(1, 1, 1, 1),
                on_release=lambda *_: self._open_privacy_options(),
            )
            bar.add_widget(self.btn_privacy)
            self._refresh_privacy_button()
            return bar

        def _card_bg(self):
            return CARD_BG_DARK if self.theme_cls.theme_style == "Dark" else CARD_BG_LIGHT

        def _surface_bg(self):
            return SURFACE_DARK if self.theme_cls.theme_style == "Dark" else SURFACE_LIGHT

        def _sync_theme_surfaces(self):
            surface = self._surface_bg()
            Window.clearcolor = surface
            self.root_layout.md_bg_color = surface
            if hasattr(self, "toolbar"):
                self.toolbar.md_bg_color = (0.12, 0.55, 0.86, 1)
            for card in self._themed_cards:
                card.md_bg_color = self._card_bg()
            ad_slot = getattr(self, "ad_slot", None)
            if ad_slot is not None:
                ad_slot.md_bg_color = (
                    (0.02, 0.04, 0.06, 0.92)
                    if self.theme_cls.theme_style == "Dark"
                    else (0.86, 0.91, 0.95, 0.96)
                )
            footer_bar = getattr(self, "footer_bar", None)
            if footer_bar is not None:
                footer_bar.md_bg_color = (
                    (0.04, 0.07, 0.10, 1)
                    if self.theme_cls.theme_style == "Dark"
                    else (0.90, 0.94, 0.97, 1)
                )
            if hasattr(self, "btn_unit"):
                self._set_mass_unit(self._mass_unit)

        def _build_product_card(self, dp, MDCard, MDBoxLayout, MDIcon, MDLabel, MDRaisedButton, AsyncImage):
            card = MDCard(
                orientation="vertical",
                padding=dp(14),
                spacing=dp(12),
                size_hint_y=None,
                height=dp(292),
                radius=[16, 16, 16, 16],
                elevation=3,
                md_bg_color=self._card_bg(),
            )
            self.product_card = card
            self._themed_cards.append(card)
            self.lbl_product_title = MDLabel(
                text=self._t("product"),
                font_style="H6",
                size_hint_y=None,
                height=dp(30),
            )
            card.add_widget(self.lbl_product_title)

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
            controls.add_widget(self.btn_category)

            self.btn_product = MDRaisedButton(
                text=self._t("choose_product"),
                size_hint_x=1,
                size_hint_y=None,
                height=dp(52),
                font_size="15sp",
                disabled=True,
                on_release=lambda btn: self._open_product_menu(btn),
            )
            controls.add_widget(self.btn_product)

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
                input_filter="float",
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
                hint_text=self._t("temperature_start"), input_filter="float"
            )
            self.in_T2 = MDTextField(
                hint_text=self._t("temperature_end"), input_filter="float"
            )
            self.in_t = MDTextField(hint_text=self._t("work_time"), input_filter="float")
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

        def _build_results_card(self, dp, MDCard, MDBoxLayout, MDIcon, MDLabel, MDProgressBar, MDGridLayout, MDRaisedButton):
            card = MDCard(
                orientation="vertical",
                padding=dp(14),
                spacing=dp(8),
                size_hint_y=None,
                height=dp(574),
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

            self.bars: Dict[str, Dict] = {}
            for key, label_key, icon in [
                ("schladzanie", "cooling", "thermometer"),
                ("zamrozenie", "freezing", "snowflake"),
                ("domrozenie", "deep_freezing", "thermometer"),
            ]:
                self.bars[key] = self._add_stage_row(
                    card, key, self._t(label_key), icon, dp, MDBoxLayout, MDIcon, MDLabel, MDProgressBar
                )

            card.add_widget(
                self._make_props_title(MDLabel, dp)
            )
            self.props_grid = MDGridLayout(
                cols=2,
                size_hint_y=None,
                spacing=dp(5),
                row_default_height=dp(24),
                row_force_default=True,
            )
            self.props_grid.bind(minimum_height=self.props_grid.setter("height"))
            card.add_widget(self.props_grid)
            return card

        def _make_props_title(self, MDLabel, dp):
            self.lbl_props_title = MDLabel(
                text=self._t("product_properties"),
                font_style="Subtitle1",
                size_hint_y=None,
                height=dp(24),
            )
            return self.lbl_props_title

        def _add_stage_row(self, parent, key, label, icon, dp, MDBoxLayout, MDIcon, MDLabel, MDProgressBar):
            row = MDBoxLayout(orientation="vertical", size_hint_y=None, height=dp(62), spacing=dp(4))
            head = MDBoxLayout(orientation="horizontal", size_hint_y=None, height=dp(28), spacing=dp(8))
            icon_widget = MDIcon(
                icon=icon,
                size_hint_x=None,
                width=dp(28),
                halign="center",
                theme_text_color="Custom",
                text_color=STAGE_COLORS[key],
            )
            head.add_widget(icon_widget)
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
                md_bg_color=(0.04, 0.07, 0.10, 1),
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
                text="PRO",
                size_hint_x=None,
                width=dp(82),
                size_hint_y=None,
                height=dp(28),
                font_size="12sp",
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
                md_bg_color=(0.02, 0.04, 0.06, 0.92),
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

            self.valve_in_V = MDTextField(hint_text=self._t("valve_volume"), input_filter="float")
            self.valve_in_tp = MDTextField(hint_text=self._t("valve_temp_before"), input_filter="float")
            self.valve_in_tz = MDTextField(hint_text=self._t("valve_temp_after"), input_filter="float")
            self.valve_in_F = MDTextField(hint_text=self._t("valve_factor"), input_filter="float")
            for w in (self.valve_in_V, self.valve_in_tp, self.valve_in_tz, self.valve_in_F):
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
            res_card.add_widget(self.valve_lbl_flow)
            res_card.add_widget(self.valve_lbl_unitflow)
            content.add_widget(res_card)

            scroll.add_widget(content)
            return scroll

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
            try:
                V = self._parse_float(self.valve_in_V.text, self._t("valve_volume"))
                tp = self._parse_float(self.valve_in_tp.text, self._t("valve_temp_before"))
                tz = self._parse_float(self.valve_in_tz.text, self._t("valve_temp_after"))
                F = self._parse_float(self.valve_in_F.text, self._t("valve_factor"))
                results = calculate_decompression_valves(V, tp, tz, F, self._valve_type)
                self._last_valve_results = results
                self._render_valve_results(results)
            except ValueError as exc:
                self._show_error(str(exc))
            except Exception as exc:  # pragma: no cover - UI feedback
                log.exception("Obliczenia zaworów")
                self._show_error(self._t("calc_error", error=exc))

        def _render_valve_results(self, results):
            self.valve_lbl_count.text = self._t("valve_count", value=results.ilosc_zaworow)
            self.valve_lbl_delta.text = self._t("valve_delta_t", value=f"{results.delta_T:.4f}")
            self.valve_lbl_flow.text = self._t("valve_flow", value=f"{results.Q:.1f}")
            self.valve_lbl_unitflow.text = self._t("valve_unit_flow", value=results.przeplyw_zaworu)

        def _on_tab_switch(self, *args):
            """Reaguje na zmianę zakładki dolnej nawigacji — przełącza jednostkę reklam."""
            name = None
            for a in args:
                if isinstance(a, str) and a in ("freezing", "valves"):
                    name = a
                    break
                item_name = getattr(a, "name", None)
                if item_name in ("freezing", "valves"):
                    name = item_name
                    break
            if name is None:
                return
            self._set_active_ad_tab(name)

        def _set_active_ad_tab(self, tab: str):
            if not IS_ANDROID:
                return
            try:
                self._android_activity().setActiveAdTab(tab)
            except Exception:  # pragma: no cover - Android only
                log.debug("setActiveAdTab nie powiodło się", exc_info=True)

        def _show_product_image(self, img_path: Optional[str]) -> None:
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
                self.btn_pro.text = self._t("pro_active") if active else "PRO"
            if hasattr(self, "ad_label"):
                self.ad_label.text = self._ad_label_text()
            if hasattr(self, "ad_slot"):
                self.ad_slot.height = 0 if active else ad_height
                self.ad_slot.opacity = 0 if active else 1
                self.ad_slot.disabled = active
            if hasattr(self, "footer_label"):
                self.footer_label.text = self._status_footer_text()

        def _buy_pro(self):
            if self._pro_no_ads:
                return
            if not IS_ANDROID:
                self._show_error(self._t("pro_google_play_only"))
                return
            try:
                self._android_activity().launchProPurchase()
                Clock.schedule_once(lambda *_: self._refresh_pro_status(announce=True), 1.0)
                Clock.schedule_once(lambda *_: self._refresh_pro_status(announce=True), 4.0)
                Clock.schedule_once(lambda *_: self._refresh_pro_status(announce=True), 10.0)
            except Exception:  # pragma: no cover - Android only
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

        def _refresh_privacy_button(self):
            """Pokazuje przycisk prywatności tylko gdy UMP wymaga opcji zgody."""
            btn = getattr(self, "btn_privacy", None)
            if btn is None:
                return
            required = False
            if IS_ANDROID:
                try:
                    required = bool(self._android_activity().isPrivacyOptionsRequired())
                except Exception:  # pragma: no cover - Android only
                    log.debug("Nie udało się sprawdzić opcji prywatności", exc_info=True)
            btn.disabled = not required
            btn.opacity = 1 if required else 0

        def _open_privacy_options(self):
            """Otwiera formularz zgody UMP (zmiana zgody na reklamy / RODO)."""
            if not IS_ANDROID:
                return
            try:
                self._android_activity().showPrivacyOptionsForm()
            except Exception:  # pragma: no cover - Android only
                log.exception("Formularz prywatności")

        def _open_category_menu(self, caller):
            from kivy.metrics import dp
            from kivymd.uix.menu import MDDropdownMenu

            item_height = dp(46 if self._layout_metrics(dp)["compact"] else 52)
            items = [
                {
                    "text": self._display_category(cat),
                    "viewclass": "OneLineListItem",
                    "height": item_height,
                    "theme_text_color": "Custom",
                    "text_color": self._menu_text_color(),
                    "on_release": lambda c=cat: self._pick_category(c),
                }
                for cat in categories
            ]
            self._cat_menu = self._menu(caller, items, 3.7, dp(390), dp, MDDropdownMenu)
            self._cat_menu.open()

        def _pick_category(self, category: str):
            self._selected_category = category
            self._selected_product = None
            self.btn_category.text = self._display_category(category)
            self.btn_product.text = self._t("choose_product")
            self.btn_product.disabled = False
            self._show_product_image(None)
            if self._cat_menu:
                self._cat_menu.dismiss()

        def _open_product_menu(self, caller):
            from kivy.metrics import dp
            from kivymd.uix.menu import MDDropdownMenu

            if not self._selected_category:
                return
            item_height = dp(46 if self._layout_metrics(dp)["compact"] else 52)
            unlocked = self._entitlements.is_unlocked(self._pro_no_ads)
            items = []
            for idx, name in enumerate(list_products(catalog, self._selected_category)):
                allowed = unlocked or idx < FREE_PRODUCTS_PER_CATEGORY
                if allowed:
                    items.append(
                        {
                            "text": name,
                            "viewclass": "OneLineListItem",
                            "height": item_height,
                            "theme_text_color": "Custom",
                            "text_color": self._menu_text_color(),
                            "on_release": lambda n=name: self._pick_product(n),
                        }
                    )
                else:
                    items.append(
                        {
                            "text": f"{name}{self._t('locked_suffix')}",
                            "viewclass": "OneLineListItem",
                            "height": item_height,
                            "theme_text_color": "Custom",
                            "text_color": (0.55, 0.58, 0.62, 1),
                            "on_release": lambda *_: self._on_locked_product(),
                        }
                    )
            self._prod_menu = self._menu(caller, items, 4.4, dp(420), dp, MDDropdownMenu)
            self._prod_menu.open()

        def _on_locked_product(self):
            if self._prod_menu:
                self._prod_menu.dismiss()
            self._show_error(self._t("product_locked"))

        def _pick_product(self, name: str):
            self._selected_product = name
            self.btn_product.text = name
            img = _safe_image_path(name)
            self._show_product_image(img)
            if self._prod_menu:
                self._prod_menu.dismiss()

        # --- akcje -------------------------------------------------------
        def _toggle_mass_unit(self):
            self._set_mass_unit("t" if self._mass_unit == "kg" else "kg")

        def _set_mass_unit(self, unit: str):
            self._mass_unit = "t" if unit == "t" else "kg"
            if hasattr(self, "btn_unit"):
                self.btn_unit.text = self._mass_unit
                self.btn_unit.md_bg_color = (0.12, 0.55, 0.86, 1)
                self.btn_unit.theme_text_color = "Custom"
                self.btn_unit.text_color = (1, 1, 1, 1)

        def _toggle_theme(self):
            is_dark = self.theme_cls.theme_style == "Dark"
            self.theme_cls.theme_style = "Light" if is_dark else "Dark"
            self._sync_theme_surfaces()
            if hasattr(self, "btn_theme"):
                self.btn_theme.icon = "weather-night" if self.theme_cls.theme_style == "Dark" else "weather-sunny"

        def _reset_inputs(self):
            for field_ in (self.in_m, self.in_T1, self.in_T2, self.in_t):
                field_.text = ""
            self.lbl_total.text = self._total_text()
            for entry in self.bars.values():
                entry["bar"].value = 0
                entry["value_label"].text = "—"
            self.props_grid.clear_widgets()
            self._last_results = None

        def _build_pdf_bytes(self) -> Optional[bytes]:
            """Buduje PDF: pełny reportlab (desktop) lub fpdf2 (Android)."""
            try:
                from tpof.core.pdf_report import build_pdf

                img_path = _safe_image_path(self._last_results.produkt.nazwa)
                return build_pdf(
                    self._last_results,
                    font_path=FONT_PATH,
                    product_image_path=Path(img_path) if img_path else None,
                    watermark_image_path=WATERMARK_PATH if WATERMARK_PATH.exists() else None,
                )
            except ImportError:
                pass
            try:
                _purge_host_arch_fonttools_so()
                from tpof.core.pdf_report_mobile import build_pdf_simple
            except ImportError:
                return None
            return build_pdf_simple(self._last_results, font_path=FONT_PATH)

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
                if IS_ANDROID:
                    try:
                        self._android_activity().shareFile(
                            str(out_path),
                            "application/pdf",
                            self._t("pdf_share_subject"),
                            self._t("pdf_share_text"),
                        )
                    except Exception:  # pragma: no cover - Android only
                        log.exception("Udostępnianie PDF")
                        self._show_error(self._t("saved", path=out_path))
                else:
                    self._show_error(self._t("saved", path=out_path))
            except Exception as exc:  # pragma: no cover - UI feedback
                log.exception("Eksport PDF")
                self._show_error(self._t("pdf_error", error=exc))

        def _show_error(self, message: str):
            # KivyMD 1.2.0 udostępnia MDSnackbar; starsze wersje miały Snackbar(text=...).
            try:
                from kivymd.uix.label import MDLabel
                from kivymd.uix.snackbar import MDSnackbar
                from kivy.metrics import dp

                MDSnackbar(
                    MDLabel(text=message),
                    y=dp(24),
                    pos_hint={"center_x": 0.5},
                    size_hint_x=0.9,
                ).open()
                return
            except Exception:
                pass
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

        def _calculate(self):
            try:
                if not self._selected_category or not self._selected_product:
                    self._show_error(self._t("pick_product_error"))
                    return
                product = find_product(catalog, self._selected_category, self._selected_product)
                if product is None:
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

                masa = self._parse_float(self.in_m.text, self._t("field_mass"))
                if self._mass_unit == "t":
                    masa *= 1000.0
                T1 = self._parse_float(self.in_T1.text, self._t("field_temp_start"))
                T2 = self._parse_float(self.in_T2.text, self._t("field_temp_end"))
                czas = self._parse_float(self.in_t.text, self._t("field_time"))

                inputs = FreezingInputs(masa_kg=masa, T_pocz_C=T1, T_konc_C=T2, czas_h=czas)
                results = calculate_freezing(inputs, product)
                self._last_results = results
                self._render_results(results)
            except ValueError as exc:
                self._show_error(str(exc))
            except Exception as exc:  # pragma: no cover
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

            from kivymd.uix.label import MDLabel

            self.props_grid.clear_widgets()
            p = results.produkt
            warn = self._t("estimated") if results.T_zam_szacunkowy else ""
            # Subscripty przez Kivy markup (Roboto nie ma ₁₂).
            rows = [
                (self._t("category"), p.kategoria or "—"),
                ("c[sub]1[/sub] [kJ/kg·K]:", f"{p.c1:.2f}" if p.c1 is not None else "—"),
                ("c[sub]2[/sub] [kJ/kg·K]:", f"{p.c2:.2f}" if p.c2 is not None else "—"),
                ("L[sub]1[/sub] [kJ/kg]:", f"{p.L1:.0f}" if p.L1 is not None else "—"),
                (self._t("water"), f"{p.wodaprocent:.1f}" if p.wodaprocent is not None else "—"),
                ("T[sub]zam[/sub] [°C]:", f"{results.T_zam_uzyte_C:.2f}{warn}"),
            ]
            for label, value in rows:
                self.props_grid.add_widget(
                    MDLabel(text=label, theme_text_color="Secondary", markup=True)
                )
                self.props_grid.add_widget(MDLabel(text=value))

            # Auto-scroll do wyników po obliczeniu — żeby nie chowały się pod akcjami.
            if scroll:
                try:
                    self.scroll.scroll_to(self.results_card, padding=dp(12), animate=True)
                except Exception:  # pragma: no cover
                    pass

    ShockerCalcApp().run()


if __name__ == "__main__":
    main()

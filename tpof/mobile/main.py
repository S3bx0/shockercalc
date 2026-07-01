"""Refrigeration Calc — wersja mobilna (KivyMD).

UI w parytecie z desktopem:
  • TopAppBar z przełącznikiem Dark/Light
  • kaskadowy wybór Kategoria → Produkt
  • masa z przełącznikiem jednostek kg/t
  • paski mocy (schładzanie / zamrożenie / domrażanie) + SUMA
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
import math
import os
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional

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
from tpof.mobile.entitlements import FREE_PRODUCTS_PER_CATEGORY, MODULE_VALVES, TRIAL_DAYS, Entitlements
from tpof.mobile.paths import DATA_PATH, FONT_PATH, IMAGES_DIR
from tpof.mobile import telemetry
from tpof.mobile.user_data import CustomProductStore, UiPreferences, create_custom_product

log = logging.getLogger(__name__)

STAGE_COLORS = {
    "schladzanie": (0.11, 0.62, 0.85, 1),
    "zamrozenie": (0.49, 0.40, 0.96, 1),
    "domrozenie": (0.06, 0.76, 0.82, 1),
    "total": (0.05, 0.62, 0.42, 1),
}

BRAND_NAVY = (0.02, 0.07, 0.14, 1)
BRAND_BLUE = (0.04, 0.33, 0.54, 1)
BRAND_CYAN = (0.06, 0.72, 0.80, 1)
BRAND_ICE = (0.62, 0.94, 1.0, 1)

APP_NAME = "Refrigeration Calc"
ADMOB_APP_ID = "ca-app-pub-7481054652344026~2716191071"
ADMOB_BANNER_AD_UNIT_ID = "ca-app-pub-7481054652344026/5599859341"
ADMOB_TEST_BANNER_AD_UNIT_ID = "ca-app-pub-3940256099942544/9214589741"
PRO_SUBSCRIPTION_PRODUCT_ID = "refrigeration_pro"

IS_ANDROID = "ANDROID_ARGUMENT" in os.environ
CARD_BG_DARK = (0.09, 0.13, 0.17, 1)
CARD_BG_LIGHT = (0.96, 0.98, 1.0, 1)
SURFACE_DARK = (0.05, 0.08, 0.11, 1)
SURFACE_LIGHT = (0.93, 0.96, 0.98, 1)

ABSOLUTE_ZERO_C = -273.15
TEMP_HIGH_WARNING_C = 90.0
TEMP_HIGH_STRONG_WARNING_C = 120.0
TEMP_HIGH_ERROR_C = 130.0
TEMP_LOW_WARNING_C = -35.0
TEMP_LOW_STRONG_WARNING_C = -50.0
TEMP_LOW_EXTREME_WARNING_C = -60.0

_FONTTOOLS_SO_PURGED = False


def _runtime_font_path() -> Optional[Path]:
    """Używa fontu aplikacji albo kopii DejaVu dostarczanej przez Kivy."""
    if FONT_PATH.exists():
        return FONT_PATH
    try:
        from kivy.resources import resource_find

        found = resource_find("data/fonts/DejaVuSans.ttf")
        return Path(found) if found else None
    except ImportError:
        return None


def _numeric_input_filter(value: str, _from_undo: bool = False) -> str:
    """Pozwala wpisywac liczby z polskim przecinkiem i znakiem minus."""
    return "".join(char for char in str(value) if char in "0123456789-.,")


def _search_key(value: str) -> str:
    """Normalizuje tekst do wyszukiwania bez wielkości liter i akcentów."""
    decomposed = unicodedata.normalize("NFKD", str(value or "").casefold())
    text = "".join(char for char in decomposed if not unicodedata.combining(char))
    return text.replace("ł", "l")


def _search_product_names(names: List[str], query: str) -> List[str]:
    """Filtruje produkty, preferując początek nazwy i początek słowa."""
    normalized_query = _search_key(query).strip()
    if not normalized_query:
        return list(names)
    tokens = normalized_query.split()
    matches = []
    for index, name in enumerate(names):
        normalized_name = _search_key(name)
        if not all(token in normalized_name for token in tokens):
            continue
        words = normalized_name.split()
        if normalized_name.startswith(normalized_query):
            rank = 0
        elif any(word.startswith(tokens[0]) for word in words):
            rank = 1
        else:
            rank = 2
        matches.append((rank, index, name))
    return [name for _rank, _index, name in sorted(matches)]


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
        "product_hint": "Wybierz kategorię, a produkt znajdź przez wyszukiwarkę lub ostatnie wybory. Przycisk + dodaje własny produkt w PRO.",
        "product_picker_title": "Wybierz produkt",
        "search_products": "Szukaj produktu",
        "recent_products": "Ostatnio używane",
        "all_products": "Wszystkie produkty",
        "no_products_found": "Brak produktów pasujących do wyszukiwania",
        "add_custom_product": "Dodaj własny produkt",
        "custom_product_pro": "Własne produkty są dostępne w aktywnej wersji PRO.",
        "custom_product_title": "Własny produkt",
        "custom_product_saved": "Produkt zapisany lokalnie i dodany do listy.",
        "custom_product_limit": "Osiągnięto limit własnych produktów ({limit}).",
        "custom_name": "Nazwa produktu",
        "custom_category": "Kategoria",
        "custom_moisture": "Wilgotność [%]",
        "custom_protein": "Białko [%] (opcjonalnie)",
        "custom_fat": "Tłuszcz [%] (opcjonalnie)",
        "custom_carbs": "Węglowodany [%] (opcjonalnie)",
        "custom_fiber": "Błonnik [%] (opcjonalnie)",
        "custom_ash": "Popiół [%] (opcjonalnie)",
        "custom_tzam": "Punkt zamarzania [°C]",
        "custom_c1": "c1 powyżej zamarzania [kJ/kg·K]",
        "custom_c2": "c2 poniżej zamarzania [kJ/kg·K]",
        "custom_l1": "Ciepło topnienia L1 [kJ/kg]",
        "custom_required": "Uzupełnij poprawnie zaznaczone pole.",
        "save": "Zapisz",
        "cancel": "Anuluj",
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
        "pro_button": "PRO 4,99 zł/mies.",
        "pro_ads_off": "PRO: reklamy wyłączone",
        "pro_google_play_only": "Subskrypcja PRO działa tylko w wersji z Google Play.",
        "pro_unavailable": "Subskrypcja PRO jest chwilowo niedostępna.",
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
        "field_required": "To pole jest wymagane.",
        "hints_on": "Podpowiedzi włączone",
        "hints_off": "Podpowiedzi wyłączone",
        "hint_mass": "Wpisz masę partii; jednostkę zmienisz przyciskiem kg/t.",
        "hint_temp_start": "Temperatura produktu przed rozpoczęciem procesu.",
        "hint_temp_end": "Docelowa temperatura produktu po procesie.",
        "hint_time": "Łączny czas osiągnięcia temperatury końcowej.",
        "settings_title": "Ustawienia",
        "settings_intro": "Podstawowe ustawienia aplikacji. Część opcji jest przygotowana pod kolejne wersje.",
        "units_title": "Jednostki",
        "units_metric": "Metric: °C, kg, kW, m",
        "units_imperial": "Imperial/US: °F, lb, BTU/h, ft",
        "units_metric_active": "Aktywne: Metric",
        "units_imperial_disabled": "Imperial/US jest przygotowane, ale wyłączone do czasu pełnej konwersji wzorów.",
        "temperature_warning_high": "{field}: nietypowo wysoka temperatura ({value:.1f}°C). Zweryfikuj dane technologiczne.",
        "temperature_warning_high_strong": "{field}: bardzo wysoka temperatura ({value:.1f}°C). Zweryfikuj, czy to poprawny zakres procesu.",
        "temperature_error_high": "{field}: wartość powyżej {limit:.0f}°C jest poza bezpiecznym zakresem tej aplikacji.",
        "temperature_warning_low": "{field}: nietypowo niska temperatura ({value:.1f}°C). Zweryfikuj zakres pracy instalacji.",
        "temperature_warning_low_strong": "{field}: bardzo niska temperatura ({value:.1f}°C). To może dotyczyć układów specjalnych; sprawdź czynnik chłodniczy i projekt instalacji.",
        "temperature_warning_co2": "Dla CO₂ / R744 niskotemperaturowe zastosowania wymagają weryfikacji konfiguracji układu i zakresu pracy.",
        "temperature_error_absolute": "{field}: temperatura nie może być niższa niż zero bezwzględne (-273,15°C).",
        "telemetry_title": "Pomóż ulepszać aplikację",
        "telemetry_text": "Dobrowolne statystyki użycia, raporty błędów i zdalna konfiguracja pomagają ulepszać aplikację. Google może przetwarzać identyfikator instalacji i dane techniczne urządzenia. Wartości obliczeń, nazwy własnych produktów i pliki PDF nie są wysyłane.",
        "telemetry_enable": "Włącz",
        "telemetry_disable": "Wyłącz",
        "telemetry_not_now": "Nie teraz",
        "telemetry_on": "Statystyki i raporty błędów: włączone",
        "telemetry_off": "Statystyki i raporty błędów: wyłączone",
        "privacy_title": "Prywatność",
        "ad_privacy": "Ustawienia reklam",
        "close": "Zamknij",
        "estimated": "  (szacowane)",
        "trial_active": "Wersja próbna: pozostało {days} dni",
        "trial_last_day": "Wersja próbna: ostatni dzień",
        "trial_expired": "Wersja darmowa • 1 produkt z listy",
        "pro_unlocked_footer": "PRO • pełen dostęp",
        "locked_suffix": "  — PRO",
        "product_locked": "Ten produkt jest dostępny w PRO. W wersji darmowej masz 1 produkt z każdej listy.",
        "trial_expired_info": "Okres próbny dobiegł końca. Subskrybuj PRO, aby odblokować wszystkie produkty.",
        "watch_ad_for_token": "Obejrzyj reklamę, aby wykonać 1 bezpłatne przeliczenie tego produktu.",
        "ad_token_earned": "Masz token! Naciśnij Oblicz, aby wykonać bezpłatne przeliczenie.",
        "ad_thanks": "Dziękujemy za obejrzenie reklamy! Masz 1 bezpłatne przeliczenie.",
        "pro_thanks": "Dziękujemy za subskrypcję PRO! Reklamy wyłączone, pełen dostęp odblokowany.",
        "ad_not_ready": "Reklama jeszcze się ładuje. Spróbuj za chwilę.",
        "ad_limit_reached": "Dzienny limit reklam wyczerpany. Subskrybuj PRO, aby liczyć bez ograniczeń.",
        "nav_freezing": "Chłodnicze",
        "nav_valves": "Zawory",
        "valve_title": "Zawory dekompresyjne",
        "valve_type": "Typ zaworu",
        "valve_mode_volume": "Kubatura",
        "valve_mode_dims": "Wymiary",
        "valve_volume": "Objętość komory [m³]",
        "valve_length": "Długość [m]",
        "valve_width": "Szerokość [m]",
        "valve_height": "Wysokość [m]",
        "valve_temp_before": "Temp. przed wlotem [°C]",
        "valve_temp_after": "Temp. za wlotem [°C]",
        "valve_coolers": "Ilość chłodnic",
        "valve_flow_per": "Przepływ na 1 chłodnicę [m³/h]",
        "valve_coolers_min": "Ilość chłodnic musi być co najmniej 1.",
        "valve_flow_positive": "Przepływ na 1 chłodnicę musi być większy od zera.",
        "hint_valve_volume": "Podaj kubaturę netto komory w m³.",
        "hint_valve_length": "Wewnętrzna długość komory w metrach.",
        "hint_valve_width": "Wewnętrzna szerokość komory w metrach.",
        "hint_valve_height": "Wewnętrzna wysokość komory w metrach.",
        "hint_valve_temp_before": "Temperatura powietrza przed chłodnicą.",
        "hint_valve_temp_after": "Temperatura powietrza za chłodnicą.",
        "hint_valve_coolers": "Liczba pracujących chłodnic w komorze.",
        "hint_valve_flow": "Nominalny przepływ jednej chłodnicy w m³/h.",
        "valve_calculate": "Oblicz zawory",
        "valve_result": "Wynik",
        "valve_delta_t": "Tempo zmian ΔT: {value} °C/min",
        "valve_total_flow": "Przepływ całkowity F: {value} m³/h",
        "valve_flow": "Wymagany przepływ Q: {value} l/min",
        "valve_unit_flow": "Przepływ zaworu: {value} l/min",
        "valve_count": "Liczba zaworów: {value}",
        "valve_locked": "Moduł doboru zaworów dekompresyjnych jest częścią PRO. Subskrybuj PRO, kup moduł jednorazowo albo obejrzyj reklamę za jedno przeliczenie.",
        "valve_locked_hint": "Moduł zaworów zablokowany — subskrybuj PRO, kup moduł lub obejrzyj reklamę.",
        "valve_buy": "Kup moduł jednorazowo",
        "valve_watch_ad": "Obejrzyj reklamę (1 przeliczenie)",
        "valve_purchase_unavailable": "Zakup chwilowo niedostępny. Spróbuj ponownie później.",
        "valve_unlocked_thanks": "Dziękujemy! Moduł zaworów odblokowany na stałe.",
    },
    "en": {
        "product": "Product",
        "choose_category": "Choose category",
        "choose_product": "Choose product",
        "product_hint": "Choose a category, then find a product using search or recent selections. The + button adds a custom PRO product.",
        "product_picker_title": "Choose product",
        "search_products": "Search products",
        "recent_products": "Recently used",
        "all_products": "All products",
        "no_products_found": "No matching products",
        "add_custom_product": "Add custom product",
        "custom_product_pro": "Custom products require an active PRO subscription.",
        "custom_product_title": "Custom product",
        "custom_product_saved": "Product saved locally and added to the list.",
        "custom_product_limit": "Custom product limit reached ({limit}).",
        "custom_name": "Product name",
        "custom_category": "Category",
        "custom_moisture": "Moisture [%]",
        "custom_protein": "Protein [%] (optional)",
        "custom_fat": "Fat [%] (optional)",
        "custom_carbs": "Carbohydrates [%] (optional)",
        "custom_fiber": "Fiber [%] (optional)",
        "custom_ash": "Ash [%] (optional)",
        "custom_tzam": "Freezing point [°C]",
        "custom_c1": "c1 above freezing [kJ/kg·K]",
        "custom_c2": "c2 below freezing [kJ/kg·K]",
        "custom_l1": "Latent heat L1 [kJ/kg]",
        "custom_required": "Complete the highlighted field correctly.",
        "save": "Save",
        "cancel": "Cancel",
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
        "pro_button": "PRO 4.99 zł/mo",
        "pro_ads_off": "PRO: ads disabled",
        "pro_google_play_only": "PRO subscription works only in the Google Play build.",
        "pro_unavailable": "PRO subscription is temporarily unavailable.",
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
        "field_required": "This field is required.",
        "hints_on": "Hints enabled",
        "hints_off": "Hints disabled",
        "hint_mass": "Enter the batch mass; use the kg/t button to change units.",
        "hint_temp_start": "Product temperature before the process starts.",
        "hint_temp_end": "Target product temperature after the process.",
        "hint_time": "Total time required to reach the final temperature.",
        "settings_title": "Settings",
        "settings_intro": "Basic app settings. Some options are prepared for future releases.",
        "units_title": "Units",
        "units_metric": "Metric: °C, kg, kW, m",
        "units_imperial": "Imperial/US: °F, lb, BTU/h, ft",
        "units_metric_active": "Active: Metric",
        "units_imperial_disabled": "Imperial/US is prepared but disabled until full formula conversion is implemented.",
        "temperature_warning_high": "{field}: unusually high temperature ({value:.1f}°C). Verify the process data.",
        "temperature_warning_high_strong": "{field}: very high temperature ({value:.1f}°C). Verify this process range.",
        "temperature_error_high": "{field}: values above {limit:.0f}°C are outside this app's safe input range.",
        "temperature_warning_low": "{field}: unusually low temperature ({value:.1f}°C). Verify the system operating range.",
        "temperature_warning_low_strong": "{field}: very low temperature ({value:.1f}°C). This may indicate a special low-temperature system; verify refrigerant and system design.",
        "temperature_warning_co2": "For CO₂ / R744, low-temperature applications require verification of system configuration and operating range.",
        "temperature_error_absolute": "{field}: temperature cannot be below absolute zero (-273.15°C).",
        "telemetry_title": "Help improve the app",
        "telemetry_text": "Optional usage statistics, crash reports, and remote configuration help improve the app. Google may process an installation identifier and technical device data. Calculation values, custom product names, and PDF files are never sent.",
        "telemetry_enable": "Enable",
        "telemetry_disable": "Disable",
        "telemetry_not_now": "Not now",
        "telemetry_on": "Usage statistics and crash reports: enabled",
        "telemetry_off": "Usage statistics and crash reports: disabled",
        "privacy_title": "Privacy",
        "ad_privacy": "Ad privacy settings",
        "close": "Close",
        "estimated": "  (estimated)",
        "trial_active": "Trial: {days} days left",
        "trial_last_day": "Trial: last day",
        "trial_expired": "Free version • 1 product per list",
        "pro_unlocked_footer": "PRO • full access",
        "locked_suffix": "  — PRO",
        "product_locked": "This product is available in PRO. The free version allows 1 product per list.",
        "trial_expired_info": "The trial has ended. Subscribe to PRO to unlock all products.",
        "watch_ad_for_token": "Watch an ad to run 1 free calculation for this product.",
        "ad_token_earned": "Token granted! Tap Calculate to run your free calculation.",
        "ad_thanks": "Thanks for watching the ad! You have 1 free calculation.",
        "pro_thanks": "Thank you for subscribing to PRO! Ads disabled, full access unlocked.",
        "ad_not_ready": "The ad is still loading. Try again in a moment.",
        "ad_limit_reached": "Daily ad limit reached. Subscribe to PRO to calculate without limits.",
        "nav_freezing": "Cooling",
        "nav_valves": "Valves",
        "valve_title": "Decompression valves",
        "valve_type": "Valve type",
        "valve_mode_volume": "Volume",
        "valve_mode_dims": "Dimensions",
        "valve_volume": "Chamber volume [m³]",
        "valve_length": "Length [m]",
        "valve_width": "Width [m]",
        "valve_height": "Height [m]",
        "valve_temp_before": "Temp. before cooler [°C]",
        "valve_temp_after": "Temp. after cooler [°C]",
        "valve_coolers": "Number of coolers",
        "valve_flow_per": "Flow per cooler [m³/h]",
        "valve_coolers_min": "Number of coolers must be at least 1.",
        "valve_flow_positive": "Flow per cooler must be greater than zero.",
        "hint_valve_volume": "Enter the chamber net volume in m³.",
        "hint_valve_length": "Internal chamber length in metres.",
        "hint_valve_width": "Internal chamber width in metres.",
        "hint_valve_height": "Internal chamber height in metres.",
        "hint_valve_temp_before": "Air temperature before the cooler.",
        "hint_valve_temp_after": "Air temperature after the cooler.",
        "hint_valve_coolers": "Number of operating coolers in the chamber.",
        "hint_valve_flow": "Nominal airflow of one cooler in m³/h.",
        "valve_calculate": "Calculate valves",
        "valve_result": "Result",
        "valve_delta_t": "Change rate ΔT: {value} °C/min",
        "valve_total_flow": "Total flow F: {value} m³/h",
        "valve_flow": "Required flow Q: {value} l/min",
        "valve_unit_flow": "Valve flow: {value} l/min",
        "valve_count": "Number of valves: {value}",
        "valve_locked": "The decompression valve module is included in PRO. Subscribe to PRO, buy the module once, or watch an ad for a single calculation.",
        "valve_locked_hint": "Valve module locked — subscribe to PRO, buy the module, or watch an ad.",
        "valve_buy": "Buy module (one-time)",
        "valve_watch_ad": "Watch an ad (1 calculation)",
        "valve_purchase_unavailable": "Purchase is temporarily unavailable. Please try again later.",
        "valve_unlocked_thanks": "Thank you! The valve module is now unlocked.",
    },
}

for _fallback_lang in ("es", "fr", "it", "pt", "ja", "zh"):
    I18N[_fallback_lang] = dict(I18N["en"])

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

FEATURED_MOBILE_CATEGORIES = ("owoce", "warzywa")
_POLISH_SORT_TRANSLATION = str.maketrans({"ł": "l", "Ł": "L"})


def _mobile_sort_key(value: str) -> str:
    """Zwraca stabilny klucz sortowania nazw polskich i angielskich."""
    normalized = unicodedata.normalize("NFKD", value.translate(_POLISH_SORT_TRANSLATION))
    return "".join(
        char for char in normalized if not unicodedata.combining(char)
    ).casefold()


def _ordered_mobile_categories(
    categories: List[str], display_name: Optional[Callable[[str], str]] = None
) -> tuple[List[str], List[str]]:
    """Umieszcza owoce i warzywa na początku, resztę sortuje alfabetycznie."""
    display_name = display_name or (lambda category: category.replace("_", " "))
    available = list(dict.fromkeys(categories))
    featured = [category for category in FEATURED_MOBILE_CATEGORIES if category in available]
    remaining = sorted(
        (category for category in available if category not in featured),
        key=lambda category: _mobile_sort_key(display_name(category)),
    )
    return featured, remaining


def _is_mobile_hidden_product(category: str, product_name: str) -> bool:
    """Ukrywa techniczne rekordy CTP wyłącznie w mobilnym selektorze."""
    return category.casefold() == "różne" and product_name.casefold().endswith(
        "_ctp aldi"
    )


def _mobile_product_names(catalog: Dict[str, List[Product]], category: str) -> List[str]:
    return [
        name
        for name in list_products(catalog, category)
        if not _is_mobile_hidden_product(category, name)
    ]


def _safe_image_path(nazwa: str) -> Optional[str]:
    """Zwraca ścieżkę do .webp/.png/.jpg dla produktu albo None."""
    for ext in (".webp", ".png", ".jpg", ".jpeg"):
        candidate = IMAGES_DIR / f"{nazwa}{ext}"
        if candidate.exists():
            return str(candidate)
    return None


def _sync_module_ownership(entitlements: Entitlements, module_id: str, owned: bool) -> None:
    """Synchronizuje lokalne uprawnienie modułu z aktualnym stanem Google Play."""
    if owned:
        entitlements.grant_module(module_id)
    else:
        entitlements.revoke_module(module_id)


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
        from kivy.graphics import Color, Ellipse, Line, Rectangle, RoundedRectangle
        from kivy.graphics.texture import Texture
        from kivy.metrics import dp
        from kivy.uix.image import AsyncImage
        from kivy.uix.floatlayout import FloatLayout
        from kivy.uix.widget import Widget
        from kivymd.app import MDApp
        from kivymd.uix.bottomnavigation import (
            MDBottomNavigation,
            MDBottomNavigationItem,
        )
        from kivymd.uix.boxlayout import MDBoxLayout
        from kivymd.uix.button import MDIconButton, MDRaisedButton
        from kivymd.uix.card import MDCard
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
    catalog: Dict[str, List[Product]] = load_products(DATA_PATH)
    custom_products = CustomProductStore()
    custom_products.merge_into(catalog)
    categories = list_categories(catalog)

    class FrostBackground(Widget):
        """Subtelne, wolno poruszajace sie lodowe refleksy pod interfejsem."""

        PARTICLE_COUNT = 18

        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self._elapsed = 0.0
            self._dark = True
            self._particles = [
                {
                    "x": ((index * 47) % 101) / 100.0,
                    "y": ((index * 71 + 13) % 103) / 102.0,
                    "speed": 0.0018 + (index % 5) * 0.00035,
                    "phase": index * 1.73,
                    "size": dp(1.6 + (index % 4) * 0.45),
                }
                for index in range(self.PARTICLE_COUNT)
            ]

            with self.canvas.before:
                Color(1, 1, 1, 1)
                self._background = Rectangle(pos=self.pos, size=self.size)
                self._band_colors = []
                self._bands = []
                for _index in range(4):
                    color = Color(1, 1, 1, 0.04)
                    band = Line(points=[], width=dp(30), cap="none")
                    self._band_colors.append(color)
                    self._bands.append(band)

            self._particle_graphics = []
            with self.canvas:
                for _particle in self._particles:
                    color = Color(0.48, 0.86, 1.0, 0.14)
                    horizontal = Line(width=0.65)
                    vertical = Line(width=0.65)
                    diagonal = Line(width=0.45)
                    self._particle_graphics.append(
                        (color, horizontal, vertical, diagonal)
                    )

            self.bind(pos=self._sync_background, size=self._sync_background)
            self.set_dark(True)
            self._animation_event = Clock.schedule_interval(
                self._animate_particles, 1.0 / 15.0
            )

        def set_dark(self, dark: bool):
            self._dark = bool(dark)
            top = (5, 20, 38) if self._dark else (226, 244, 252)
            bottom = (8, 52, 84) if self._dark else (184, 222, 241)
            texture = Texture.create(size=(1, 96), colorfmt="rgba")
            pixels = bytearray()
            for row in range(96):
                fraction = row / 95.0
                eased = fraction * fraction * (3.0 - 2.0 * fraction)
                pixels.extend(
                    int(bottom[channel] * (1.0 - eased) + top[channel] * eased)
                    for channel in range(3)
                )
                pixels.append(255)
            texture.blit_buffer(bytes(pixels), colorfmt="rgba", bufferfmt="ubyte")
            texture.mag_filter = "linear"
            texture.min_filter = "linear"
            self._background.texture = texture
            self._gradient_texture = texture
            for color, *_lines in self._particle_graphics:
                color.rgba = (
                    (0.48, 0.86, 1.0, 0.14)
                    if self._dark
                    else (0.12, 0.48, 0.68, 0.12)
                )
            band_palette = (
                [
                    (0.12, 0.58, 0.82, 0.06),
                    (0.04, 0.74, 0.80, 0.04),
                    (1.00, 1.00, 1.00, 0.03),
                    (0.25, 0.72, 1.00, 0.028),
                ]
                if self._dark
                else [
                    (0.11, 0.59, 0.82, 0.06),
                    (0.03, 0.70, 0.78, 0.045),
                    (1.00, 1.00, 1.00, 0.10),
                    (0.16, 0.58, 0.94, 0.04),
                ]
            )
            for color, rgba in zip(self._band_colors, band_palette):
                color.rgba = rgba
            self._sync_background()

        def _sync_background(self, *_args):
            self._background.pos = self.pos
            self._background.size = self.size
            self._position_bands()
            self._position_particles()

        def _position_bands(self):
            if self.width <= 0 or self.height <= 0:
                return
            x, y, width, height = self.x, self.y, self.width, self.height
            specs = [
                (-0.22, 0.94, 0.26, 1.13),
                (0.74, 1.02, 1.14, 0.78),
                (-0.16, 0.16, 0.22, -0.04),
                (0.64, 0.18, 1.10, -0.04),
            ]
            for band, (x1, y1, x2, y2) in zip(self._bands, specs):
                band.points = [
                    x + width * x1,
                    y + height * y1,
                    x + width * x2,
                    y + height * y2,
                ]

        def _animate_particles(self, dt):
            self._elapsed += min(float(dt), 0.2)
            for particle in self._particles:
                particle["y"] += particle["speed"] * min(float(dt), 0.2) * 15.0
                if particle["y"] > 1.04:
                    particle["y"] = -0.04
            self._position_particles()

        def _position_particles(self):
            if self.width <= 0 or self.height <= 0:
                return
            for particle, graphics in zip(
                self._particles, self._particle_graphics
            ):
                _color, horizontal, vertical, diagonal = graphics
                drift = math.sin(self._elapsed * 0.32 + particle["phase"]) * dp(5)
                x = self.x + particle["x"] * self.width + drift
                y = self.y + particle["y"] * self.height
                size = particle["size"]
                horizontal.points = [x - size, y, x + size, y]
                vertical.points = [x, y - size, x, y + size]
                diagonal.points = [
                    x - size * 0.55,
                    y - size * 0.55,
                    x + size * 0.55,
                    y + size * 0.55,
                ]

    class BrandToolbar(MDBoxLayout):
        """Gradientowy pasek naglowka nawiazujacy do nowego logo."""

        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.md_bg_color = (0, 0, 0, 0)
            self._gradient_texture = self._make_gradient_texture()
            with self.canvas.before:
                Color(1, 1, 1, 1)
                self._background = Rectangle(pos=self.pos, size=self.size)
                Color(1, 1, 1, 0.10)
                self._shine_left = Line(points=[], width=dp(16))
                Color(1, 1, 1, 0.06)
                self._shine_right = Line(points=[], width=dp(22))
                Color(0, 0, 0, 0.28)
                self._bottom_shadow = Rectangle(pos=self.pos, size=(0, 0))
                Color(*BRAND_ICE[:3], 0.72)
                self._bottom_accent = Rectangle(pos=self.pos, size=(0, 0))
            self._background.texture = self._gradient_texture
            self.bind(pos=self._sync_canvas, size=self._sync_canvas)
            self._sync_canvas()

        @staticmethod
        def _make_gradient_texture():
            stops = [
                (0.0, (3, 17, 36, 255)),
                (0.42, (6, 78, 126, 255)),
                (0.74, (11, 142, 182, 255)),
                (1.0, (16, 179, 196, 255)),
            ]
            texture = Texture.create(size=(192, 1), colorfmt="rgba")
            pixels = bytearray()
            for col in range(192):
                fraction = col / 191.0
                color = stops[-1][1]
                for index in range(len(stops) - 1):
                    left_stop, left_color = stops[index]
                    right_stop, right_color = stops[index + 1]
                    if left_stop <= fraction <= right_stop:
                        local = (fraction - left_stop) / (right_stop - left_stop)
                        local = local * local * (3.0 - 2.0 * local)
                        color = tuple(
                            int(left_color[channel] * (1.0 - local) + right_color[channel] * local)
                            for channel in range(4)
                        )
                        break
                pixels.extend(color)
            texture.blit_buffer(bytes(pixels), colorfmt="rgba", bufferfmt="ubyte")
            texture.mag_filter = "linear"
            texture.min_filter = "linear"
            return texture

        def _sync_canvas(self, *_args):
            self._background.pos = self.pos
            self._background.size = self.size
            self._bottom_shadow.pos = (self.x, self.y)
            self._bottom_shadow.size = (self.width, dp(8))
            self._bottom_accent.pos = (self.x, self.y)
            self._bottom_accent.size = (self.width, dp(2))
            self._shine_left.points = [
                self.x + self.width * 0.16,
                self.top + dp(8),
                self.x + self.width * 0.02,
                self.y - dp(8),
            ]
            self._shine_right.points = [
                self.x + self.width * 0.78,
                self.top + dp(12),
                self.x + self.width * 0.57,
                self.y - dp(12),
            ]

    class FrostChip(MDBoxLayout):
        """Mała półprzezroczysta kapsuła pod ikonę."""

        def __init__(self, *, active: bool = False, accent=BRAND_ICE, **kwargs):
            super().__init__(**kwargs)
            self.orientation = "vertical"
            self.size_hint_x = None
            self.size_hint_y = None
            self.pos_hint = {"center_y": 0.5}
            self.active = active
            self.accent = accent
            with self.canvas.before:
                self._outer_color = Color(1, 1, 1, 0.16)
                self._outer = RoundedRectangle(
                    pos=self.pos, size=self.size, radius=[dp(18)] * 4
                )
                self._inner_color = Color(1, 1, 1, 0.08)
                self._inner = RoundedRectangle(
                    pos=self.pos, size=self.size, radius=[dp(17)] * 4
                )
            self.bind(pos=self._sync_canvas, size=self._sync_canvas)
            self.set_active(active)

        def set_active(self, active: bool):
            self.active = bool(active)
            accent = self.accent
            self._outer_color.rgba = (
                (accent[0], accent[1], accent[2], 0.42)
                if self.active
                else (1, 1, 1, 0.13)
            )
            self._inner_color.rgba = (
                (1, 1, 1, 0.17)
                if self.active
                else (1, 1, 1, 0.075)
            )

        def _sync_canvas(self, *_args):
            radius = [min(self.width, self.height) * 0.36] * 4
            self._outer.pos = self.pos
            self._outer.size = self.size
            self._outer.radius = radius
            inset = dp(1.15)
            self._inner.pos = (self.x + inset, self.y + inset)
            self._inner.size = (
                max(0, self.width - inset * 2),
                max(0, self.height - inset * 2),
            )
            self._inner.radius = [max(0, radius[0] - inset)] * 4

    class StageIconBadge(MDBoxLayout):
        """Znak etapu wyniku z subtelnym tłem i akcentem koloru."""

        def __init__(self, *, accent, **kwargs):
            super().__init__(**kwargs)
            self.orientation = "vertical"
            self.size_hint_x = None
            self.size_hint_y = None
            self.accent = accent
            with self.canvas.before:
                Color(1, 1, 1, 0.075)
                self._outer = RoundedRectangle(
                    pos=self.pos, size=self.size, radius=[dp(14)] * 4
                )
                Color(accent[0], accent[1], accent[2], 0.18)
                self._inner = RoundedRectangle(
                    pos=self.pos, size=self.size, radius=[dp(13)] * 4
                )
            self.bind(pos=self._sync_canvas, size=self._sync_canvas)
            self._sync_canvas()

        def _sync_canvas(self, *_args):
            radius = [min(self.width, self.height) * 0.32] * 4
            self._outer.pos = self.pos
            self._outer.size = self.size
            self._outer.radius = radius
            inset = dp(1.5)
            self._inner.pos = (self.x + inset, self.y + inset)
            self._inner.size = (
                max(0, self.width - inset * 2),
                max(0, self.height - inset * 2),
            )
            self._inner.radius = [max(0, radius[0] - inset)] * 4

    class StageMotionIcon(Widget):
        """Lekka animacja etapu wyniku bez dokladania plikow GIF do paczki."""

        def __init__(self, *, mode: str, accent, **kwargs):
            super().__init__(**kwargs)
            self.mode = mode
            self.accent = accent
            self.font_size = "24sp"
            self._elapsed = 0.0
            self._event = None
            self._snow_lines = []
            self._snow_dots = []
            with self.canvas:
                if self.mode == "zamrozenie":
                    self._snow_color = Color(*accent[:3], 0.95)
                    for _index in range(18):
                        self._snow_lines.append(Line(points=[], width=dp(1.45), cap="round"))
                    self._frost_color = Color(0.90, 0.98, 1.0, 0.0)
                    for _index in range(7):
                        self._snow_dots.append(Ellipse(pos=(0, 0), size=(0, 0)))
                else:
                    self._tube_bg_color = Color(1, 1, 1, 0.16)
                    self._tube_bg = RoundedRectangle(pos=(0, 0), size=(0, 0), radius=[dp(4)] * 4)
                    self._fill_color = Color(*accent[:3], 0.92)
                    self._tube_fill = RoundedRectangle(pos=(0, 0), size=(0, 0), radius=[dp(4)] * 4)
                    self._bulb_fill = Ellipse(pos=(0, 0), size=(0, 0))
                    self._edge_color = Color(1, 1, 1, 0.34)
                    self._tube_edge = Line(points=[], width=dp(1.1), cap="round")
                    self._tick = Line(points=[], width=dp(0.9), cap="round")
            self.bind(pos=self._sync_canvas, size=self._sync_canvas)
            self._event = Clock.schedule_interval(self._tick_motion, 1.0 / 24.0)
            self._sync_canvas()

        @staticmethod
        def _mix(left, right, fraction):
            fraction = max(0.0, min(1.0, float(fraction)))
            return tuple(
                left[index] * (1.0 - fraction) + right[index] * fraction
                for index in range(3)
            )

        def on_parent(self, _instance, parent):
            if parent is None and self._event is not None:
                self._event.cancel()
                self._event = None

        def _tick_motion(self, dt):
            self._elapsed += min(float(dt), 0.12)
            self._sync_canvas()

        def _sync_canvas(self, *_args):
            if self.width <= 0 or self.height <= 0:
                return
            if self.mode == "zamrozenie":
                self._sync_snowflake()
            else:
                self._sync_thermometer()

        def _sync_thermometer(self):
            size = min(self.width, self.height)
            cx = self.x + self.width * 0.5
            cy = self.y + self.height * 0.5
            phase = (self._elapsed / 2.6) % 1.0
            phase = phase * phase * (3.0 - 2.0 * phase)
            if self.mode == "domrozenie":
                color = self._mix((0.18, 0.86, 1.0), (0.38, 0.20, 0.92), phase)
                level = 0.78 - 0.46 * phase
            else:
                color = self._mix((0.96, 0.28, 0.20), (0.08, 0.72, 0.92), phase)
                level = 0.86 - 0.60 * phase
            tube_w = max(dp(5), size * 0.14)
            tube_h = size * 0.47
            bulb = size * 0.28
            tube_x = cx - tube_w * 0.5
            tube_y = cy - size * 0.08
            fill_h = max(dp(4), tube_h * level)
            self._fill_color.rgba = (color[0], color[1], color[2], 0.94)
            self._tube_bg.pos = (tube_x, tube_y)
            self._tube_bg.size = (tube_w, tube_h)
            self._tube_bg.radius = [tube_w * 0.5] * 4
            self._tube_fill.pos = (tube_x, tube_y)
            self._tube_fill.size = (tube_w, fill_h)
            self._tube_fill.radius = [tube_w * 0.5] * 4
            self._bulb_fill.pos = (cx - bulb * 0.5, tube_y - bulb * 0.58)
            self._bulb_fill.size = (bulb, bulb)
            self._tube_edge.points = [
                cx,
                tube_y,
                cx,
                tube_y + tube_h,
            ]
            self._tick.points = [
                cx + tube_w * 0.9,
                tube_y + tube_h * (0.75 - 0.5 * phase),
                cx + tube_w * 1.9,
                tube_y + tube_h * (0.75 - 0.5 * phase),
            ]

        def _sync_snowflake(self):
            size = min(self.width, self.height)
            cx = self.x + self.width * 0.5
            cy = self.y + self.height * 0.5
            phase = (math.sin(self._elapsed * 1.45) + 1.0) * 0.5
            color = self._mix((0.18, 0.84, 0.95), self.accent[:3], phase)
            self._snow_color.rgba = (color[0], color[1], color[2], 0.84 + 0.14 * phase)
            radius = size * (0.26 + 0.05 * phase)
            branch = radius * 0.34
            lines = []
            for arm in range(6):
                angle = math.tau * arm / 6.0 - math.pi / 2.0
                end_x = cx + math.cos(angle) * radius
                end_y = cy + math.sin(angle) * radius
                lines.append((cx, cy, end_x, end_y))
                for side in (-1, 1):
                    side_angle = angle + side * math.radians(42)
                    base_x = cx + math.cos(angle) * radius * 0.58
                    base_y = cy + math.sin(angle) * radius * 0.58
                    lines.append(
                        (
                            base_x,
                            base_y,
                            base_x - math.cos(side_angle) * branch,
                            base_y - math.sin(side_angle) * branch,
                        )
                    )
            for line, points in zip(self._snow_lines, lines):
                line.points = points
            self._frost_color.rgba = (0.90, 0.98, 1.0, 0.16 + 0.34 * phase)
            for index, dot in enumerate(self._snow_dots):
                orbit = radius * (0.35 + (index % 3) * 0.22)
                angle = self._elapsed * (0.8 + index * 0.08) + index * 1.37
                dot_size = dp(1.4 + (index % 3) * 0.45)
                dot.pos = (
                    cx + math.cos(angle) * orbit - dot_size * 0.5,
                    cy + math.sin(angle) * orbit - dot_size * 0.5,
                )
                dot.size = (dot_size, dot_size)

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
            self._product_dialog = None
            self._product_search_field = None
            self._product_results_list = None
            self._product_dialog_names: List[str] = []
            self._product_dialog_indexes: Dict[str, int] = {}
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
            self._validation_bound_fields = set()
            self._native_ad_height_dp = 0
            self._pro_no_ads = False
            self._pro_thanks_shown = False
            self._valve_type = "Maxi Elebar"
            self._valve_input_mode = "K"  # "K" = kubatura, "W" = wymiary
            self._last_valve_results = None
            self._valve_menu: Optional[MDDropdownMenu] = None
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
            text = I18N.get(self._language, I18N["pl"]).get(key, I18N["pl"].get(key, key))
            return text.format(**kwargs) if kwargs else text

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

        def _mark_field_error(self, field, message: Optional[str] = None):
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

        def _temperature_warning(self, field_name: str, value: float) -> Optional[str]:
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

        def _validate_temperature_input(self, field, field_name: str, value: float) -> Optional[str]:
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
            product_hint_h = 30 if self._hints_enabled else 0

            card_pad = 10 if narrow else 12 if compact else 14
            card_pad_x = card_pad
            card_pad_top = card_pad + (8 if compact else 10)
            card_pad_bottom = card_pad + (5 if compact else 6)
            content_pad = 10 if narrow else 14 if compact else 16
            stage_row_h = 66 if compact or short else 74
            action_h = 64 if compact else 68
            title_h = 42 if compact else 46
            total_h = 44 if compact else 50
            result_space = 8 if compact or short else 10
            field_h = 54 if compact or short else 60
            card_spacing = 10 if compact else 12
            native_ad_h = getattr(self, "_native_ad_height_dp", 0)
            reserved_ad_h = max(64 if compact else 70, native_ad_h + 8 if native_ad_h else 0)
            result_h = (
                card_pad_top
                + card_pad_bottom
                + title_h
                + action_h
                + total_h
                + (stage_row_h * 3)
                + (result_space * 5)
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
                product_card_h = (
                    product_body_h + title_h + product_hint_h
                    + card_pad_top + card_pad_bottom + 12
                )
                product_controls_h = product_body_h
                product_image_h = product_body_h
            else:
                product_controls_h = 130
                product_image_h = 162
                product_body_h = product_controls_h + product_image_h + 12
                product_card_h = (
                    product_body_h + title_h + product_hint_h
                    + card_pad_top + card_pad_bottom + 12
                )

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
                "toolbar_icon_w": dp(38 if narrow else 42 if compact else 44),
                "toolbar_btn_w": dp(40 if narrow else 42 if compact else 44),
                "toolbar_icon_sp": 24 if narrow else 26 if compact else 28,
                "toolbar_btn_sp": 23 if narrow else 24 if compact else 26,
                "toolbar_title_sp": int(14 * text_scale) if narrow else int(15 * text_scale) if compact else 16,
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
                "product_hint_h": dp(product_hint_h),
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
                "stage_head_h": dp(34 if compact else 38),
                "stage_icon_w": dp(34 if compact else 38),
                "stage_icon_sp": 22 if compact else 24,
                "unit_w": dp(64 if compact else 72),
                "unit_h": dp(38 if compact else 42),
                "footer_h": dp(42 if compact else 46),
                "footer_sp": int(11 * text_scale),
                "pro_w": dp(116 if compact else 128),
                "pro_h": dp(28),
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

            if hasattr(self, "bottom_nav"):
                # MDBottomNavigation owns the tab screen area as well as the bar,
                # so it must remain the expanding child in the root layout.
                self.bottom_nav.size_hint_y = 1
                for attr, value in (
                    ("panel_color", (0.07, 0.08, 0.10, 1)),
                    ("text_color_active", BRAND_ICE),
                    ("text_color_normal", (0.74, 0.80, 0.84, 1)),
                ):
                    try:
                        setattr(self.bottom_nav, attr, value)
                    except Exception:
                        pass

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
            if hasattr(self, "tab_freezing"):
                self.tab_freezing.text = self._t("nav_freezing")
            if hasattr(self, "tab_valves"):
                self.tab_valves.text = self._t("nav_valves")
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

        def _card_bg(self):
            return CARD_BG_DARK if self.theme_cls.theme_style == "Dark" else CARD_BG_LIGHT

        def _surface_bg(self):
            return SURFACE_DARK if self.theme_cls.theme_style == "Dark" else SURFACE_LIGHT

        def _style_app_button(self, button, variant: str = "primary"):
            palettes = {
                "primary": ((0.04, 0.42, 0.68, 1), (1, 1, 1, 1)),
                "ice": ((0.04, 0.56, 0.72, 1), (0.94, 1.0, 1.0, 1)),
                "dark": ((0.08, 0.12, 0.18, 1), (1.0, 0.58, 0.58, 1)),
                "pro": ((0.05, 0.48, 0.72, 1), (1, 1, 1, 1)),
            }
            bg, fg = palettes.get(variant, palettes["primary"])
            button.md_bg_color = bg
            button.theme_text_color = "Custom"
            button.text_color = fg
            try:
                button.elevation = 4
            except Exception:
                pass

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
            for button, variant in (
                (getattr(self, "btn_category", None), "primary"),
                (getattr(self, "btn_product", None), "primary"),
                (getattr(self, "btn_calc", None), "primary"),
                (getattr(self, "btn_pdf", None), "ice"),
                (getattr(self, "btn_clear", None), "dark"),
                (getattr(self, "btn_pro", None), "pro"),
            ):
                if button is not None:
                    self._style_app_button(button, variant)

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

            self.bars: Dict[str, Dict] = {}
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
            active = self.theme_cls.primary_color
            inactive = (0.55, 0.57, 0.62, 1)
            if hasattr(self, "valve_btn_mode_k"):
                self.valve_btn_mode_k.md_bg_color = active if k else inactive
                self.valve_btn_mode_w.md_bg_color = inactive if k else active

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
            telemetry.set_screen(name)
            self._animate_bottom_tab(name)
            if name == "valves":
                self._refresh_valve_lock_ui()

        def _animate_bottom_tab(self, name: str):
            """Lekka reakcja zakładki bez kosztownych animacji layoutu."""
            try:
                from kivy.animation import Animation

                item = self.tab_valves if name == "valves" else self.tab_freezing
                Animation.cancel_all(item, "opacity")
                (Animation(opacity=0.78, d=0.08) + Animation(opacity=1.0, d=0.16)).start(item)
                # TODO: Rotate the snowflake icon directly after migrating to a
                # bottom-navigation component that exposes the icon widget.
                # TODO: Animate the valve drawing itself once it moves to a
                # repo-owned SVG/canvas icon instead of the Material icon font.
            except Exception:
                log.debug("Animacja zakładki nie powiodła się", exc_info=True)

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
                self._settings_dialog = MDDialog(
                    title=self._t("settings_title"),
                    type="custom",
                    content_cls=content,
                    buttons=[
                        MDRaisedButton(
                            text=self._t("units_metric"),
                            on_release=lambda *_: self._set_unit_system("metric"),
                        ),
                        MDFlatButton(
                            text=self._t("units_imperial"),
                            disabled=True,
                        ),
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

        def _build_pdf_bytes(self) -> Optional[bytes]:
            """Buduje PDF bez ujawniania źródłowych właściwości produktu."""
            runtime_font = _runtime_font_path()
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

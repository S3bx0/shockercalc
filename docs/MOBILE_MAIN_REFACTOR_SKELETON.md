# Mobile `main.py` Refactor Skeleton

Stan na podstawie roadmapy v1.5.1 i aktualnego kodu z tej gałęzi:
`tpof/mobile/main.py` ma 4959 linii. To jest snapshot roboczy - przed każdym
etapem refaktoru liczby trzeba odświeżyć skryptem/AST, bo plik nadal szybko się
zmienia. Na poziomie modułu istnieje tylko kilka helperów oraz funkcja `main()`,
a wewnątrz `main()` są zdefiniowane klasy UI:

- `FrostBackground`
- `BrandToolbar`
- `FrostChip`
- `StageIconBadge`
- `StageMotionIcon`
- `BottomNavMotionIcon`
- `BottomNavTab`
- `CenterNotice`
- `ShockerCalcApp` z 122 metodami

Cel refaktoru: podzielić mobilny UI na moduły bez zmiany zachowania, bez zmiany
wzorów obliczeniowych i bez zmiany kluczy zapisanych danych.

## Zasada zerowa

Każdy etap musi być mechaniczny i sprawdzalny:

- brak zmian wzorów, stałych domenowych i formatu wyników,
- brak zmian nazw produktów, sortowania katalogu i ścieżek zasobów,
- brak zmian identyfikatorów Billing/AdMob/Firebase,
- brak zmian kluczy `JsonStore`, preferencji i lokalnych plików JSON,
- po każdym etapie: realny import/smoke test, testy Python i dopiero potem AAB.

Jeżeli metoda jest przenoszona, jej ciało powinno zostać przeniesione możliwie
1:1. Zmiana nazw, stylu i większa poprawa kodu to osobny etap po stabilizacji.

## Reguły antycykliczne

- Nowe moduły nie importują runtime'owo `tpof.mobile.main` ani `ShockerCalcApp`.
- Stałe współdzielone trafiają najpierw do liścia `tpof/mobile/constants.py`.
- Typy zależne od aplikacji wolno importować tylko pod `if TYPE_CHECKING`.
- Kontrolery mogą tymczasowo przyjmować `app`, ale nie powinny tworzyć nowych
  zależności przez `from tpof.mobile.app import ShockerCalcApp` w runtime.
- Docelowo każda zakładka posiada swoje widgety i wystawia mały interfejs
  (`build`, `refresh_texts`, `apply_layout`, `calculate`). Nie dokładamy nowych
  "reach-inów" typu `self.app.some_tab_widget`, jeśli da się trzymać referencję
  w kontrolerze zakładki.

## Docelowa struktura

```text
tpof/mobile/
├── main.py                  # cienki launcher
├── app.py                   # ShockerCalcApp: cykl życia + składanie kontrolerów
├── android_bridge.py        # ActivityBridge: Java/Kivy/Android, reklamy, billing, privacy
├── catalog.py               # mobilne helpery katalogu produktów i obrazków
├── constants.py             # liść: BRAND_*, ADMOB_*, PRO_*, STAGE_COLORS
├── hints.py                 # definicje podpowiedzi i przypisanie pól
├── i18n.py                  # teksty, fallback językowy, helper translate()
├── layout.py                # metryki responsywne i skalowanie
├── theme.py                 # paleta, kolory powierzchni, style przycisków
├── validation.py            # parsowanie pól i ostrzeżenia zakresów
├── pdf_export.py            # składanie i zapis PDF
├── widgets/
│   ├── __init__.py
│   ├── frost.py             # FrostBackground
│   ├── toolbar.py           # BrandToolbar, FrostChip
│   ├── stage_icons.py       # StageIconBadge, StageMotionIcon
│   ├── bottom_nav.py        # BottomNavMotionIcon, BottomNavTab
│   ├── menus.py             # wspólny builder dropdownów/menu
│   └── notice.py            # CenterNotice
├── dialogs/
│   ├── __init__.py
│   ├── settings.py          # ustawienia, jednostki, telemetry toggle
│   ├── privacy.py           # UMP/privacy options
│   ├── custom_product.py    # własny produkt PRO
│   └── labor_rates.py       # edycja stawek robocizny PRO
├── tabs/
│   ├── __init__.py
│   ├── freezing.py          # zakładka chłodnicza
│   ├── valves.py            # zakładka zaworów
│   └── labor.py             # zakładka robocizny
└── services/
    ├── __init__.py
    ├── monetization.py      # PRO, rewarded ads, aktywna zakładka reklam
    ├── entitlements_ui.py   # odświeżanie blokad i statusów UI
    └── telemetry_ui.py      # zgody + zdarzenia UI
```

## Docelowy `main.py`

Końcowo `tpof/mobile/main.py` powinien zostać sprowadzony do launchera:

```python
from __future__ import annotations

from tpof.mobile.app import ShockerCalcApp


def main() -> None:
    ShockerCalcApp().run()


if __name__ == "__main__":
    main()
```

W fazie przejściowej `main.py` może re-eksportować przeniesione symbole, jeżeli
testy lub Buildozer oczekują starego importu. Re-eksport ma być tymczasowy.

## Etap 0.5: stałe jako liść importów

To jest warunek konieczny przed wyciąganiem widgetów. Aktualne klasy widgetów
używają `BRAND_ICE` i `BRAND_CYAN`, a te stałe są dziś na poziomie `main.py`.
Gdyby widgety importowały je z `main.py`, a `main.py` importował widgety, powstaje
cykl importów.

### `tpof/mobile/constants.py`

Przenieść:

- `STAGE_COLORS`
- `BRAND_NAVY`
- `BRAND_BLUE`
- `BRAND_CYAN`
- `BRAND_ICE`
- `ADMOB_APP_ID`
- `ADMOB_BANNER_AD_UNIT_ID`
- `ADMOB_BANNER_LABOR_AD_UNIT_ID`
- `ADMOB_TEST_BANNER_AD_UNIT_ID`
- `ADMOB_REWARDED_LABOR_AD_UNIT_ID`
- `PRO_SUBSCRIPTION_PRODUCT_ID`
- `IS_ANDROID`
- `CARD_BG_DARK`
- `CARD_BG_LIGHT`

Przejściowo `main.py` może mieć:

```python
from tpof.mobile.constants import *  # TODO(refactor): remove after app split.
```

Docelowo importy mają być jawne. `import *` jest tylko shimmem, żeby pierwszy
mechaniczny patch był mały.

## Etap 1: czyste helpery

Najpierw przenieść kod, który nie zależy od instancji `ShockerCalcApp`.

### `tpof/mobile/catalog.py`

Przenieść:

- `_mobile_sort_key`
- `_ordered_mobile_categories`
- `_is_mobile_hidden_product`
- `_mobile_product_names`
- `_safe_image_path`

Kontrakt:

- kolejność kategorii zostaje identyczna,
- ukrywanie produktów mobilnych zostaje identyczne,
- fallback obrazka zostaje identyczny,
- desktop nie jest ruszany.

### `tpof/mobile/files.py` albo `pdf_export.py`

Przenieść:

- `_runtime_font_path`
- `_purge_host_arch_fonttools_so`
- `_pdf_output_dir`

Uwaga: `_build_pdf_bytes` i `_export_pdf` zostają na razie w `ShockerCalcApp`,
bo mają dużo zależności od stanu UI. Przenosimy je dopiero w etapie PDF.

### `tpof/mobile/validation.py`

Przenieść później lub w tym etapie, ale bez zmiany komunikatów:

- `_numeric_input_filter`
- `_clear_field_error`
- `_mark_field_error`
- czyste fragmenty parsowania liczb, gdy zostaną odklejone od UI
- czysty wariant `temperature_warning(...)`, jeżeli da się go odseparować od UI

Na start można zostawić `_parse_float`, `_parse_int` i `_parse_required_field`
w `ShockerCalcApp`, bo znakują pola błędów.

Zalecany kierunek:

```python
class FieldErrorController:
    def clear(self, field) -> None: ...
    def mark(self, field, message: str) -> None: ...
```

Zakładki przyjmują taki helper zamiast wołać `self.app._mark_field_error`.

## Etap 2: i18n i teksty

### `tpof/mobile/i18n.py`

Przenieść słowniki i helpery tekstowe:

- wszystkie mapy tekstów PL/EN i przyszłe fallbacki,
- helper `translate(lang, key, **kwargs)`,
- helpery tekstowe niezależne od UI.

Metody do przeniesienia lub uproszczenia:

- `_t` -> wrapper na `translate()`
- `_total_text`
- `_ad_label_text`
- `_status_footer_text`
- `_display_category`

Zachowanie przejściowe:

```python
class ShockerCalcApp(App):
    def _t(self, key: str, **kwargs: object) -> str:
        return translate(self.lang, key, **kwargs)
```

## Etap 3: theme/layout

### `tpof/mobile/theme.py`

Przenieść logikę kolorów i styli:

- `_card_bg`
- `_surface_bg`
- `_bottom_nav_bg`
- `_footer_bg`
- `_ad_slot_bg`
- `_menu_bg_color`
- `_menu_text_color`
- `_style_app_button`

Proponowany kontrakt:

```python
@dataclass(frozen=True)
class MobilePalette:
    dark: bool
    card_bg: tuple[float, float, float, float]
    surface_bg: tuple[float, float, float, float]
    footer_bg: tuple[float, float, float, float]
    bottom_nav_bg: tuple[float, float, float, float]
```

### `tpof/mobile/layout.py`

Przenieść responsywność:

- `_screen_dp`
- `_clamp`
- `_layout_metrics`
- część `_apply_responsive_layout`, ale dopiero po wydzieleniu widgetów.

Pierwszy krok może być bezpieczny: `layout.py` zwraca tylko dataclass
`LayoutMetrics`, a `ShockerCalcApp` dalej aplikuje wartości do istniejących
widżetów.

## Etap 4: widgety wizualne

Ten etap jest mechaniczny i ma wysoką wartość, bo usuwa klasy z wnętrza
`main()`.

### `tpof/mobile/widgets/frost.py`

Przenieść klasę:

- `FrostBackground`

### `tpof/mobile/widgets/toolbar.py`

Przenieść klasy:

- `BrandToolbar`
- `FrostChip`

Przenieść helper:

- `_toolbar_chip_button`

### `tpof/mobile/widgets/stage_icons.py`

Przenieść klasy:

- `StageIconBadge`
- `StageMotionIcon`

### `tpof/mobile/widgets/bottom_nav.py`

Przenieść klasy:

- `BottomNavMotionIcon`
- `BottomNavTab`

### `tpof/mobile/widgets/menus.py`

Przenieść wspólny builder:

- `_menu`

Ten moduł musi importować swoje zależności Kivy samodzielnie. Nie wolno polegać
na importach wykonanych wewnątrz `main()`.

### `tpof/mobile/widgets/notice.py`

Przenieść klasę:

- `CenterNotice`

Zasada:

- klasy widgetów nie mogą importować `ShockerCalcApp`,
- callbacki przyjmują przez konstruktor,
- animacje i canvas zostają 1:1,
- po przeniesieniu `main()` importuje klasy z `tpof.mobile.widgets`,
- każdy plik widgetu ma komplet własnych importów Kivy (`Color`, `Ellipse`,
  `Clock`, `dp` itd.); `compileall` tego nie zweryfikuje.

## Etap 5: Android bridge i monetyzacja

### `tpof/mobile/android_bridge.py`

Utworzyć cienką fasadę:

```python
class ActivityBridge:
    def activity(self): ...
    def show_banner(self, placement: str) -> None: ...
    def set_active_ad_tab(self, tab: str) -> None: ...
    def buy_pro(self) -> None: ...
    def buy_module_valves(self) -> None: ...
    def show_rewarded_ad(self, placement: str) -> None: ...
    def open_privacy_options(self) -> bool: ...
```

Przenieść lub opakować:

- `_android_activity`
- `_set_active_ad_tab`
- `_refresh_ad_slot_height`
- `_buy_valve_module`
- `_offer_reward_ad`
- `_open_ad_privacy_options`

Na pierwszym etapie można zostawić metody w `ShockerCalcApp` jako delegaty do
`self.android`.

### `tpof/mobile/services/monetization.py`

Wykonany pierwszy etap:

- `ProMonetizationController` przejął `_refresh_pro_status`, `_set_pro_status`
  i `_buy_pro`,
- kontroler pobiera z natywnego `BillingService` lokalną cenę subskrypcji,
  stosuje bezpieczny fallback i nie importuje Kivy ani PyJNIus,
- `main.py` zachowuje wyłącznie callback aktualizujący konkretne widżety.

Pozostało przenieść:

- `_credit_pending_reward_tokens`
- `_after_reward_ad`
- `_valve_module_available`
- `_refresh_module_valves_status`
- `_refresh_valve_lock_ui`
- `_after_valve_purchase`

Ten moduł nadal może przyjmować `app` jako właściciela. Dopiero drugi refaktor
może wprowadzić pełny model MVVM/controller.

## Etap 6: dialogi

Dialogi są dobrym następnym krokiem, bo mają zamknięte zakresy.

### `tpof/mobile/dialogs/settings.py`

Przenieść:

- `_close_settings_dialog`
- `_set_unit_system`
- `_open_settings_dialog`

### `tpof/mobile/dialogs/privacy.py`

Przenieść:

- `_refresh_privacy_button`
- `_prompt_telemetry_consent`
- `_set_telemetry_consent`
- `_close_privacy_dialog`
- `_open_privacy_options`
- `_change_telemetry_from_settings`

### `tpof/mobile/dialogs/custom_product.py`

Przenieść:

- `_open_custom_product_dialog`
- `_close_custom_product_dialog`
- `_save_custom_product`

### `tpof/mobile/dialogs/labor_rates.py`

Przenieść:

- `_labor_rate_config`
- `_close_labor_rates_dialog`
- `_labor_rate_text_values`
- `_open_labor_rates_dialog`
- `_mark_labor_rate_errors`
- `_save_labor_rates`
- `_reset_labor_rates`

Przejściowy wzorzec:

```python
class SettingsDialogController:
    def __init__(self, app: "ShockerCalcApp") -> None:
        self.app = app

    def open(self) -> None:
        ...
```

To zachowuje obecne zależności i pozwala przenosić kod bez przepisywania logiki.

## Etap 7: zakładki

Zakładki wydzielać dopiero po widgetach i dialogach.

### `tpof/mobile/tabs/freezing.py`

Klasa:

```python
class FreezingTabController:
    def __init__(self, app: "ShockerCalcApp") -> None: ...
    def build(self): ...
    def refresh_texts(self) -> None: ...
    def apply_layout(self, metrics) -> None: ...
    def calculate(self) -> None: ...
    def reset_inputs(self) -> None: ...
```

Przenieść metody:

- `_hint_field_items` albo podpiąć wynik z `tpof.mobile.hints`
- `_build_product_card`
- `_build_params_card`
- `_build_action_button`
- `_build_results_card`
- `_add_stage_row`
- `_clear_main_validation`
- `_temperature_warning`
- `_validate_temperature_input`
- `_show_product_image`
- `_open_category_menu`
- `_pick_category`
- `_open_product_menu`
- `_add_product_search_item`
- `_add_product_search_heading`
- `_refresh_product_search_results`
- `_close_product_dialog`
- `_on_locked_product`
- `_pick_product`
- `_toggle_mass_unit`
- `_set_mass_unit`
- `_reset_inputs`
- `_calculate`
- `_render_results`

Właścicielstwo widgetów:

- `FreezingTabController` buduje i przechowuje własne pola, etykiety, paski
  wyników i przyciski.
- `ShockerCalcApp` wywołuje metody kontrolera, ale nie powinien trzymać nowych
  bezpośrednich referencji do widgetów zakładki.

### `tpof/mobile/tabs/valves.py`

Klasa:

```python
class ValvesTabController:
    def build(self): ...
    def calculate(self) -> None: ...
    def refresh_lock_ui(self) -> None: ...
```

Przenieść metody:

- `_build_valve_tab`
- `_set_valve_mode`
- `_open_valve_type_menu`
- `_pick_valve_type`
- `_calculate_valves`
- `_render_valve_results`
- `_clear_valve_validation`

### `tpof/mobile/tabs/labor.py`

Klasa:

```python
class LaborTabController:
    def build(self): ...
    def calculate(self) -> None: ...
    def invalidate_results(self) -> None: ...
```

Przenieść metody:

- `_build_labor_tab`
- `_set_labor_highways`
- `_toggle_labor_highways`
- `_set_labor_additional_enabled`
- `_toggle_labor_additional`
- `_clear_labor_validation`
- `_parse_labor_int`
- `_parse_labor_decimal`
- `_format_labor_money`
- `_labor_travel_mode_text`
- `_render_labor_results`
- `_invalidate_labor_results`
- `_calculate_labor`

## Etap 8: `ShockerCalcApp` jako composition root

Po wydzieleniu zakładek `ShockerCalcApp` powinien trzymać tylko:

- cykl życia Kivy (`build`),
- globalny stan aplikacji (`lang`, `dark`, `unit_system`, entitlements),
- instancje kontrolerów,
- przełączanie zakładek,
- odświeżanie globalnych powierzchni,
- integracje wysokiego poziomu z Android bridge.

Metody, które mogą zostać w `app.py`:

- `build`
- `_sync_root_background`
- `_build_toolbar`
- `_build_bottom_nav`
- `_build_footer`
- `_build_ad_slot`
- `_on_tab_switch`
- `_show_tab`
- `_set_tab_visibility`
- `_raise_tab_widget`
- `_animate_bottom_tab`
- `_toggle_language`
- `_toggle_hints`
- `_apply_hints`
- `_toggle_theme`
- `_show_error`
- `_refresh_texts` jako agregator delegujący do kontrolerów
- `_apply_responsive_layout` jako agregator delegujący do kontrolerów
- `_sync_theme_surfaces` jako agregator delegujący do kontrolerów

## Etap 9: testy po refaktorze

Minimalny zestaw po każdym etapie:

```powershell
python -m pytest
python -m pytest tests/test_mobile_smoke.py
```

Dla etapów wydzielających czysty kod dodać 1-2 testy charakteryzujące:

- `catalog.py`: kolejność kategorii, ukrywanie produktów mobilnych,
- `i18n.py`: fallback języka i brakujące klucze,
- `theme.py`: paleta jasna/ciemna,
- `validation.py`: parsowanie liczb, błędy pól, ostrzeżenia temperatur.

Sama kompilacja:

```powershell
python -m compileall tpof\mobile
```

jest tylko dodatkowym sanity checkiem. Nie wykrywa brakujących importów Kivy,
cykli importów ani błędów instancjacji. Bramką po refaktorze widgetów jest
minimum `tests/test_mobile_smoke.py`, bo faktycznie importuje mobilną warstwę.

Dla etapów Android/monetyzacja:

- GitHub Actions AAB musi przejść na zielono,
- ręcznie sprawdzić start aplikacji,
- ręcznie sprawdzić przełączanie zakładek,
- ręcznie sprawdzić zakup PRO/test purchase,
- ręcznie sprawdzić reklamy i brak zasłaniania stopki.

## Etap 10: odłożony layout `.kv`

Ten refaktor celowo zostawia imperatywne budowanie UI w Pythonie, żeby nie
zmienić zachowania. Po stabilizacji podziału modułów warto dodać osobny etap:

- przeniesienie statycznych układów kart do plików `.kv`,
- zostawienie logiki callbacków w kontrolerach,
- porównanie zrzutów ekranu przed/po dla trybu jasnego i ciemnego.

Nie mieszać migracji `.kv` z wyciąganiem klas i zakładek.

## Pierwszy bezpieczny patch refaktoru

Zakres pierwszego patcha powinien być mały, ale musi zaczynać się od stałych:

1. `constants.py`:
   - przenieść `BRAND_*`, `STAGE_COLORS`, `CARD_BG_*`, `ADMOB_*`, `PRO_*`,
     `IS_ANDROID`,
   - w `main.py` zostawić tymczasowy shim importu.
2. `widgets/*`:
   - przenieść tylko widgety:
     - `FrostBackground`
     - `BrandToolbar`
     - `FrostChip`
     - `StageIconBadge`
     - `StageMotionIcon`
     - `BottomNavMotionIcon`
     - `BottomNavTab`
     - `CenterNotice`
   - każdy moduł dostaje własne importy Kivy,
   - widgety importują stałe z `tpof.mobile.constants`, nigdy z `main.py`.
3. W `main()` zastąpić lokalne definicje importami z `tpof.mobile.widgets`.
4. Nie przenosić jeszcze `ShockerCalcApp`.
5. Bramki:
   - `python -m pytest tests/test_mobile_smoke.py`
   - `python -m pytest`
   - zielony AAB.

To daje największy spadek ryzyka przy najmniejszej zmianie zachowania: klasy
przestają być redefiniowane przy każdym wywołaniu `main()`, ale cała logika
aplikacji nadal zostaje w jednym miejscu.

## Inwentarz metod do przypisania

Metody, które łatwo zostawić jako "resztki" w God-klasie, mają jawnego
właściciela:

| Metoda | Docelowy właściciel |
| --- | --- |
| `_clear_field_error` | `tpof.mobile.validation.FieldErrorController` |
| `_mark_field_error` | `tpof.mobile.validation.FieldErrorController` |
| `_clear_main_validation` | `tpof.mobile.tabs.freezing.FreezingTabController` |
| `_temperature_warning` | `tpof.mobile.validation` jako pure helper albo `tabs.freezing` jako wrapper |
| `_validate_temperature_input` | `tpof.mobile.tabs.freezing.FreezingTabController` |
| `_hint_field_items` | `tpof.mobile.hints` |
| `_menu` | `tpof.mobile.widgets.menus` |
| `_toolbar_chip_button` | `tpof.mobile.widgets.toolbar` |
| `_build_pdf_bytes` | `tpof.mobile.pdf_export` po odklejeniu od UI |
| `_export_pdf` | `tpof.mobile.pdf_export` po odklejeniu od Android bridge |

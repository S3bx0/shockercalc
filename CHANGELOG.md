# Changelog

Wszystkie istotne zmiany w projekcie **Refrigeration Calc** (`pl.smilczarek.refrigerationcalc`).
Format na podstawie [Keep a Changelog](https://keepachangelog.com/),
wersjonowanie wg [SemVer](https://semver.org/).

## [1.2.0] — 2026-06-09

### Dodane — płatny moduł zaworów (monetyzacja)

- **Gating modułu `module_valves`**: zakładka zaworów jest jednorazowo płatna.
  Dostęp przez: trial (1 dzień, wszystkie moduły), trwały zakup `module_valves`
  albo obejrzenie reklamy rewarded = 1 przeliczenie (token, dzienny limit 8).
  PRO (brak reklam) **nie** odblokowuje modułu — kupowany niezależnie.
- **`entitlements.try_unlock_module_with_token()`** — jednorazowe odblokowanie
  modułu tokenem (token zużywany, moduł nie jest nadawany na stałe). +3 testy
  (suita: 104 testy).
- **Java Billing** (`RefrigerationCalcActivity`): drugi produkt INAPP
  `module_valves` równolegle do `pro_no_ads` — `launchModulePurchase()`,
  `isModuleValvesOwned()`, query/handle/acknowledge/ownership-sync. Gdy produkt
  nie jest jeszcze aktywny w Play Console, zakup pokazuje „niedostępny", a ścieżka
  z reklamą nadal działa.
- **UI zakładki zaworów**: karta blokady z przyciskami „Kup moduł na stałe"
  i „Obejrzyj reklamę (1 przeliczenie)"; synchronizacja własności z warstwą
  Android; lokalizacja PL/EN nowych komunikatów.

## [1.1.0] — 2026-06-09

### Dodane — druga zakładka: zawory dekompresyjne

- **`tpof/core/valves.py`** — czysta logika doboru zaworów dekompresyjnych
  (port z desktopowego repo): `calculate_decompression_valves()` + `ValveResults`,
  słownik `ZAWORY` (Maxi Elebar 4300 l/min, EVO-VERTICAL 1430 l/min), stała `K=3.66`,
  limity bezpieczeństwa i pełna walidacja wejść. Bez pośrednich zaokrągleń.
- **`tests/test_valves.py`** — 22 testy (oba typy zaworów, walidacja, `KeyError`,
  niemutowalność wyniku). Cała suita: 101 testów.
- **Dolna nawigacja** (`MDBottomNavigation`) w stylu Danfoss Ref Tools: zakładki
  **Chłodnicze** (dotychczasowy kalkulator) i **Zawory** (nowy kalkulator).
- Kalkulator zaworów: wybór typu, objętość komory, temperatury przed/po dekompresji,
  współczynnik częstości; wynik = liczba zaworów, ΔT, wymagany przepływ Q.
- Lokalizacja PL/EN nowych etykiet i zakładek.

### Dodane — reklamy per zakładka (AdMob)

- Dedykowane jednostki reklamowe dla zakładki zaworów: baner `/6303778370`,
  rewarded `/1060900411`.
- **`RefrigerationCalcActivity.setActiveAdTab()`** — przy zmianie zakładki baner
  i reklama rewarded przeładowują się na jednostkę przypisaną do aktywnej zakładki
  (`getBannerAdUnitId()` / `getRewardedAdUnitId()` zależne od `activeAdTab`).
- Strona Pythona podpina przełączanie zakładek (`on_switch_tabs`) do mostka Android.
## [Unreleased] — 2026-05-30

### Mobile (Android — Etap A: parytet UI)

#### Dodane
- **`tpof/mobile/main.py`** — pełne UI KivyMD zamiast wcześniejszego stuba:
  - `MDTopAppBar` z przełącznikiem motywu Dark/Light (ikony `weather-night` / `weather-sunny`).
  - Karta **Produkt**: kaskadowy wybór `Kategoria → Produkt` (osobne `MDDropdownMenu`),
    miniaturka produktu (`AsyncImage` z `assets/images/`).
  - Karta **Parametry**: pola masy / T_pocz / T_konc / czasu, przełącznik jednostek
    masy `kg ↔ t` (`MDSwitch`) automatycznie skalujący wartość.
  - Karta **Wynik**: nagłówek z sumą mocy, 3 paski postępu (`MDProgressBar`) dla
    etapów Schładzanie / Zamrożenie / Domrażanie wraz z wartością kW i % udziału,
    siatka właściwości produktu (`c₁`, `c₂`, `L₁`, woda, T_zam z oznaczeniem
    „szacowane" gdy dane brakują).
  - Przyciski **Oblicz** (`MDRaisedButton` z ikoną) i **Wyczyść** (`MDFlatButton`).
  - `Snackbar` dla błędów walidacji zamiast surowych wyjątków na ekranie.
- **`tests/test_mobile_smoke.py`** — 5 testów smoke nie wymagających KivyMD:
  - import `tpof.mobile.main`, istnienie zasobów (`DATA_PATH`, `IMAGES_DIR`),
  - `_safe_image_path` dla istniejących/nieistniejących produktów,
  - poprawne `SystemExit` gdy KivyMD niedostępne.
- **Helper `_safe_image_path()`** — szuka obrazu produktu w `.webp/.png/.jpg/.jpeg`.

#### Zmienione
- Importy KivyMD/Kivy wyizolowane wewnątrz `main()` — dzięki temu pakiet
  `tpof.mobile` można importować na czystym Pythonie (CI, testy, desktop bez Kivy).
- Liczba testów: **47 → 52** (100% pass).

#### Wciąż brakuje do gotowego APK (Etap B + C)
- Pierwszy build Buildozerem w WSL2/Linux (nigdy nie był uruchomiony).
- Testy na fizycznym urządzeniu, podpis release.

### Mobile (Android — Etap A.2: CI + branding + PDF)

#### Dodane
- **`.github/workflows/android.yml`** — pełny workflow buildów APK na GitHub Actions:
  - Ubuntu 22.04 + JDK 17 + Python 3.11 + Buildozer 1.5.0 + Cython 0.29.36.
  - Cache `~/.buildozer`, `~/.gradle` i `.buildozer/` (przyspiesza kolejne buildy ~5×).
  - Uruchamia testy `pytest` przed buildem.
  - Artefakt `shockercalc-debug-apk` (30 dni retencji).
  - Trigger: push do main/master, tag `v*`, PR, oraz manualnie (`workflow_dispatch`).
- **`assets/icon.png`** (512×512) — ikona z płatkiem śniegu, gradient granat → niebieski.
- **`assets/presplash.png`** (1280×1920) — splash screen z logo i napisem
  „Shocker Calc — Obliczenia chłodnicze" (DejaVu Sans).
- **Eksport PDF z mobilnego UI** — nowy przycisk `PDF` w karcie akcji:
  - Używa istniejącego `tpof.core.pdf_report.build_pdf` (pełna zgodność z desktopem).
  - Helper `_pdf_output_dir()` — na Androidzie zapisuje do `/sdcard/Download`,
    z fallbackiem do `ANDROID_PRIVATE`; na desktopie do `cwd`.
  - Nazwa pliku: `ShockerCalc_<Produkt>_<YYYYMMDD_HHMMSS>.pdf`.
  - Snackbar potwierdza ścieżkę zapisu lub raportuje błąd.
- **`tests/test_mobile_smoke.py`** — +1 test (`test_pdf_output_dir_na_desktopie_zwraca_cwd`).

#### Zmienione
- **`buildozer.spec`** — odkomentowane `icon.filename`, `presplash.filename`,
  dodane `android.presplash_color = #1E3C6E` (granatowe tło splasha).
- **`tpof/mobile/main.py`** — karta akcji `Oblicz | PDF | Wyczyść` (3 przyciski
  zamiast 2), `_last_results` zapamiętywane dla eksportu PDF.
- Liczba testów: **52 → 53** (100% pass).

---

## [Unreleased] — 2026-05-29

### Architektura

#### Dodane
- **Pakiet `tpof/`** — nowa, modułowa struktura projektu:
  - `tpof/core/` — czysta logika domenowa (modele, obliczenia, walidacja, I/O, PDF).
  - `tpof/desktop/` — warstwa UI Tkinter + ttkbootstrap (`FreezingCalculatorApp`).
  - `tpof/mobile/` — szkielet pod port KivyMD / Buildozer (Android).
- **`tpof/core/models.py`** — `Product`, `FreezingInputs`, `FreezingResults` jako `@dataclass(frozen=True)` z typami opcjonalnymi.
- **`tpof/core/calculations.py`** — `calculate_freezing()` jako jedyne źródło prawdy dla matematyki.
- **`tpof/core/validators.py`** — `is_positive_number`, `is_valid_temperature`, `parse_number`.
- **`tpof/core/data_loader.py`** — `load_products`, `find_product`, `list_categories`, `list_products`.
- **`tpof/core/formatters.py`** — `format_results_text` (legacy, używany przez PDF).
- **`tpof/core/pdf_report.py`** — generowanie PDF (`build_pdf`, `save_pdf`).
- **`tests/`** — pełen zestaw testów (47 testów, 100% pass).
- **`run.py`** — uruchomienie aplikacji desktop bez instalacji pakietu.
- **`pyproject.toml`** — konfiguracja pakietu (deps, pytest, build).
- **`buildozer.spec`** — szkielet dla przyszłej kompilacji Androida.
- **`archive/backup_pre_refactor_2026-05-29.zip`** — backup stanu sprzed refaktoringu.

#### Usunięte
- Stare pliki na poziomie głównym (po zarchiwizowaniu):
  - `gui.py`, `logika.py`, `obliczenia.py`, `Domrozenie.py`, `cli.py`, `controller.py`, `pdf_generator.py`, `models.py` — przeniesione/przepisane do `tpof/`.
- `project/src/` — eksperymentalny katalog zastąpiony przez `tpof/`.

### UI (desktop)

#### Dodane
- **Modernizacja ttkbootstrap** — przejście z surowego `tk`/`ttk` na ttkbootstrap z motywem `superhero`.
- **Selektor motywów** w nagłówku (`Combobox`) — 10 motywów (5 ciemnych, 5 jasnych).
- **Toggle Dark/Light** — szybki przycisk `☾ Dark / ☀ Light` przełączający między `superhero` ↔ `flatly`.
- **Selektor jednostki masy** kg/t (`Combobox`) obok pola masy — automatyczna konwersja w `_read_inputs`.
- **Floodgauge dla każdego etapu** (Schładzanie / Zamrożenie / Domrażanie) z animacją od poprzedniej do nowej wartości i etykietą `"X.X kW (Y%)"`.
- **Meter** (gauge analogowy) dla mocy całkowitej z auto-skalowaniem (skala podnoszona gdy wynik > 80%).
- **Treeview** z 4 kolumnami (Etap / Q [MJ] / P [kW] / Udział [%]) z:
  - zebra (`stage` / `stage_alt`),
  - wierszem **SUMA** wyróżnionym kolorem `primary` z białą czcionką,
  - ikonami etapów (❄ 🧊 ⛄) i symbolem `Σ` przy SUMA,
  - wysokością wiersza 38 px i czcionką 11 pt.
- **Panel "Parametry produktu"** (po prawej w Wynikach) — Labelframe z dynamicznie generowanymi parami `etykieta : wartość` (c₁, c₂, T_zam, woda, L, skład %).
- **Karta "Produkt"** — zdjęcie produktu, nazwa w bocie info, 3 odznaki (Badge): kategoria / T_zam / H₂O%.
- **Nagłówek aplikacji** — logo (72 px), tytuł 26 pt `primary`, podtytuł kursywą `info`, separator pod nagłówkiem.
- **Pasek statusu** z kolorową kropką ● (zielona/niebieska/żółta/czerwona) zmieniającą się wg poziomu (`success/info/warn/error`) + autor w czerwonym kursywie.
- **Tooltips** (`_add_tooltip`) — żółte dymki nad polami formularza, opisujące co wpisać.
- **Placeholder text** w `Entry` (szary tekst znikający przy focus).
- **`_animate_meter` / `_animate_gauge`** — płynne przejścia wskaźników (20 kroków po 20 ms).
- **`_apply_global_style`** + per-widget `style.configure(tree_style_name, rowheight=38)` — wymusza wysokość wiersza Treeview niezależnie od motywu ttkbootstrap.

#### Zmienione
- Layout główny: `Header → Separator → TopPanels (Form | Product | Meter) → Results (Floodgauges + Treeview + Props)` zamiast monolitycznego pola Text.
- Paddingi: `outer=16`, `top_panels gap=12`, `card padding=10-16`.
- Typografia: jednolity Segoe UI (H1 26, H2 11-12, body 10-11).

#### Usunięte
- **Pole `Text` z wynikami** — zastąpione tabelą Treeview.
- **Funkcje obsługi tagów Text** — `_tag_pattern`, `_tag_full_line_containing`, `_configure_text_tags`, `_apply_text_theme_colors`.
- **Chipy etapów** (proste Label-pigułki) — zastąpione przez `Floodgauge`.

### Logika / matematyka

#### Dodane
- **`_estimate_T_zam(woda_procent)`** — szacowanie punktu zamarzania ze wzoru `T_zam ≈ -0.6 · (100/woda%)` gdy produkt nie ma `T_zam`:
  - 100 % wody → −0.6 °C
  - 50 % → −1.2 °C
  - 20 % → −3.0 °C
  - brak wody → fallback −0.6 °C
- **Walidacja `czas_h > 0`** w `calculate_freezing` — rzuca `ValueError` z czytelnym komunikatem zamiast cichego zwrotu `P=0`.

#### Zmienione
- `calculate_freezing` — gdy `product.T_zam is None`, używa `_estimate_T_zam(product.wodaprocent)` zamiast hardkodowanego `0.0`. Flaga `T_zam_szacunkowy=True` nadal jest ustawiana.

#### Naprawione
- Konwersja masy `t → kg` (×1000) w `_read_inputs` w zależności od `mass_unit_var`.
- `Meter.configure(amountused=...)` — poprawna nazwa atrybutu (`amountusedvar`, nie `amountusedvariable`).
- Floodgauge `mask="{}"` usunięty — blokował wyświetlanie pełnego tekstu `"X.X kW (Y%)"`.
- Treeview `rowheight` — `style.configure("Treeview", ...)` nie działał, bo ttkbootstrap nadaje style typu `success.Treeview`; teraz odczytujemy `cget("style")` i konfigurujemy właściwy styl + reapply przez `after(100)`.
- Sieroty `return card` w `_render_props` (resztka po starym kodzie) — usunięte (powodowały `NameError`).
- Wartości produktu — poprawione mapowanie polskich kluczy JSON na ASCII (`T_zam`, `wodaprocent`, `L1` zamiast `punkt_zamarzania`, `wilgotnosc`).

### Testy

#### Dodane (47 testów, było 26)
- **`TestEdgeCases`** (7 testów): `T_konc=T_zam`, `T_pocz=T_zam`, `T_pocz=T_konc`, brak L1, brak c2, wszystkie dane `None`, masa = 0.
- **`TestSkalowalnoscIProporcje`** (3): podwójna masa → 2× energia, podwójny czas → ½ mocy, suma etapów = `Q_total`.
- **`TestJednostekIKonwersji`** (2): ręczne sprawdzenie `kJ → kW` na próbce 1 kg / 1 h, 1 h vs 24 h.
- **`test_parametryzowane_realne_przypadki`** (2): pełne cykle ze znanymi wynikami liczbowymi.
- **`TestProperties`** (2): nieujemność wszystkich `Q`, monotoniczność względem ΔT.
- **`TestEstimateTzam`** (5): brak wody → fallback, 100 % → −0.6, 50 % → −1.2, monotoniczność.

#### Zmienione
- `test_produkt_bez_punktu_zamarzania_uzywa_zera` → `test_produkt_bez_punktu_zamarzania_szacuje_z_wody` (dostosowane do `_estimate_T_zam`).
- `test_zerowy_czas_daje_zerowa_moc` → `test_zerowy_czas_rzuca_wyjatek` (`pytest.raises(ValueError)`).
- `test_ujemny_czas_traktowany_jak_zero` → `test_ujemny_czas_rzuca_wyjatek`.
- `test_wszystkie_dane_zerowe_lub_None` — sprawdza teraz fallback −0.6 zamiast 0.0.

### Build / packaging
- **`requirements.txt`** + **`requirements-dev.txt`** — rozdzielenie zależności runtime/dev (pytest, pytest-cov).
- **`pyproject.toml`** — `pytest` skonfigurowany (`testpaths`, `rootdir`).
- **`.gitignore`** — Python build artifacts, venv, IDE.
- **`buildozer.spec`** — szkielet dla `pl.smilczarek.refrigerationcalc` (Android).

---

## Pre-refactor (stan zarchiwizowany)
- Monolityczny `gui.py` (Tkinter, ~1500 linii) z logiką, walidacją i I/O wymieszanymi z UI.
- Brak testów.
- Brak struktury pakietu.
- Brak motywów i animacji.
- Brak rozdzielenia core / desktop / mobile.

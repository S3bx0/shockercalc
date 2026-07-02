# Refrigeration Calc

Kalkulator zapotrzebowania chłodu dla procesu zamrażania produktów spożywczych,
doboru zaworów dekompresyjnych oraz szybkiej wyceny robocizny.

> **⚠️ Oprogramowanie własnościowe.** Ten kod jest udostępniony publicznie
> wyłącznie do wglądu. **Nie wolno** go kopiować, używać, modyfikować ani
> rozpowszechniać bez pisemnej zgody autora. Szczegóły w pliku
> [`LICENSE`](LICENSE).

## Struktura projektu

```
tpof/                  # pakiet źródłowy
├── core/              # czysta logika (działa też na Androidzie)
│   ├── models.py
│   ├── validators.py
│   ├── calculations.py
│   ├── data_loader.py
│   ├── formatters.py
│   └── pdf_report.py
├── labor/             # czysta logika kalkulatora robocizny
│   ├── models.py
│   ├── config.py
│   ├── validation.py
│   └── cost_calculator.py
└── desktop/           # warstwa Tkinter + ttkbootstrap
    ├── app.py
    └── paths.py
└── mobile/            # warstwa mobilna (KivyMD)
    ├── main.py        # UI + integracja AdMob/Billing/Firebase
    ├── entitlements.py# trial, freemium, tokeny za reklamy, moduły płatne
    ├── telemetry.py   # bezpieczny most Analytics/Crashlytics/Remote Config
    ├── user_data.py   # podpowiedzi i lokalne produkty użytkownika
    └── paths.py

assets/                # zasoby aplikacji
├── Table3.json        # baza produktów
├── fonts/             # DejaVuSans.ttf
├── images/            # zdjęcia produktów (.webp)
└── watermark.png      # znak wodny do PDF

tests/                 # testy pytest dla `tpof.core`
archive/               # backupy przed-refaktorowe
```

## Uruchomienie (desktop)

```powershell
# Instalacja zależności (jednorazowo)
python -m pip install -r requirements-desktop.txt

# Start aplikacji
python run.py
# albo
python -m tpof.desktop
```

## Testy

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest
```

## Android / AdMob / PRO

Build mobilny używa natywnego banera AdMob przez `RefrigerationCalcActivity`.
W `debug` ładowane są testowe reklamy Google, a w `release` właściwe jednostki
— **osobne dla każdej zakładki** (rozdzielone raporty):

| Zakładka | Baner | Reklama z nagrodą |
|----------|-------|-------------------|
| Chłodnicze (zamrażanie) | `…/5599859341` | `…/1548239161` |
| Zawory dekompresyjne    | `…/6303778370` | `…/1060900411` |
| Robocizna               | domyślny baner chłodniczy | domyślna ścieżka główna |

App ID: `ca-app-pub-7481054652344026~2716191071`. Jednostka reklamowa jest
przełączana w warstwie natywnej (`setActiveAdTab`) przy zmianie zakładki.

### Model dostępu (freemium)

Logika uprawnień jest w `tpof/mobile/entitlements.py` (w pełni testowana,
niezależna od UI):

- **Trial 1 dzień** — od pierwszego uruchomienia pełen dostęp do wszystkich
  produktów, kart i modułów płatnych.
- **Po triallu (wersja darmowa)** — 1 produkt z każdej listy za darmo;
  pozostałe są płatne (PRO) lub odblokowywane pojedynczo za reklamę.
- **Reklama z nagrodą = token** — obejrzenie pełnej reklamy daje 1 token =
  1 bezpłatne przeliczenie zablokowanego produktu / modułu. Limit
  **8 reklam/dobę** (przesuwne okno 24 h); cooldown konfigurowalny
  (`REWARD_AD_COOLDOWN_S`).

### PRO (`refrigeration_pro`)

Miesięczna subskrypcja Google Play Billing:

- typ produktu: subscription / auto-renewing,
- product ID w Play Console: `refrigeration_pro`,
- base plan ID: `monthly-499`,
- efekt aktywnej subskrypcji: usuwa reklamy, odblokowuje pełną listę produktów,
  eksport PDF oraz moduły PRO, w tym zawory dekompresyjne,
- cena: ustawiana w Google Play Console, nie w kodzie aplikacji.

Legacy zakup jednorazowy `pro_no_ads` nadal jest rozpoznawany jako PRO, aby
nie odbierać dostępu użytkownikom/testom ze starego modelu.

### Moduł zaworów dekompresyjnych (`module_valves`)

Druga zakładka (dobór zaworów) jest **płatnym modułem jednorazowym**:

- product ID w Play Console: `module_valves` (one-time / non-consumable),
- dostęp: trial → za darmo; aktywne PRO → dostęp; trwały zakup
  `module_valves` → na stałe; reklama z nagrodą → 1 przeliczenie (token),
- gdy produkt nie jest jeszcze aktywny w Play Console, zakup pokazuje
  „niedostępny”, a ścieżka z reklamą działa normalnie.

### Zgoda na reklamy (Google UMP / RODO)

Przed inicjalizacją SDK reklam aplikacja uruchamia przepływ zgody **Google
User Messaging Platform**. Dla użytkowników z EOG/UK pokazywany jest formularz
zgody, a SDK reklam startuje dopiero gdy `canRequestAds()` zwróci `true`.
Przycisk „tarcza" w pasku górnym pozwala później zmienić zgodę
(`showPrivacyOptionsForm`). Komunikat o zgodzie trzeba jeszcze skonfigurować
w panelu **AdMob → Prywatność i komunikaty** oraz uzupełnić deklaracje danych
w Play Console.

### Firebase (dobrowolna telemetria)

Build obsługuje Google Analytics for Firebase, Crashlytics i Remote Config.
Integracja jest aktywowana tylko wtedy, gdy CI otrzyma poprawny
`google-services.json`, a samo zbieranie danych jest domyślnie wyłączone do
czasu zgody użytkownika. Zdarzenia opisują użycie funkcji; nie zawierają
wartości obliczeń, nazw własnych produktów ani treści PDF.

Workflow debug może opcjonalnie przekazać APK testerom przez Firebase App
Distribution. Pełna konfiguracja sekretów, Remote Config i zmian wymaganych w
Play Console jest opisana w [`docs/FIREBASE_SETUP.md`](docs/FIREBASE_SETUP.md).

### Warstwa wizualna Android

Przy zimnym starcie system pokazuje zatwierdzony emblemat Refrigeration Calc,
a następnie natywne intro Java trwające 4,6 sekundy. W szerokim pierścieniu
22 płatki lecą promieniście z różnymi prędkościami i rosną wraz z pozornym
zbliżaniem się do użytkownika. Trzy wolniejsze komety obiegają emblemat po
niewidocznych, przesuniętych orbitach 8-kątnych. Główny interfejs zachowuje
lekki gradient i wolno poruszające się refleksy. Animacje nie wymagają Lottie
ani dodatkowych zależności i respektują systemowe ograniczenie ruchu.

### Artefakty diagnostyczne Google Play

Release workflow generuje dodatkowy artefakt `play-console-diagnostics`.
Zawiera on:

- `native-debug-symbols.zip`, jeśli Android Gradle Plugin wygeneruje osobny
  plik symboli natywnych albo jeśli workflow znajdzie nieobcięte biblioteki
  `.so` i zbuduje ZIP ręcznie,
- `mapping.txt`, jeśli w przyszłości włączymy R8/ProGuard,
- `README.txt` z informacją, co zostało znalezione w danym buildzie.

Dla App Bundle ustawiamy `debugSymbolLevel = SYMBOL_TABLE`, więc symbole
natywne powinny być dołączone bezpośrednio do AAB. R8/ProGuard jest obecnie
wyłączony dla release p4a/Kivy, dlatego brak `mapping.txt` jest oczekiwany.

## Plany rozwoju

- Po testach wizualnych rozwazyc wariant splash Lottie przygotowany w After
  Effects: skladanie platka z krysztalkow i bardziej organiczny slad mrozu.
  Warunki wdrozenia: maks. 2 s, maly plik animacji, brak regresji czasu startu
  oraz zachowanie obecnej animacji natywnej jako lekkiego fallbacku.
- Kafelkowy ekran glowny dla kolejnych kalkulatorow i modulow.
- Kolejna płatna karta funkcyjna: izolacja (`module_insulation`) jako
  niezależny produkt IAP.
- Dalsze testy zamknięte i publikacja w Google Play.

## Licencja

Copyright © 2026 Sebastian Milczarek. Wszelkie prawa zastrzeżone.

To repozytorium jest **własnościowe** i udostępnione publicznie wyłącznie
w celach poglądowych (portfolio / wgląd w kod). Bez uprzedniej pisemnej zgody
autora **zabronione** jest m.in.: kopiowanie, uruchamianie, modyfikowanie,
rozpowszechnianie, publikowanie, tworzenie utworów zależnych oraz komercyjne
lub niekomercyjne wykorzystanie kodu, zasobów i danych (w tym `Table3.json`,
grafik i ikon). Pełny tekst w pliku [`LICENSE`](LICENSE).

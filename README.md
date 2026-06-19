# Refrigeration Calc

Kalkulator zapotrzebowania chłodu dla procesu zamrażania produktów spożywczych
oraz doboru zaworów dekompresyjnych.

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
└── desktop/           # warstwa Tkinter + ttkbootstrap
    ├── app.py
    └── paths.py
└── mobile/            # warstwa mobilna (KivyMD)
    ├── main.py        # UI (dolna nawigacja) + integracja AdMob/Billing
    ├── entitlements.py# trial, freemium, tokeny za reklamy, moduły płatne
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

## Plany rozwoju

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

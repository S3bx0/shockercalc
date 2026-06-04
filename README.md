# Refrigeration Calc

Kalkulator zapotrzebowania chłodu dla procesu zamrażania produktów spożywczych.

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
    ├── main.py        # UI + integracja AdMob/Billing
    ├── entitlements.py# trial, freemium, tokeny za reklamy, karty
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

Build mobilny używa natywnego banera AdMob przez `ShockerCalcActivity`.
W `debug` ładowane są testowe reklamy Google, a w `release` właściwe jednostki:

- baner: `ca-app-pub-7481054652344026/5599859341`
- reklama z nagrodą (rewarded): `ca-app-pub-7481054652344026/1548239161`

### Model dostępu (freemium)

Logika uprawnień jest w `tpof/mobile/entitlements.py` (w pełni testowana,
niezależna od UI):

- **Trial 7 dni** — od pierwszego uruchomienia pełen dostęp do wszystkich
  produktów i kart.
- **Po triallu (wersja darmowa)** — 1 produkt z każdej listy za darmo;
  pozostałe są płatne (PRO) lub odblokowywane pojedynczo za reklamę.
- **Reklama z nagrodą = token** — obejrzenie pełnej reklamy daje 1 token =
  1 bezpłatne przeliczenie zablokowanego produktu. Limit **8 reklam/dobę**
  (przesuwne okno 24 h); cooldown konfigurowalny (`REWARD_AD_COOLDOWN_S`).

### PRO (`pro_no_ads`)

Jednorazowy zakup Google Play Billing:

- typ produktu: one-time product / non-consumable,
- product ID w Play Console: `pro_no_ads`,
- efekt po zakupie: usuwa reklamy i odblokowuje **pełną listę produktów w karcie
  rdzeniowej (zamrażanie)**,
- cena: ustawiana w Google Play Console, nie w kodzie aplikacji.

> PRO świadomie **nie** odblokowuje przyszłych płatnych kart funkcyjnych
> (np. dobór zaworów) — każda nowa karta jest osobnym produktem
> (`module_valves`, `module_insulation`, …), kupowanym niezależnie.

### Zgoda na reklamy (Google UMP / RODO)

Przed inicjalizacją SDK reklam aplikacja uruchamia przepływ zgody **Google
User Messaging Platform**. Dla użytkowników z EOG/UK pokazywany jest formularz
zgody, a SDK reklam startuje dopiero gdy `canRequestAds()` zwróci `true`.
Przycisk „tarcza" w pasku górnym pozwala później zmienić zgodę
(`showPrivacyOptionsForm`). Komunikat o zgodzie trzeba jeszcze skonfigurować
w panelu **AdMob → Prywatność i komunikaty** oraz uzupełnić deklaracje danych
w Play Console.

## Plany rozwoju

- **Etap 4**: warstwa mobilna (KivyMD) + szablon `buildozer.spec` do publikacji w Google Play.
- Kolejne płatne karty funkcyjne (zawory, izolacja) jako niezależne produkty IAP.

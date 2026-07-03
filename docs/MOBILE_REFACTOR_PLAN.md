# Mobile Refactor Plan

Stan na 2026-07-03: `tpof/mobile/main.py` ma ponad 4400 linii i zawiera jednocześnie motyw, lokalizację, widżety, dialogi, zakładki, integracje Androida oraz logikę ekranową. Dalsze zmiany warto robić etapami, bez zmiany wzorów obliczeniowych.

## Cel

- Zmniejszyć ryzyko regresji w UI mobilnym.
- Ułatwić testowanie pojedynczych funkcji: zakładki chłodniczej, zaworów i robocizny.
- Oddzielić integracje Androida od kodu widżetów Kivy.

## Proponowany podział

1. `tpof/mobile/theme.py`
   - Kolory, gradienty, style przycisków, ustawienia jasnego/ciemnego motywu.

2. `tpof/mobile/i18n.py`
   - Słowniki tekstów, fallback językowy, helper `_t`.

3. `tpof/mobile/android_bridge.py`
   - Wywołania aktywności Androida: reklamy, billing, telemetry opt-in, aktywna zakładka reklam.

4. `tpof/mobile/widgets/`
   - `BrandToolbar`, `FrostBackground`, `BottomNavTab`, `StageMotionIcon`, `CenterNotice`.

5. `tpof/mobile/dialogs/`
   - Ustawienia, produkt użytkownika, edycja stawek robocizny, PRO/subskrypcje.

6. `tpof/mobile/tabs/freezing.py`
   - Budowa i obsługa zakładki chłodniczej.

7. `tpof/mobile/tabs/valves.py`
   - Budowa i obsługa zakładki zaworów.

8. `tpof/mobile/tabs/labor.py`
   - Budowa i obsługa zakładki robocizny, bez zmiany `tpof.labor`.

## Kolejność prac

1. Wydzielić czyste stałe i helpery bez zmiany zachowania.
2. Wydzielić widżety wizualne, zostawiając `ShockerCalcApp` jako orkiestrator.
3. Wydzielić dialogi jeden po drugim, zaczynając od najnowszego edytora stawek robocizny.
4. Wydzielić zakładki dopiero po zamrożeniu obecnej wersji UI na testach.
5. Dodać testy smoke dla każdego wydzielonego modułu.

## Zasady bezpieczeństwa

- Nie przenosić wzorów obliczeniowych do UI.
- Każdy etap powinien kończyć się zielonymi testami i działającym AAB.
- Nie mieszać dużego refaktoru z funkcją biznesową w jednej wersji.
- Jeśli trzeba zmienić strukturę danych preferencji, dodać migrację i test odczytu starego pliku.

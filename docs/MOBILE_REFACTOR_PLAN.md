# Mobile Refactor Plan

Stan na 2026-07-28: `tpof/mobile/main.py` ma 13 linii i jest gotowym, cienkim
launcherem. `ShockerCalcApp` i cykl życia Kivy znajdują się w
`tpof/mobile/app.py` (374 linie, z czego `build()` zajmuje 174), a składanie
stanu i kontrolerów w niezależnym od frameworka
`tpof/mobile/app_controllers.py` (355 linii). Wszystkie trzy zakładki, powłoka aplikacji,
motyw, responsywny układ, dialogi oraz wspólna obsługa
podpowiedzi, walidacji, klawiatury, lokalizacji, reklam nagradzanych, tokenów i
dostępu do modułu zaworów są już wydzielone. PyJNIus, natywna Activity oraz
widoczność przycisku prywatności także mają osobne, testowalne kontrolery.
Generowanie, zapis i udostępnianie PDF obsługuje `PdfExportController`.
W `app.py` pozostaje głównie składanie widoku, cykl życia oraz krótka
orkiestracja usług aplikacji.

Konkretny szkielet podziału plików, mapowanie metod i kolejność bezpiecznej migracji są opisane w `docs/MOBILE_MAIN_REFACTOR_SKELETON.md`.

## Cel

- Zmniejszyć ryzyko regresji w UI mobilnym.
- Ułatwić testowanie pojedynczych funkcji: zakładki chłodniczej, zaworów i robocizny.
- Oddzielić integracje Androida od kodu widżetów Kivy.

## Proponowany podział

1. `tpof/mobile/theme.py`
   - Kolory, gradienty, style przycisków, ustawienia jasnego/ciemnego motywu.

2. `tpof/mobile/i18n.py`
   - Słowniki tekstów, fallback językowy, helper `_t`.

3. `tpof/mobile/android_bridge.py` — wykonane
   - Leniwy dostęp do natywnej Activity przez PyJNIus.
   - Aktywna karta reklam, wysokość banera, opcje UMP i udostępnianie plików.
   - Bezpieczne zachowanie poza Androidem i osobne testy kontraktu.

4. `tpof/mobile/widgets/`
   - `BrandToolbar`, `FrostBackground`, `BottomNavTab`, `StageMotionIcon`, `CenterNotice`.

5. `tpof/mobile/dialogs/`
   - Ustawienia, produkt użytkownika, edycja stawek robocizny, PRO/subskrypcje.

6. `tpof/mobile/tabs/freezing.py`
   - Budowa i obsługa zakładki chłodniczej.

7. `tpof/mobile/tabs/valves.py` — wykonane
   - Budowa widoku, stan trybu danych i typu zaworu, walidacja, obliczenia,
     wynik oraz prezentacja blokady dostępu.
   - Polityka uprawnień, zakup i reklama nagradzana są w osobnym kontrolerze.

8. `tpof/mobile/tabs/labor.py` — wykonane
   - Budowa i obsługa zakładki robocizny, bez zmiany `tpof.labor`.

9. `tpof/mobile/services/monetization.py`
   - Stan PRO, lokalna cena Google Play i asynchroniczne odświeżanie zakupu.
   - Wykonane; kontroler nie importuje Kivy ani PyJNIus.

10. `tpof/mobile/services/rewarded_access.py` — wykonane
    - Reklamy rewarded, transfer tokenów z Androida, dostęp jednorazowy do
      zablokowanych produktów i obliczeń zaworów.
    - Synchronizacja i zakup `module_valves` oraz stan karty blokady.
    - Kontroler nie importuje Kivy ani PyJNIus i ma osobne testy zachowania.

11. `tpof/mobile/form_interactions.py` — wykonane
    - Stan podpowiedzi, wspólna prezentacja błędów pól oraz przewijanie
      aktywnego pola nad klawiaturę.
    - Moduł nie importuje Kivy i ma osobne testy zachowania.

12. `tpof/mobile/localization.py` — wykonane
   - Stan języka, tłumaczenie kategorii oraz synchronizacja tekstów powłoki,
     zakładek, formularzy i modułu PRO.
   - Moduł nie importuje Kivy i ma osobne testy przełączania PL/EN.

13. `tpof/mobile/pdf_export.py` — wykonane
   - Budowanie pełnego i mobilnego PDF, zapis w prywatnym katalogu oraz
     udostępnianie przez Android bridge.
   - Kontroler nie importuje Kivy i ma osobne testy sukcesu, fallbacków i błędów.

14. `tpof/mobile/app.py` — wykonane
   - `ShockerCalcApp`, cykl życia Kivy i składanie kontrolerów są poza launcherem.
   - `tpof/mobile/main.py` zachowuje leniwy import KivyMD i tylko uruchamia klasę.
   - Osobny test kontraktowy pilnuje granicy `main.py` → `app.py`.

15. `tpof/mobile/app_controllers.py` — wykonane
   - Składanie stanu oraz 17 kontrolerów zostało usunięte z `build()`.
   - Moduł nie importuje Kivy, KivyMD ani PyJNIus; zależności runtime otrzymuje
     jawnie w `compose_controllers()`.
   - Osobny test kontraktowy pilnuje granicy
     `app.py` → `app_controllers.py` oraz maksymalnego rozmiaru `app.py`.

## Kolejność prac

1. Wydzielić współdzielone stałe do `tpof/mobile/constants.py`, żeby uniknąć cykli importów przy przenoszeniu widgetów.
2. Wydzielić czyste helpery bez zmiany zachowania.
3. Wydzielić widżety wizualne, zostawiając `ShockerCalcApp` jako orkiestrator — wykonane.
4. Wydzielić dialogi jeden po drugim, zaczynając od najnowszego edytora stawek robocizny.
5. Wydzielić zakładki dopiero po zamrożeniu obecnej wersji UI na testach.
6. Dodać testy smoke i testy charakteryzujące dla każdego wydzielonego modułu
   — wykonywane na każdym checkpointcie; bieżący zestaw obejmuje 376 testów.

## Zasady bezpieczeństwa

- Nie przenosić wzorów obliczeniowych do UI.
- Każdy etap powinien kończyć się zielonymi testami i działającym AAB.
- Po zmianach importów nie ufać samemu `compileall`; wymagany jest co najmniej `tests/test_mobile_smoke.py`.
- Nie mieszać dużego refaktoru z funkcją biznesową w jednej wersji.
- Jeśli trzeba zmienić strukturę danych preferencji, dodać migrację i test odczytu starego pliku.

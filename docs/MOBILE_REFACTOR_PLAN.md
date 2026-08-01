# Mobile Refactor Plan

Stan na 2026-08-01: `tpof/mobile/main.py` ma 13 linii i jest gotowym, cienkim
launcherem. `ShockerCalcApp` i cykl życia Kivy znajdują się w
`tpof/mobile/app.py` (385 linii), a składanie
stanu i kontrolerów w niezależnym od frameworka
`tpof/mobile/app_controllers.py` (371 linii). Wszystkie trzy zakładki, powłoka aplikacji,
motyw, responsywny układ, dialogi oraz wspólna obsługa
podpowiedzi, walidacji, klawiatury, lokalizacji, reklam nagradzanych, tokenów i
dostępu do modułu zaworów są już wydzielone. PyJNIus, natywna Activity oraz
widoczność przycisku prywatności także mają osobne, testowalne kontrolery.
Generowanie, zapis i udostępnianie PDF obsługuje `PdfExportController`.
Konstrukcja widoku chłodniczego jest już w `tabs/freezing_view.py` (491 linii),
wybór i historia produktów w `tabs/freezing_products.py` (342 linie),
obliczenia w `tabs/freezing_workflow.py`, wyniki w
`tabs/freezing_results.py`, a motyw i responsywność w
`tabs/freezing_presentation.py`. `tabs/freezing.py` zmniejszył się z 1270 do
160 linii bez zmiany zachowania.
Widok zakładki robocizny jest w `tabs/labor_view.py` (330 linii), workflow
obliczeń w `tabs/labor_workflow.py` (236 linii), prezentacja wyników i wykresu
w `tabs/labor_results.py` (396 linii), a `tabs/labor.py` po trzech cięciach
zmniejszył się z 1112 do 257 linii.
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

6. `tpof/mobile/tabs/freezing.py` — wykonane
   - Kontroler zachowuje inicjalizację, stan jednostki masy i lokalizację.
   - Widok, produkty, workflow, wyniki oraz prezentacja mają osobne moduły.

7. `tpof/mobile/tabs/valves.py` — wykonane
   - Budowa widoku, stan trybu danych i typu zaworu, walidacja, obliczenia,
     wynik oraz prezentacja blokady dostępu.
   - Polityka uprawnień, zakup i reklama nagradzana są w osobnym kontrolerze.

8. `tpof/mobile/tabs/labor.py` — wykonane
   - Obsługa zakładki robocizny bez zmiany `tpof.labor`.
   - Budowa widoku jest już w osobnym `tabs/labor_view.py`.
   - Parsowanie, walidacja i obliczenia są w `tabs/labor_workflow.py`.

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

16. `tpof/mobile/tabs/freezing_view.py` — wykonane
   - Zawiera `FreezingTabView`, `FreezingStageView` i mechaniczne składanie
     drzewa widżetów Kivy.
   - `FreezingTabController` zachowuje kompatybilny import typów oraz metodę
     `build()` przez mały mixin kompozycji.
   - Test kontraktowy pilnuje granicy, braku importu zwrotnego i maksymalnego
     rozmiaru kontrolera.

17. `tpof/mobile/tabs/freezing_products.py` — wykonane
   - Zawiera wybór kategorii i produktu, dialog wyszukiwania, ostatnie wybory,
     blokady Free/PRO oraz prezentację zdjęcia produktu.
   - Dwanaście metod przeniesiono bez zmian semantycznych; dalszy etap
     wydzielił także walidację i uruchamianie obliczeń.
   - Test kontraktowy pilnuje jednokierunkowej zależności oraz maksymalnego
     rozmiaru `tabs/freezing.py`.

18. Dialog wyszukiwania produktów i klawiatura Androida — wykonane
   - Na czas dialogu wyłączane jest globalne przesuwanie `below_target`, które
     przenosiło całą powierzchnię Kivy do aktywnego pola wyszukiwania.
   - Android `Activity` uwzględnia w głównym layoucie tylko paski systemowe
     i wycięcie ekranu. Nie dodaje drugi raz wysokości IME do dolnego paddingu;
     pozycjonowanie względem klawiatury pozostaje po stronie Kivy.
   - Przy zamknięciu pole traci fokus, a poprzedni tryb okna jest przywracany.
   - Testy regresyjne pilnują przejść stanu oraz braku podwójnego insetu IME.

19. `tpof/mobile/tabs/freezing_workflow.py` — wykonane
   - Zawiera parsowanie pól, walidację temperatur, przygotowanie
     `FreezingInputs` oraz orkiestrację `calculate()`.
   - Wzory pozostają w `tpof/core`, a kontroler zachowuje renderowanie
     `FreezingResults`; zależności biegną tylko od workflow do core i widoku.
   - `tabs/freezing.py` zmniejszył się z 549 do 341 linii.

20. `tpof/mobile/tabs/freezing_results.py` — wykonane
   - Zawiera formatowanie sumy mocy, prezentację trzech etapów obliczenia
     oraz pełne zerowanie pól i widoku wyników.
   - Nie importuje kalkulatora ani `FreezingInputs`; otrzymuje wyłącznie
     gotowe `FreezingResults`.
   - `tabs/freezing.py` zmniejszył się z 341 do 289 linii.

21. `tpof/mobile/tabs/freezing_presentation.py` — wykonane
   - Zawiera synchronizację motywu przycisków i zastosowanie kompletu
     responsywnych metryk do widoku zakładki.
   - Lokalizacja oraz stan jednostki masy pozostają w koordynatorze.
   - `tabs/freezing.py` zmniejszył się z 289 do 160 linii.

22. `tpof/mobile/tabs/labor_view.py` — wykonane
   - Zawiera `LaborTabView`, klucze etykiet wyników i mechaniczne składanie
     drzewa widgetów Kivy.
   - `LaborTabController.build()` pozostaje kompatybilne przez mixin
     kompozycji.
   - `tabs/labor.py` zmniejszył się z 1112 do 798 linii.

23. `tpof/mobile/tabs/labor_workflow.py` — wykonane
   - Zawiera parsowanie pól, walidację, przygotowanie `CalculationInput`,
     konfigurację stawek oraz orkiestrację `calculate()`.
   - Wzory pozostają w `tpof/labor`, a kontroler zachowuje zgodne publiczne
     API przez mixin workflow.
   - `tabs/labor.py` zmniejszył się z 798 do 604 linii.

24. `tpof/mobile/tabs/labor_results.py` — wykonane
   - Zawiera prezentację wyniku, podsumowania kosztów, legendę i dialog
     interaktywnego wykresu robocizny.
   - Koordynator `tabs/labor.py` ma 257 linii i nie rysuje już wykresu.
   - Osobne testy pilnują danych wykresu, widoczności i granicy importów.

## Kolejność prac

1. Wydzielić współdzielone stałe do `tpof/mobile/constants.py`, żeby uniknąć cykli importów przy przenoszeniu widgetów.
2. Wydzielić czyste helpery bez zmiany zachowania.
3. Wydzielić widżety wizualne, zostawiając `ShockerCalcApp` jako orkiestrator — wykonane.
4. Wydzielić dialogi jeden po drugim, zaczynając od najnowszego edytora stawek robocizny.
5. Wydzielić zakładki dopiero po zamrożeniu obecnej wersji UI na testach.
6. Dodać testy smoke i testy charakteryzujące dla każdego wydzielonego modułu
   — wykonywane na każdym checkpointcie; bieżący zestaw obejmuje 403 testy.
7. Wydzielić wybór, wyszukiwanie i historię produktów z `tabs/freezing.py`
   bez przenoszenia walidacji i obliczeń — wykonane.
8. Wydzielić walidację pól i uruchamianie obliczeń z
   `tabs/freezing.py`, pozostawiając wzory w `tpof/core` i zachowując
   dotychczasową prezentację wyników — wykonane.
9. Wydzielić prezentację i zerowanie wyników, pozostawiając
   `FreezingTabController` jako koordynator stanu, lokalizacji i motywu
   — wykonane.
10. Wydzielić responsywny układ i synchronizację motywu do osobnego modułu,
    pozostawiając kontrolerowi inicjalizację i lokalizację — wykonane.
11. Wydzielić granicę widoku robocizny do `tabs/labor_view.py` bez zmiany
    zachowania — wykonane.
12. Wydzielić parsowanie, walidację i `calculate()` do
    `tabs/labor_workflow.py`, bez przenoszenia wzorów z `tpof/labor`
    — wykonane.
13. Wydzielić prezentację wyników i wykres do `tabs/labor_results.py`,
    pozostawiając workflow i wzory bez zmian — wykonane.
14. Przed dalszym refaktorem zamknąć bramkę publikacyjną z
    `docs/GOOGLE_PLAY_RELEASE_QUALITY_AUDIT_2026-08-01.md`: ABI, backup,
    inicjalizacja Firebase po zgodzie, zielone CI i nowy AAB.
15. Następne cięcie po stabilnym checkpointcie: rozdzielić mechaniczne widoki
    `labor_results.py` od modelu/prezentera danych wykresu, a następnie
    analogicznie rozdzielić widok i workflow zaworów bez dokładania logiki do
    `app.py`.

## Zasady bezpieczeństwa

- Nie przenosić wzorów obliczeniowych do UI.
- Każdy etap powinien kończyć się zielonymi testami i działającym AAB.
- Po zmianach importów nie ufać samemu `compileall`; wymagany jest co najmniej `tests/test_mobile_smoke.py`.
- Nie mieszać dużego refaktoru z funkcją biznesową w jednej wersji.
- Jeśli trzeba zmienić strukturę danych preferencji, dodać migrację i test odczytu starego pliku.

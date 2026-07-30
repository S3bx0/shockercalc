# Refrigeration Calc roadmap

## Nadrzędny kierunek: dekompozycja monolitu

Każda kolejna funkcja powinna zmniejszać odpowiedzialność tymczasowych powłok
`tpof/mobile/main.py` i `RefrigerationCalcActivity.java`, zamiast dopisywać do
nich następne bloki logiki. Nowe moduły muszą mieć jawne API, własne testy i
nie mogą importować klasy aplikacji.

Kolejność migracji:

1. Wydzielać istniejące dialogi do `tpof/mobile/dialogs/` i zakładki do
   `tpof/mobile/tabs/`, pozostawiając w `main.py` tylko składanie zależności.
2. Wydzielić integracje reklam, Billing i Firebase z Activity do osobnych klas
   Java; publiczne metody Activity mają być wyłącznie cienką fasadą dla pyjnius.
3. Przenosić stan i operacje asynchroniczne do `tpof/mobile/services/`, bez
   bezpośredniej zależności od widgetów.
4. Dopiero na tych granicach dodawać funkcje z backlogu platformowego, np.
   In-App Review, elastyczne In-App Updates i App Shortcuts.

Wdrożone cięcia:

- kontroler dialogu ustawień w `tpof/mobile/dialogs/settings.py`,
- kontroler dialogu stawek w `tpof/mobile/dialogs/labor_rates.py`,
- `LaborTabController` w `tpof/mobile/tabs/labor.py`, który posiada stan
  przełączników, walutę kosztu dodatkowego, walidację, obliczenia, wyniki oraz
  wykres; budowa drzewa Kivy i `LaborTabView` są już w `labor_view.py`, a
  `main.py` nie przechowuje aliasów jego widgetów,
- `ValvesTabController` w `tpof/mobile/tabs/valves.py`, który przejął budowę
  karty, tryb kubatura/wymiary, wybór typu, walidację, obliczenia i prezentację
  wyników; polityka PRO, zakup i reklama nagradzana pozostają w orkiestratorze,
- natywne serwisy `FirebaseTelemetryService`, `PrivacyConsentService`,
  `AdvertisingService`, `BillingService` i `FileShareService`, pozostawiające
  w Activity fasadę dla PyJNIus, składanie zależności i cykl życia.
- niezależny od Kivy i PyJNIus `ProMonetizationController`, który przejął
  lokalną cenę Google Play, stan przycisku PRO i harmonogram odświeżania zakupu
  z `main.py`,
- `FreezingTabController` rozłożony na osobne moduły budowy widoku, wyboru
  produktów, obliczeń, wyników oraz prezentacji motywu i responsywnego układu;
  koordynator ma 160 linii zamiast pierwotnych 1270.

Następny naturalny krok to wydzielenie parsowania, walidacji i `calculate()`
z `tpof/mobile/tabs/labor.py` do `labor_workflow.py`, bez przenoszenia wzorów
z `tpof/labor`. Następnie osobną granicę powinny otrzymać wykres i prezentacja
wyników. Natywna bramka serwisów została zamknięta; In-App Review, elastyczne
In-App Updates i App Shortcuts nie powinny ponownie rozbudowywać Activity.

## Future: WebView chart engine

Future chart engine option:
Consider WebView-based charts using Chart.js or Apache ECharts if the app
requires more advanced interactive charts, tooltips, legends, export options,
or richer animations. This should be evaluated only after the Kivy Canvas
implementation is stable. WebView charts may increase app complexity, APK/AAB
size, startup cost, and Android compatibility risk. Keep Kivy Canvas as the
default lightweight chart engine for now.

- TODO: Evaluate angle-based donut segment selection after device-level UX and
  accessibility tests of the lightweight Kivy Canvas chart.

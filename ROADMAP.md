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
  przełączników, walutę kosztu dodatkowego, wyniki oraz wykres; budowa drzewa
  Kivy i `LaborTabView` są w `labor_view.py`, a parsowanie, walidacja i
  orkiestracja `calculate()` w `labor_workflow.py`. Prezentacja wyników,
  legendy i dialogu wykresu znajduje się w `labor_results.py`; koordynator ma
  około 260 linii zamiast 604. `main.py` nie przechowuje aliasów jego widgetów,
- `ValvesTabController` w `tpof/mobile/tabs/valves.py`, który przejął budowę
  karty, tryb kubatura/wymiary, wybór typu, walidację, obliczenia i prezentację
  wyników; polityka PRO, zakup i reklama nagradzana pozostają w orkiestratorze,
- natywne serwisy `FirebaseTelemetryService`, `PrivacyConsentService`,
  `AdvertisingService`, `BillingService`, `FileShareService` i
  `FeedbackService`, pozostawiające w Activity fasadę dla PyJNIus, składanie
  zależności i cykl życia,
- niezależny od Kivy i PyJNIus `ProMonetizationController`, który przejął
  lokalną cenę Google Play, stan przycisku PRO i harmonogram odświeżania zakupu
  z `main.py`,
- niezależny od Kivy i PyJNIus `UserFeedbackController`, który tworzy
  edytowalny, lokalizowany szkic wiadomości z wersją i językiem aplikacji.
  Użytkownik sam decyduje o treści i wysłaniu; aplikacja nie zbiera
  diagnostyki ani nie wysyła danych w tle,
- `FreezingTabController` rozłożony na osobne moduły budowy widoku, wyboru
  produktów, obliczeń, wyników oraz prezentacji motywu i responsywnego układu;
  koordynator ma 160 linii zamiast pierwotnych 1270.

Następny krok publikacyjny to zebrać rzeczywiste opinie przez wdrożoną akcję
„Wyślij opinię / Zgłoś błąd” oraz prywatny kanał Google Play, zapisać decyzje w
`docs/CLOSED_TEST_FEEDBACK_LOG.md` i wydać co najmniej jedną uzasadnioną
aktualizację testową. Następny krok platformowy po ustabilizowaniu testu to
In-App Review jako osobny kontroler Python i osobny serwis Java. Elastyczne
In-App Updates i App Shortcuts również nie powinny ponownie rozbudowywać
Activity.

## Priorytet publikacyjny: ponowny test zamknięty Google Play

Google Play odrzucił pierwszy wniosek o dostęp do wersji produkcyjnej i wskazał
jako możliwe przyczyny niewystarczające zaangażowanie testerów oraz brak
udokumentowanego procesu zbierania i wdrażania opinii. Przed ponownym wnioskiem:

- 30 lipca 2026 o 16:25 Google odrzucił pierwszy wniosek i w Konsoli Play
  rozpoczął wymaganie kolejnych 14 dni liczonych od daty sprawdzenia; wersja
  96 (1.5.11) jest dostępna w aktywnej ścieżce Alpha od 30 lipca, 19:59,
- nie składać wniosku przed odblokowaniem przycisku przez Konsolę Play;
  operacyjnie najbezpieczniej sprawdzić możliwość ponownego zgłoszenia
  14 sierpnia 2026, zamiast zakładać samodzielnie wcześniejszą godzinę końca,

- utrzymać co najmniej 12 realnych testerów zapisanych do testu zamkniętego
  nieprzerwanie przez pełne 14 dni; lista Alpha zawiera obecnie 18 testerów,
  więc nie usuwać listy, nie wstrzymywać ścieżki i zachować zapas,
- przekazać testerom krótkie scenariusze obejmujące kalkulator chłodniczy,
  zawory, robociznę, ustawienia, zmianę języka i motywu oraz eksport PDF,
- upewnić się, że testerzy instalują i aktualizują aplikację przez link testu
  zamkniętego Google Play oraz faktycznie korzystają z jej funkcji,
- wdrożono w ustawieniach akcję „Wyślij opinię / Zgłoś błąd”, która tworzy
  edytowalną wiadomość z wersją i językiem aplikacji, bez zbierania danych w
  tle; należy udostępnić ją testerom w kolejnej kompilacji,
- równolegle zbierać prywatne opinie w Google Play i prowadzić rejestr:
  data, obszar aplikacji, zgłoszenie, decyzja i wersja zawierająca poprawkę,
- 30 lipca sekcja „Opinie z testów” nie zawierała jeszcze żadnego wpisu;
  przed kolejnym wnioskiem zebrać rzeczywiste opinie i odpowiedzieć testerom,
- opublikować w teście zamkniętym co najmniej jedną uzasadnioną aktualizację
  wynikającą z rzeczywistych opinii testerów i zachować jej informacje o wersji,
- sprawdzić raport przed opublikowaniem, Android Vitals, awarie i ANR oraz
  naprawić istotne problemy przed kolejnym zgłoszeniem,
- zaktualizować formularz „Bezpieczeństwo danych”: obecna deklaracja wskazuje
  tylko identyfikatory urządzenia, choć wydanie zawiera aktywną konfigurację
  AdMob oraz dobrowolne Analytics, Crashlytics i Remote Config; szczegóły
  audytu są w `docs/GOOGLE_PLAY_CLOSED_TEST_AUDIT_2026-07-30.md`,
- ponownie wnioskować dopiero po zakończeniu okresu wskazanego w Konsoli Play
  i opisać wyłącznie rzeczywiste zaangażowanie, feedback oraz wdrożone zmiany.

Funkcja opinii została wydzielona do `UserFeedbackController` z własnymi
testami. `main.py` nie zawiera jej logiki, a `RefrigerationCalcActivity.java`
udostępnia wyłącznie cienki delegat do `FeedbackService`.

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

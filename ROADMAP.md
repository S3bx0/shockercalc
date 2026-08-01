# Refrigeration Calc roadmap

## Bramka jakości po superaudycie 2026-08-01

Pełny raport znajduje się w
[`docs/GOOGLE_PLAY_RELEASE_QUALITY_AUDIT_2026-08-01.md`](docs/GOOGLE_PLAY_RELEASE_QUALITY_AUDIT_2026-08-01.md).
Decyzja dla obecnego stanu to **NO-GO dla kolejnego AAB**, dopóki nie zostaną
zamknięte poniższe zadania P0:

1. usunąć z AAB niekompletne ABI `armeabi-v7a`, `x86` i `x86_64` albo
   dostarczyć dla nich pełny runtime; wygenerowany przez Bundletool pakiet
   `x86_64` obecnie instaluje się i natychmiast ulega awarii;
2. ustawić jawną politykę Android Auto Backup i nie przywracać lokalnych flag
   PRO, tokenów ani identyfikatorów SDK;
3. opóźnić inicjalizację Firebase do zgody i potwierdzić pomiarem brak
   transmisji Firebase przed zgodą;
4. naprawić powtarzalne przepełnienie dysku podczas odtwarzania cache Buildozera
   w wymaganym checku PR #13 (przebiegi `30690032852` i `30692299604`),
   ograniczyć lub usunąć ciężki cache, dodać raport wolnego miejsca, uzyskać
   zielone CI i zbudować nowy podpisany AAB z aktualnego `HEAD`;
5. zweryfikować nowy AAB: podpis, wersję, 16 KB, kompletność ABI, split APK,
   uruchomienie ARM oraz API 35/36;
6. zmergować PR do `main`, zaktualizować opis repozytorium i publiczną politykę
   prywatności przed tagiem i wysłaniem do Alpha.

Stan realizacji 2026-08-01:

- **P0.1 ABI — APK potwierdzony, AAB oczekuje:** przebieg `30693177259`
  zbudował APK zawierający wyłącznie `arm64-v8a` i komplet 15 bibliotek;
  hook p4a dodaje filtr Gradle, a osobny walidator blokuje APK/AAB zawierające
  nieobsługiwane ABI lub pozbawione bibliotek Python/SDL;
- **P0.2 Auto Backup — manifest APK potwierdzony:** ustawiono
  `android.allow_backup = False`, zachowując odtwarzanie PRO przez Play Billing;
  przebieg `30693969034` oraz niezależny odczyt binarnego manifestu potwierdziły
  `android:allowBackup=false`;
- **P0.3 Firebase lazy opt-in — test przed zgodą zaliczony:**
  usunięto `FirebaseInitProvider`, konfiguracja jest wykrywana bez SDK,
  `FirebaseApp` startuje dopiero po zgodzie, a cofnięcie zgody czyści dane
  lokalne i zleca usunięcie FID. APK z przebiegu `30696006335` nie zawiera
  `FirebaseInitProvider` ani `MobileAdsInitProvider`. Test świeżej instalacji
  potwierdził brak `FirebaseApp` oraz plików Installations, Crashlytics i
  Sessions. Żądanie do wspólnego `firebaselogging.googleapis.com` zostało
  jednoznacznie przypisane przez bazę DataTransport do zdarzeń
  `PLAY_BILLING_LIBRARY`, nie Firebase. Do pełnego zamknięcia pozostaje test
  włączenia i cofnięcia zgody na fizycznym urządzeniu ARM;
- **P0.4 miejsce na runnerze — potwierdzone dla PR/APK:** przebieg
  `30693177259` przeszedł po usunięciu projektowego cache `.buildozer`
  (~1,9 GB skompresowane); cache globalny działa wyłącznie w trybie restore,
  a workflow raportuje miejsce przed i po jego przywróceniu;
- **P0.5 bramka AAB — wdrażana:** kontrola wyrównania bibliotek została
  wydzielona do testowanego narzędzia i zmieniona z ostrzeżenia na twardy błąd;
  workflow sprawdza też podpis AAB i wykonuje `bundletool validate` narzędziem
  przypiętym wersją oraz SHA-256;
- stare artefakty 1.5.12 są celowo odrzucane przez nową bramkę; zadania można
  oznaczyć jako zamknięte dopiero po zielonym buildzie i inspekcji nowego AAB.

Następna warstwa P1 to: dostępność TalkBack, cele dotykowe 48 dp, kontrast,
skalowanie czcionek, landscape/duże ekrany, audyt zależności w CI, progi
pokrycia oraz bazowe pomiary wydajności release na ARM. Te prace mają być
wydzielane do osobnych modułów i narzędzi; nie wolno ponownie rozbudować
`app.py` ani `RefrigerationCalcActivity.java`.

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

Po zamknięciu bramki P0 następny krok publikacyjny to zebrać rzeczywiste opinie
przez wdrożoną akcję „Wyślij opinię / Zgłoś błąd” oraz prywatny kanał Google
Play, zapisać decyzje w `docs/CLOSED_TEST_FEEDBACK_LOG.md` i wydać co najmniej
jedną uzasadnioną aktualizację testową. Następny krok platformowy po
ustabilizowaniu testu to In-App Review jako osobny kontroler Python i osobny
serwis Java. Elastyczne In-App Updates również nie powinny ponownie
rozbudowywać Activity. App Shortcuts zrealizowano przez osobny serwis Java,
mostek i kontroler Python.

Raport testowy został rozszerzony o wersjonowany, ustrukturyzowany szablon 2.
Proces operacyjny, scenariusze i wiadomość dla testerów znajdują się w
`docs/CLOSED_TESTER_GUIDE.md`. Sam formularz nie zastępuje prawdziwego użycia:
przed ponownym wnioskiem trzeba zebrać zgłoszenia, odpowiedzieć na nie,
opublikować uzasadnioną poprawkę i potwierdzić ją w ponownym teście.

## Priorytet publikacyjny: ponowny test zamknięty Google Play

Google Play odrzucił pierwszy wniosek o dostęp do wersji produkcyjnej i wskazał
jako możliwe przyczyny niewystarczające zaangażowanie testerów oraz brak
udokumentowanego procesu zbierania i wdrażania opinii. Przed ponownym wnioskiem:

- 30 lipca 2026 o 16:25 Google odrzucił pierwszy wniosek i w Konsoli Play
  rozpoczął wymaganie kolejnych 14 dni liczonych od daty sprawdzenia; wersja
  96 (1.5.11) była dostępna w aktywnej ścieżce Alpha od 30 lipca, 19:59, a
  później przesłano wersję 98 (1.5.12) do sprawdzenia; przed kolejnym AAB
  potwierdzić w Konsoli, która wersja jest obecnie dostępna testerom,
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
- 30 lipca sekcja „Opinie z testów” zawierała jedną starszą, ogólną ocenę 5/5
  „Super”, bez szczegółów możliwych do wdrożenia; przed kolejnym wnioskiem
  zebrać nowe, konkretne opinie i odpowiedzieć testerom,
- opublikować w teście zamkniętym co najmniej jedną uzasadnioną aktualizację
  wynikającą z rzeczywistych opinii testerów i zachować jej informacje o wersji,
- sprawdzić raport przed opublikowaniem, Android Vitals, awarie i ANR oraz
  naprawić istotne problemy przed kolejnym zgłoszeniem,
- formularz „Bezpieczeństwo danych” został rozszerzony 30 lipca o sześć typów
  danych, ale po zmianie inicjalizacji Firebase i polityki backupu trzeba go
  ponownie porównać z rzeczywistym ruchem sieciowym; szczegóły są w
  `docs/GOOGLE_PLAY_CLOSED_TEST_AUDIT_2026-07-30.md` i nowym superaudycie,
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

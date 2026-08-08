# Refrigeration Calc roadmap

## Ścieżka krytyczna: ponowny test zamknięty Google Play

Odrzucenie dostępu produkcyjnego jest obecnie problemem procesu testowego, nie
brakiem kolejnej funkcji. Prace P1 i dalsza dekompozycja mogą być wykonywane w
tle, ale nie mogą opóźniać ani zastępować rzeczywistego zaangażowania testerów,
zbierania opinii i wydania poprawki wynikającej z opinii.

Kolejność release train:

1. naprawić uszkodzone maski alfa ilustracji bananów i awokado, przeskanować
   pozostałe grafiki produktów, zabezpieczyć higienę repozytorium, uzyskać
   zielone checki i scalić bieżącą gałąź do `main`;
2. utworzyć checkpoint/tag na `main`, zbudować podpisany AAB z tego commita i
   wykonać krótki smoke na fizycznym ARM oraz API 35/36;
3. opublikować ten sam AAB na aktywnej ścieżce testu zamkniętego i potwierdzić,
   że testerzy widzą właściwy numer wersji;
4. utrzymać co najmniej 12 realnych testerów zapisanych nieprzerwanie przez 14
   dni i rozłożyć rzeczywiste scenariusze użycia na cały okres;
5. zbierać konkretne opinie w Google Play i przez formularz aplikacji,
   odpowiadać na nie oraz prowadzić zanonimizowany rejestr decyzji;
6. w trakcie testu wydać co najmniej jedną widoczną poprawkę wynikającą z
   prawdziwej opinii i uzyskać jej ponowny test;
7. dopiero po potwierdzeniu Vitals, raportu przed opublikowaniem i dowodów
   procesu ponownie złożyć wniosek o dostęp produkcyjny.

In-App Review może zostać dodany w trakcie testu jako dodatkowy kanał prywatnej
opinii, ale wyświetlenie okna podlega decyzji i limitom Google Play. Nie
zastępuje więc istniejącego feedbacku testowego w Play Console ani raportu
e-mail i nie jest warunkiem rozpoczęcia testu.

## Bramka jakości po superaudycie 2026-08-01

Pełny raport znajduje się w
[`docs/GOOGLE_PLAY_RELEASE_QUALITY_AUDIT_2026-08-01.md`](docs/GOOGLE_PLAY_RELEASE_QUALITY_AUDIT_2026-08-01.md).
Techniczny kandydat AAB jest gotowy do ścieżki testowej, ale produkcja pozostaje
**NO-GO procesowym** do czasu ukończenia rzeczywistego testu zamkniętego.
Historyczna bramka P0 obejmowała:

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

- **P0.1 ABI — AAB potwierdzony:** przebieg `30699855081` zbudował AAB
  zawierający wyłącznie `arm64-v8a` i komplet 15 bibliotek;
  hook p4a dodaje filtr Gradle, a osobny walidator blokuje APK/AAB zawierające
  nieobsługiwane ABI lub pozbawione bibliotek Python/SDL;
- **P0.2 Auto Backup — manifest AAB potwierdzony:** ustawiono
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
- **P0.5 bramka AAB — potwierdzona:** kontrola wyrównania bibliotek została
  wydzielona do testowanego narzędzia i zmieniona z ostrzeżenia na twardy błąd;
  workflow sprawdza też podpis AAB i wykonuje `bundletool validate` narzędziem
  przypiętym wersją oraz SHA-256. Odczyt finalnego AAB ujawnił techniczne
  uprawnienia zależności, dlatego CI otrzymuje jawną allowlistę i ma blokować
  każde nowe uprawnienie do czasu audytu. Następna bramka wymusza jawną blokadę
  cleartext traffic i pilnuje, aby nie pojawił się niezaudytowany Network
  Security Config;
- **P0.6 walidacja finalnego backupu — naprawiona:** przebieg `31185098966`
  zbudował poprawny podpisany AAB, lecz stary krok CI odczytał manifest
  źródłowy sprzed scalania Gradle i zgłosił fałszywy błąd. Walidator odczytuje
  teraz finalny manifest bezpośrednio z AAB przez Bundletool, a wariant APK
  sprawdza finalny manifest scalony;
- do pełnego zamknięcia technicznego pozostaje krótki test fizycznego ARM oraz
  API 35/36 na kandydacie odtworzonym z `main`.

Podpisany AAB z commita `f57ed4b` i przebiegu `30699855081` przeszedł podpis,
`bundletool validate`, legal bundle, wyłącznie `arm64-v8a`, wyrównanie 16 KB,
backup, allowlistę uprawnień, blokadę cleartext traffic oraz bramkę providerów
Firebase/AdMob. Pozostaje odtworzyć go z `main` po scaleniu release train.

Stan warstwy P1 po pakiecie jakości 2026-08-02:

- **dostępność — etap 1 wdrożony:** osobny kontroler Python i natywny serwis
  Android udostępniają TalkBackowi lokalizowany opis aktywnej karty oraz
  komunikaty o zmianie ekranu, wyniku i błędzie; wszystkie krytyczne akcje mają
  co najmniej 48 dp, kontrast palet jest testowany względem 4,5:1, a układ
  reaguje na font scale do 200% i landscape;
- **ważne ograniczenie Kivy:** obecna warstwa udostępnia semantykę całej
  powierzchni i komunikaty live region, ale jeszcze nie tworzy osobnych
  `AccessibilityNodeInfo` dla każdego pola i przycisku. Pełna nawigacja bez
  wzroku pozostaje zadaniem P1.1 po ręcznym teście POC na urządzeniu;
- **CI wdrożone:** pełna suita ma próg pokrycia 50%, zależności są sprawdzane
  przez `pip-audit`, a historia Git przez Gitleaks;
- **zależności desktop/core zaktualizowane:** Pillow 12.3.0, pypdf 6.15.0,
  ttkbootstrap 1.20.4, Ruff 0.15.22 i mypy 2.3.0; fallback szyfrowania PDF
  obsługuje obie sygnatury API;
- **Pillow 12.3.0 — migracja zakończona w `v1.5.13`:** lokalna receptura
  przypina źródło i SHA-256, wyłącza ścieżki hosta podczas cross-build oraz
  zachowuje dotychczasowy zestaw JPEG/PNG/FreeType. CI odczytuje wersję
  faktycznie zapakowaną w `libpybundle.so`, a audyt nie używa wyjątków CVE.
  APK/AAB, rozmiar, 16 KB i smoke na fizycznym ARM przeszły; tag `v1.5.13`
  wskazuje zweryfikowany merge commit;
- **Dependency Review i Dependabot — wdrożone:** Dependency Graph, Dependabot
  Alerts i Security Updates są aktywne, a osobna bramka PR blokuje nowe
  podatności od poziomu `moderate`. Zwykłe aktualizacje pozostają grupowane,
  poprawki bezpieczeństwa są osobnymi PR i nie mają automatycznego scalania;
- **następne P1:** ręczny audyt TalkBack/Switch Access, test fizycznego ARM oraz
  API 35/36 i bazowe pomiary startu, pamięci, ANR/jank release.

Te prace są wydzielane do osobnych modułów i narzędzi; nie wolno ponownie
rozbudować `app.py` ani `RefrigerationCalcActivity.java`.

## Nadrzędny kierunek: dekompozycja monolitu

Cel zasadniczy został osiągnięty: `main.py` jest cienkim launcherem, a główne
integracje, zakładki i dialogi mają osobne kontrolery lub serwisy. Dalsza
dekompozycja ma charakter utrzymaniowy: wykonujemy ją przy zmianie danego
obszaru, ale nie jest już samodzielnym priorytetem przed testem zamkniętym.

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

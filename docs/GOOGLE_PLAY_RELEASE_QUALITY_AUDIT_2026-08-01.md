# Superaudyt jakości i gotowości Google Play — 2026-08-01

## Decyzja

**Stan bieżący: NO-GO dla kolejnego AAB i publikacji produkcyjnej.**

Nie należy przez to zatrzymywać istniejącej ścieżki Alpha ani usuwać testerów,
bo przerwa mogłaby zniszczyć ciągłość wymaganego testu. Poprawkę trzeba wydać
na tej samej ścieżce z wyższym `versionCode`, a obecnego AAB nie promować do
produkcji.

Nie oznacza to, że aplikacja jest niskiej jakości. Logika obliczeń, podstawowa
stabilność, uprawnienia, Billing, UMP, zgodność 16 KB i organizacja kodu mają
dobry poziom. Zostały jednak wykryte trzy problemy, które trzeba zamknąć przed
następnym pakietem dla testerów:

1. AAB reklamuje architektury bez kompletnego środowiska Kivy/Python i pakiet
   wygenerowany dla `x86_64` instaluje się, lecz natychmiast ulega awarii.
2. domyślny Android Auto Backup obejmuje lokalne preferencje i pliki, mimo że
   polityka prywatności opisuje je jako dane lokalne usuwane wraz z danymi
   aplikacji;
3. Firebase jest inicjalizowany przed decyzją o dobrowolnej telemetrii. Samo
   zbieranie Analytics i Crashlytics jest wyłączone, ale zależności Firebase
   mogą utworzyć identyfikator instalacji i pliki sesji. Trzeba zagwarantować
   oraz zmierzyć brak transmisji Firebase przed zgodą albo skorygować
   deklaracje.

Stan naprawy: problemy 1 i 2 mają już automatyczne bramki oraz potwierdzony
debug APK. Dla problemu 3 wdrożono ręczny start Firebase po zgodzie, usunięcie
`FirebaseInitProvider`, czyszczenie po cofnięciu zgody i walidator wynikowego
manifestu. Pierwszy pomiar wykazał jednak żądanie wspólnego transportu Google
do `firebaselogging.googleapis.com`, mimo braku lokalnych artefaktów Firebase.
W odpowiedzi usunięto również `MobileAdsInitProvider` i rozszerzono bramkę CI.
Powtórny pomiar bazy DataTransport wykazał wyłącznie zdarzenia
`PLAY_BILLING_LIBRARY`, więc sama nazwa hosta nie była dowodem działania
Firebase. NO-GO pozostaje do testu włączenia/cofnięcia zgody na ARM oraz pełnej
weryfikacji nowego podpisanego AAB.

Po usunięciu tych blokad należy zbudować nowy AAB z aktualnego `HEAD`, wykonać
testy pakietów wygenerowanych przez Bundletool, przesłać go do Alpha i dopiero
na nim prowadzić udokumentowany test zamknięty. Samo zwiększanie liczby funkcji
nie zastąpi realnego użycia i opinii testerów.

## Zakres i podstawa audytu

Sprawdzono:

- repozytorium, historię, otwarty PR, metadane GitHub i stan GitHub Actions;
- kod Pythona i Javy, manifest wynikowy, uprawnienia, zależności i konfigurację
  Buildozera/python-for-android;
- podpisany AAB 1.5.12, `versionCode 98`, z przebiegu release dla commitu
  `80c42da`;
- aktualną gałąź `codex/refactor-labor-workflow`, commit `6539a82`;
- testy jednostkowe, lint, typowanie i pokrycie kodu;
- wygenerowany przez Bundletool zestaw APK dla urządzenia `x86_64`;
- uruchomienie na emulatorze Android 11 / API 30, zmianę orientacji, skalę
  czcionki, tryb offline, tło, blokadę ekranu i drzewo dostępności;
- publiczną politykę prywatności, dokumenty testu zamkniętego oraz aktualne
  materiały Google Play, Android i Firebase.

Ograniczenia audytu:

- lokalnie dostępny był tylko emulator API 30 `x86_64`; nie można na tej
  podstawie zatwierdzić zachowania na Androidzie 15/16, urządzeniu ARM,
  tablecie ani urządzeniu składanym;
- najnowszy debug APK z commitu `6539a82` zbudował się w CI dla `arm64-v8a`,
  ale nie powstał jeszcze podpisany AAB zawierający wszystkie późniejsze
  zmiany;
- zakupów produkcyjnych, UMP z konfiguracją produkcyjną i raportu
  przed opublikowaniem nie da się wiarygodnie zatwierdzić poza ścieżką Play;
- audyt nie zastępuje porady prawnej ani testu bezpieczeństwa wykonywanego
  przez wyspecjalizowany zespół.

## Stan artefaktów i CI

| Obszar | Wynik | Dowód |
| --- | --- | --- |
| Testy Pythona | PASS | 403 testy zakończone sukcesem |
| Ruff i mypy | PASS | przebieg 30690032881 |
| Debug APK arm64 z `6539a82` | PASS | przebieg 30690035825 |
| Podpisany AAB 1.5.12 | PASS techniczny | przebieg 30569531604, Bundletool `validate` bez błędu |
| Wyrównanie 16 KB | PASS | `PAGE_ALIGNMENT_16K`, brak wykrytych bibliotek 4 KB |
| Check PR #13 „Buildozer” | FAIL infrastrukturalny, powtarzalny | przebiegi `30690032852` i `30692299604` zakończyły się na `No space left on device` podczas odtwarzania cache; drugi runner nie mógł już zapisać własnego logu diagnostycznego |
| Check po naprawie cache i ABI | PASS dla debug APK | przebieg `30693177259`; bez lokalnego cache `.buildozer`, APK ma wyłącznie `arm64-v8a` i 15 bibliotek |
| PR #13 | NIEGOTOWY | draft, `mergeable`, lecz `mergeStateStatus=UNSTABLE` |
| Domyślna gałąź `main` | NIEAKTUALNA | 12 commitów za gałęzią audytowaną; README/buildozer nadal 1.5.11 |
| Opis repozytorium GitHub | NIEAKTUALNY | nadal zaczyna się od „Refrigeration Calc 1.5.11” |

SHA-256 sprawdzonego AAB:

`814A553FC9A051DB5A9A01172DABF0C09C929FB9BA59B87FF6A9569F048AA6C3`

Wniosek: udany ręczny build arm64 nie zastępuje czerwonego checku PR. Przed
mergem trzeba ograniczyć rozmiar cache lub wyczyścić niepotrzebne części,
ponowić check i uzyskać zielony komplet wyników.

## P0 — blokady przed kolejnym AAB

### P0.1. Niespójne ABI w AAB powoduje awarię `x86_64`

`buildozer.spec` deklaruje wyłącznie `arm64-v8a`, ale zależność AndroidX
DataStore wnosi `libdatastore_shared_counter.so` dla czterech ABI. Zawartość
AAB jest następująca:

| ABI | Liczba bibliotek | Stan |
| --- | ---: | --- |
| `arm64-v8a` | 15 | komplet SDL, Python, `libmain`, `libpybundle` i biblioteki pomocnicze |
| `armeabi-v7a` | 1 | tylko `libdatastore_shared_counter.so` |
| `x86` | 1 | tylko `libdatastore_shared_counter.so` |
| `x86_64` | 1 | tylko `libdatastore_shared_counter.so` |

Bundletool uznał `x86_64` za obsługiwane, utworzył i zainstalował zestaw
split APK. Pierwsze uruchomienie zakończyło się:

- brakiem `libpybundle.so` i `libpython3.13.so` dla `x86_64`;
- `UnsatisfiedLinkError` dla `SDLActivity.nativeSetenv`;
- `FATAL EXCEPTION: SDLActivity`.

Ryzyko dotyczy m.in. części Chromebooków, emulatorów i urządzeń laboratorium
Google. Google Play tworzy konfiguracyjne APK według architektury procesora,
dlatego samo ustawienie nazwy artefaktu na `arm64-v8a` nie jest zabezpieczeniem.

Wymagane działanie:

1. wymusić filtr ABI na poziomie Gradle/packaging tak, aby AAB zawierał tylko
   `arm64-v8a`, albo dostarczyć pełny runtime dla każdego reklamowanego ABI;
2. nie opierać poprawki wyłącznie na nazwie pliku AAB;
3. dodać do CI analizę `base/lib/<abi>` i zakończyć build błędem, jeżeli ABI nie
   ma co najmniej `libmain.so`, `libpybundle.so`, `libpython3.13.so` i SDL;
4. dla release generować Bundletool APK dla reprezentatywnego urządzenia ARM
   i każdego pozostałego ABI, a następnie wykonywać smoke start;
5. dopiero po tym wydać nowy AAB.

Kryterium akceptacji: AAB reklamuje wyłącznie kompletne ABI, Bundletool nie
generuje niekompletnego zestawu, a testowe uruchomienie nie zawiera
`UnsatisfiedLinkError` ani `FATAL EXCEPTION`.

Stan naprawy 2026-08-01: na gałęzi roboczej dodano filtr ABI do generowanego
`build.gradle` oraz niezależny walidator APK/AAB. Walidator odrzuca oba stare
artefakty 1.5.12 z powodu `armeabi-v7a`, `x86` i `x86_64`. Przebieg
`30693177259` zbudował i zweryfikował nowy APK zawierający wyłącznie
`arm64-v8a` oraz 15 bibliotek. Punkt pozostaje otwarty tylko dla podpisanego
AAB i testu Bundletool/ARM.

Źródło: [format Android App Bundle](https://developer.android.com/guide/app-bundle/app-bundle-format).

### P0.2. Auto Backup a dane lokalne i uprawnienia PRO

Manifest wydania ma `android:allowBackup="true"` i nie zawiera ani
`fullBackupContent`, ani `dataExtractionRules`. Przy tych ustawieniach Android
domyślnie obejmuje kopią m.in. SharedPreferences, pliki wewnętrzne i bazy.

W danych aplikacji występują m.in.:

- `entitlement.json`, `exchange_rates.json`, `ui_preferences.json`;
- ustawienia Billing i lokalne flagi uprawnień;
- preferencje UMP, AdMob, Analytics, Crashlytics i identyfikatory SDK;
- dane Firebase sessions/datastore.

Polityka prywatności opisuje wartości kalkulatora, własne produkty, ustawienia
i PDF jako dane lokalne usuwane przez wyczyszczenie danych lub odinstalowanie.
Automatyczna kopia na konto Google i późniejsze odtworzenie uprawnień lub
identyfikatorów nie jest z tym opisem w pełni spójne.

Rekomendacja domyślna: ustawić `allowBackup=false`. Zakupy należy odtwarzać z
Google Play Billing, a nie z lokalnej kopii flag. Jeżeli zachowanie ustawień ma
być przywracane, trzeba przygotować ścisłą listę dozwolonych danych osobno dla
Androida 11 i niższych oraz Androida 12+, wykluczając Billing, entitlement,
UMP, reklamy, Firebase, identyfikatory urządzenia i pliki tymczasowe.

Kryterium akceptacji: manifest ma jawną politykę backupu, test backup/restore
nie przywraca lokalnego PRO ani tokenów, a polityka prywatności dokładnie
opisuje wybrane zachowanie.

Stan naprawy 2026-08-01: na gałęzi roboczej ustawiono
`android.allow_backup = False`, dopisano test konfiguracji i zaktualizowano
lokalną politykę prywatności. Punkt pozostaje otwarty do sprawdzenia wynikowego
manifestu oraz próby odinstalowania/ponownej instalacji nowego APK.

Źródła: [Android Auto Backup](https://developer.android.com/identity/data/autobackup),
[bezpieczny backup](https://developer.android.com/privacy-and-security/risks/backup-best-practices).

### P0.3. Firebase musi być naprawdę dobrowolny przed inicjalizacją

Pozytywy:

- manifest ustawia `firebase_analytics_collection_enabled=false`;
- manifest ustawia `firebase_crashlytics_collection_enabled=false`;
- kod wywołuje `fetchAndActivate()` Remote Config tylko po zgodzie;
- zdarzenia i wyjątki są blokowane przez `isEnabled()`.

Problem: `RefrigerationCalcActivity.onCreate()` zawsze wywołuje
`telemetry().initialize()`, a ta metoda tworzy `FirebaseApp`, Analytics,
Crashlytics i Remote Config przed pokazaniem decyzji o telemetrii. Na świeżym
uruchomieniu zaobserwowano lokalne pliki Firebase Sessions i identyfikatorów.
Dokumentacja Firebase wskazuje, że Firebase Installations automatycznie tworzy
i zbiera FID, a Remote Config używa FID do wyboru konfiguracji.

Preferowana poprawka:

1. wykrywać obecność konfiguracji Firebase bez inicjalizacji SDK;
2. inicjalizować Firebase dopiero, gdy wcześniej zapisana zgoda jest aktywna
   albo użytkownik właśnie ją wyraził;
3. po odmowie nie tworzyć instancji Firebase;
4. po wycofaniu zgody wyłączyć kolekcję, zatrzymać kolejne pobrania i rozważyć
   usunięcie FID przez oficjalne API;
5. wykonać test sieciowy na świeżej instalacji: przed zgodą brak wywołań do
   domen Firebase/Google Analytics/Crashlytics; po zgodzie wyłącznie
   zadeklarowane usługi;
6. dopiero po teście zatwierdzić formularz Bezpieczeństwo danych i politykę.

Stan wdrożenia 2026-08-01: punkty 1–4 zostały zaimplementowane.
`FirebaseTelemetryService` wykrywa zasób `google_app_id` bez tworzenia obiektów
SDK, `Activity` uruchamia usługę tylko dla wcześniej zapisanej aktywnej zgody,
manifest usuwa `FirebaseInitProvider`, a rezygnacja wyłącza kolekcję, resetuje
lokalne dane Analytics, usuwa niewysłane raporty Crashlytics i zleca usunięcie
FID. Pierwszy test świeżej instalacji potwierdził brak `FirebaseApp`, plików
Installations, Crashlytics i Sessions przed zgodą, lecz log systemowy pokazał
żądanie DataTransport do `firebaselogging.googleapis.com`. Provider reklam
również został usunięty, a walidator APK/manifestu odrzuca teraz obecność obu
providerów automatycznego startu.

Powtórny test APK z przebiegu `30696006335` na całkowicie wyczyszczonych danych
potwierdził komunikat `Firebase remains dormant until telemetry consent`, brak
plików Firebase i brak obu providerów w binarnym manifeście. Przechwycenie
kolejki przed wysłaniem dało 20 zdarzeń, wszystkie z
`transport_name=PLAY_BILLING_LIBRARY`; pole `pseudonymous_id` było puste.
Oznacza to, że obserwowany host jest współdzielonym kanałem telemetrycznym
Biblioteki płatności Google Play, a nie dowodem inicjalizacji Firebase.
Etap „przed zgodą” jest zaliczony. Nadal trzeba na fizycznym urządzeniu ARM
potwierdzić utworzenie danych dopiero po zgodzie oraz ich wyczyszczenie po jej
cofnięciu; emulator x86 zakończył warstwę Kivy przez ograniczenie translacji
ARM (`SIGILL` w `libndk_translation.so`).

Kryterium akceptacji: brak instancji, plików, identyfikatorów i transportów
Firebase przed zgodą; host współdzielony z innym SDK musi być oceniany razem z
`transport_name`, a nie tylko po nazwie domeny. Po zgodzie wymagany jest test
utworzenia danych i ich wyczyszczenia po wycofaniu zgody.

Źródła: [sterowanie Analytics](https://firebase.google.com/docs/analytics/android/configure-data-collection),
[Firebase Installations](https://firebase.google.com/docs/projects/manage-installations),
[ujawnianie danych Firebase](https://firebase.google.com/docs/android/play-data-disclosure),
[formularz Bezpieczeństwo danych](https://support.google.com/googleplay/android-developer/answer/10787469).

### P0.4. Zamknąć PR i odtworzyć wydanie z aktualnego kodu

Sprawdzony AAB pochodzi z `80c42da`, podczas gdy gałąź PR zawiera już późniejsze
checkpointy feedbacku, App Shortcuts, polityki backupu, ABI i zgód SDK. Stary
AAB nie może być podstawą kolejnego testu. Domyślna gałąź GitHub nadal pokazuje
1.5.11.

Stan bramki wydania po audycie: kontrola ABI jest twarda, a kontrola wyrównania
16 KB została wydzielona z workflow do testowanego narzędzia. Wykrycie segmentu
`PT_LOAD` poniżej 16 KB kończy build błędem zamiast ostrzeżeniem. Workflow
sprawdza również podpis AAB przez `jarsigner` i uruchamia `bundletool validate`
wersją 1.18.3 przypiętą sumą SHA-256. Te zabezpieczenia muszą jeszcze przejść na
nowym podpisanym AAB z aktualnej gałęzi.

Wymagane działanie po P0.1–P0.3:

1. usunąć przyczynę przepełnienia dysku runnera i ponowić wymagany check;
2. uruchomić testy, Ruff, mypy, audyt zależności i bramkę ABI;
3. zbudować podpisany AAB z aktualnego commitu;
4. sprawdzić jego wersję, podpis, ABI, 16 KB, uprawnienia i split APK; podpis,
   struktura Bundletool, ABI i 16 KB mają być twardymi krokami workflow;
5. zmergować PR #13 do `main` dopiero przy zielonych checkach;
6. zaktualizować opis repozytorium z 1.5.11 na aktualną wersję;
7. zsynchronizować publiczną politykę prywatności;
8. dopiero wtedy wykonać tag i przesłać AAB do Alpha.

## P1 — istotne prace jakościowe

### P1.1. Rdzeń interfejsu nie jest dostępny dla TalkBack

Drzewo UI Automator po ustabilizowaniu aplikacji zawierało 14 węzłów, tylko
jeden niepusty tekst (`Test Ad`) i zero `content-desc`. Elementy Kivy — pola,
przyciski, trzy zakładki, wyniki i ustawienia — nie są wystawione jako natywne
semantyki Androida. TalkBack i automatyczne testy dostępności nie mogą
obsługiwać podstawowych funkcji.

To nie jest poprawka pojedynczych etykiet. Najpierw potrzebny jest krótki
spike techniczny:

- sprawdzić możliwość mostka semantyki Kivy → Android AccessibilityNodeInfo;
- jeżeli mostek nie zapewni stabilnego fokusu i akcji, zaplanować stopniowe
  przenoszenie najważniejszych formularzy/nawigacji do warstwy natywnej;
- zacząć od nagłówka, trzech kart, pól pierwszego kalkulatora, `Oblicz`, `PDF`,
  `Wyczyść` oraz wyniku;
- testować TalkBack, Switch Access i klawiaturę sprzętową;
- dodać ręczną listę kontrolną i test automatyczny etykiet.

Kryterium akceptacji: użytkownik TalkBack potrafi bez wzroku przejść przez
pełne podstawowe obliczenie, odczytać błąd i wynik.

Źródło: [testowanie dostępności Android](https://developer.android.com/guide/topics/ui/accessibility/testing).

### P1.2. Cele dotykowe i kontrast

W kodzie występują interaktywne elementy o wysokości 30, 42, 44 i 46 dp.
Przyciski paska górnego mają 44 × 44 dp. Zalecane minimum Androida to 48 dp.

Obliczony kontrast palety:

| Paleta | Kontrast | Ocena dla zwykłego tekstu |
| --- | ---: | --- |
| `primary` | 5,63:1 | PASS |
| `ice` | 3,64:1 | FAIL poniżej 4,5:1 |
| `dark` | 7,85:1 | PASS |
| `muted` | 9,55:1 | PASS |
| `pro` | 4,66:1 | PASS, mały margines |

Paleta `ice` jest używana m.in. w głównych przyciskach kalkulatorów,
ustawieniach i feedbacku. Należy przyciemnić tło albo tekst oraz automatycznie
testować kontrast obu motywów.

Kryterium akceptacji: wszystkie akcje mają efektywny cel co najmniej 48 × 48
dp, zwykły tekst minimum 4,5:1, a duży tekst i grafika interfejsu minimum 3:1.

Źródło: [Core app quality](https://developer.android.com/docs/quality-guidelines/core-app-quality).

### P1.3. Skala czcionki i responsywność

Przy `font_scale=1.3` potwierdzono:

- obcięcie tekstu stopki i informacji o wersji;
- zatłoczenie przycisku PRO i stopki;
- zmniejszenie użytecznej wysokości treści;
- problemy z układem nagłówka.

Przy orientacji poziomej dolna nawigacja, stopka i reklama zajmują większość
wysokości, a karta formularza jest silnie obcięta. Aplikacja deklaruje pełną
obsługę obu orientacji, więc nie można traktować tego jako nieobsługiwanego
scenariusza.

W ustawieniach przy zwykłej skali obcina się także tekst „Kursy: aktualizuj
automatycznie”. Potrzebne są elastyczne wysokości, zawijanie/krótsze etykiety,
kompaktowy wariant landscape i testy przy 100%, 130%, 150% oraz 200%.

Kryterium akceptacji: brak obciętego tekstu i nakładania na telefonie portrait,
landscape, tablecie i przy dużej czcionce; wszystkie funkcje pozostają
przewijalne.

### P1.4. Aktualne urządzenia i raport Play

Lokalny emulator API 30 nie reprezentuje wymagań Androida 15/16. Projekt ma
`targetSdk=36` i zgodność 16 KB, co jest dobrym wynikiem, ale trzeba dodać:

- emulator/API 35 i API 36;
- co najmniej jedno fizyczne urządzenie ARM;
- tablet lub duży ekran oraz landscape;
- wynik raportu przed opublikowaniem dla polskiego i angielskiego;
- kontrolę Android Vitals, awarii, ANR, startu i pamięci po każdym AAB.

Od 31 sierpnia 2026 aktualizacje mają celować w API 36; projekt już spełnia ten
warunek, ale zachowanie na API 36 nadal wymaga testu.

Źródła: [wymagania target API](https://support.google.com/googleplay/android-developer/answer/11926878),
[raport przed opublikowaniem](https://support.google.com/googleplay/android-developer/answer/9842757).

### P1.5. Zależności i automatyczny audyt bezpieczeństwa

`pip-audit` wykazał:

- Android faktycznie buduje `Pillow 11.3.0`, dla którego baza zgłasza wiele
  znanych podatności; poprawki zbiorcze dochodzą do `12.3.0`;
- `requirements.txt` ma `Pillow 12.2.0`, nadal z podatnościami naprawionymi w
  `12.3.0`;
- `pypdf 6.13.3` ma cztery zgłoszenia CVE, a pełny zestaw poprawek wymaga
  co najmniej `6.15.0`;
- `requirements-mobile.txt` nie odpowiada faktycznemu stosowi Androida:
  build używa `fpdf2/fonttools/defusedxml` i starszego Pillow.

Mobilna aplikacja nie przyjmuje dowolnych obrazów ani PDF do parsowania, więc
część scenariuszy ma ograniczoną osiągalność. Nie jest to powód do utrzymywania
znanych podatności.

Wymagane działanie:

1. najpierw sprawdzić zgodność Pillow 12.3.0 z python-for-android i FPDF;
2. podnieść Pillow oraz pypdf i uruchomić pełne testy PDF/obrazów;
3. ujednolicić plik mobilnych zależności z `buildozer.spec`;
4. dodać `pip-audit` do CI z udokumentowanym, terminowym wyjątkiem tylko wtedy,
   gdy poprawka nie jest jeszcze kompatybilna;
5. zachować Dependabot, który już tworzy PR dla pip i GitHub Actions;
6. dla prywatnego repo włączyć alerty/secret scanning, jeżeli plan GitHub je
   udostępnia, albo dodać lokalny skaner sekretów do CI.

### P1.6. Pokrycie testami i bramki jakości

Łączne pokrycie gałęzi audytowanego zestawu wynosi około 55%. To nie opisuje
jednak równomiernie jakości:

- kalkulatory domenowe mają około 95–100%;
- walidatory i obliczenia zaworów mają około 100%;
- nawigacja, ustawienia i część kontrolerów mają około 92–98%;
- `tpof/mobile/app.py` ma około 10%;
- widoki Kivy mają około 31–34%, a część widgetów 0%;
- telemetria ma około 16%;
- część ścieżek PDF i dialogów jest kontrolowana testami kontraktowymi, ale nie
  pełnymi testami zachowania.

Zamiast sztucznego celu 90% dla całej aplikacji należy dodać progi warstwowe:

- logika domenowa ≥ 90%;
- usługi i kontrolery ≥ 80%;
- cały projekt: najpierw 60–65%, następnie 70–75%;
- osobne testy urządzeniowe dla UI, których coverage.py nie mierzy sensownie.

CI powinno publikować raport pokrycia i blokować regresję względem uzgodnionego
minimum.

### P1.7. Stabilność i wydajność

Test tło → powrót → blokada → odblokowanie zakończył się PASS: ten sam PID,
brak `FATAL EXCEPTION` i ANR. Tryb offline kursów NBP także zakończył się PASS:
pozostał ostatni poprawny kurs i aplikacja nie uległa awarii.

Pomiar na debug x86/API 30 pokazał około 282 MB PSS oraz 32% jank w krótkiej
próbce 105 klatek. To nie jest wynik produkcyjnego ARM i nie może być użyty jako
werdykt, ale uzasadnia bazę wydajnościową:

- pomiar release/profileable na fizycznym ARM;
- czas do gotowego interfejsu, nie tylko `Activity displayed`;
- PSS po starcie i po przejściu przez każdą kartę;
- p50/p90/p95 klatek;
- próg regresji w kolejnych wersjach.

Źródło: [Android Vitals](https://developer.android.com/topic/performance/vitals).

## P2 — porządek wydania i utrzymanie

1. Publiczna polityka prywatności ma właściwy e-mail i wersję z 30 lipca, ale
   jest starsza od lokalnego pliku: nie zawiera aktualnego opisu
   ustrukturyzowanego formularza feedbacku. Po poprawkach P0 należy ją ponownie
   opublikować i porównać zawartość/hash.
2. README na gałęzi roboczej opisuje 1.5.12 i 403 testy, ale pierwsza strona
   repo pokazuje `main` z 1.5.11. Merge jest częścią procesu wydania.
3. Ocenić aktualizację Crashlytics 20.0.6 → 20.1.0 oraz AndroidX Core 1.18.0 →
   1.19.0 w osobnym checkpointcie kompatybilności, bez łączenia z P0.
4. **Wdrożone w kodzie, oczekuje na potwierdzenie nowym AAB:** hook ustawia
   `usesCleartextTraffic=false`, osobna bramka CI odrzuca brak tej wartości,
   wartość `true` oraz niezaudytowany Network Security Config, a test endpointu
   NBP wymaga HTTPS.
5. Wprowadzić checklistę ręcznego testu Billing przez licencjonowanego testera
   Play: cena z Console, zakup oczekujący, anulowanie, acknowledge, odtworzenie,
   wygaśnięcie subskrypcji i brak przywrócenia PRO z backupu.
6. Play Integrity pozostawić jako warstwę monitoringu, dopóki nie istnieje
   backend weryfikujący token. Obecna konfiguracja projektu i standardowe
   werdykty są włączone, ale aplikacja nie wysyła żądań Integrity. Włączanie
   kolejnych sygnałów bez serwera nie daje wiarygodnej ochrony. Wrócić do tego
   dopiero przy potwierdzonych nadużyciach płatności lub modułów PRO i wtedy
   zaktualizować Bezpieczeństwo danych.

## Co już spełnia dobre praktyki

- `buildozer.spec` jawnie żąda tylko `INTERNET` i `ACCESS_NETWORK_STATE`, a
  końcowy manifest zawiera ponadto zwykłe uprawnienia techniczne pochodzące z
  AdMob, Play Billing, Firebase/DataTransport i WorkManager; ich ścisła
  allowlista jest kontrolowana w CI, a aplikacja nie żąda dostępu do dokładnej
  lokalizacji, kamery, mikrofonu, kontaktów ani pamięci współdzielonej;
- release nie jest debuggowalny, a kod własny używa HTTPS i waliduje odpowiedź
  NBP z timeoutem oraz atomowym cache;
- UMP jest uruchamiany przed inicjalizacją reklam, a reklamy czekają na
  `canRequestAds()`; manifest usuwa automatyczny `MobileAdsInitProvider`, więc
  SDK reklam nie omija tej bramki przy starcie procesu;
- build debug używa testowych jednostek AdMob, release właściwych;
- Billing używa aktualnego klienta 9.1.0, obsługuje pending purchases, pobiera
  cenę z Play, odtwarza zakupy i potwierdza transakcje;
- publiczny `app-ads.txt` zwraca HTTP 200, `text/plain` i dokładnie wpis
  `google.com, pub-7481054652344026, DIRECT, f08c47fec0942fa0`; AdMob pokazuje
  pełne upoważnienie sprzedawcy;
- feedback otwiera edytowalny szkic w aplikacji pocztowej i niczego nie wysyła
  automatycznie;
- kalkulatory działają offline; NBP ma bezpieczny fallback;
- target API 36 i 16 KB są spełnione;
- logika biznesowa jest dobrze przetestowana i rozdzielona od UI;
- `RefrigerationCalcActivity` deleguje do osobnych serwisów, zgodnie z
  nadrzędnym celem rozbijania monolitu;
- istnieje rzeczywisty przewodnik testera i rejestr decyzji feedbacku.
- ostatnio sprawdzony stan Konsoli Play nie wskazywał problemów z zasadami, a
  deklaracje zawartości były ukończone; trzeba to ponowić dla każdego AAB.

## Roadmapa wykonawcza

### Etap A — twarda bramka wydania, około 2–4 dni

1. Naprawić spójność ABI i dodać CI gate + Bundletool smoke.
2. Ustalić oraz wdrożyć jawną politykę backupu.
3. Zrobić Firebase lazy opt-in i test „zero transmisji przed zgodą”.
4. Podnieść krytyczne zależności, o ile test kompatybilności Androida przejdzie.
5. Naprawić powtarzalne przepełnienie cache runnera: ograniczyć/usunąć cache
   `.buildozer`, raportować miejsce przed i po restore, a następnie uzyskać
   zielone checki PR. Dwa niezależne przebiegi (`30690032852` i `30692299604`)
   zakończyły się w tym samym miejscu, więc ponowienie bez zmiany workflow nie
   jest rozwiązaniem.

### Etap B — nowy checkpoint AAB, około 1 dzień + czas CI/Play

1. Pełne testy, lint, mypy, coverage, dependency audit i skan sekretów.
2. Podpisany AAB z aktualnego `HEAD`.
3. Weryfikacja podpisu, wersji, 16 KB, ABI i splitów Bundletool.
4. Smoke na ARM oraz API 35/36.
5. Merge do `main`, aktualizacja opisu repo, tag i synchronizacja polityki.
6. Przesłanie do Alpha i przegląd raportu przed opublikowaniem.

### Etap C — jakość widoczna dla testerów, około 3–6 dni

1. Naprawić skalę czcionki, landscape i obcięte ustawienia.
2. Podnieść cele dotykowe do 48 dp i kontrast palety `ice`.
3. Przeprowadzić POC dostępności i wdrożyć pierwszy dostępny przepływ
   kalkulatora.
4. Dodać pomiary release ARM oraz macierz urządzeń.

### Etap D — właściwy test zamknięty, minimum 14 dni

1. Utrzymać co najmniej 12 realnych testerów zapisanych bez przerwy.
2. Rozdzielić scenariusze na kilka dni i funkcji, nie wymuszać pozornych
   codziennych uruchomień.
3. Zebrać prawdziwe zgłoszenia przez aplikację i prywatne opinie Play.
4. Odpowiedzieć, sklasyfikować i zapisać decyzje bez danych osobowych.
5. Wydać co najmniej jedną poprawkę wynikającą z prawdziwej opinii i poprosić
   o jej retest.
6. Przed drugim wnioskiem sprawdzić Vitals, raport urządzeń, Bezpieczeństwo
   danych i zgodność z zasadami.

### Etap E — dalsza dekompozycja i funkcje

Po stabilnym AAB i rozpoczęciu prawidłowego testu wrócić do rozbijania
monolitu. Nowe prace z tego audytu również mają powstawać modułowo:

- `AbiBundleVerifier`/skrypt CI poza kodem aplikacji;
- osobna polityka backupu i migracji danych;
- `FirebaseTelemetryService` bez inicjalizacji w Activity przed zgodą;
- warstwa dostępności niezależna od kontrolerów obliczeń;
- moduł metryk wydajności bez logiki UI;
- dopiero potem In-App Review, elastyczne In-App Updates i następne kalkulatory.

## Dowody dla kolejnego wniosku Google

Google nie wymaga dokumentu „na pokaz”. Najmocniejszy pakiet dowodów to:

- tabela realnych urządzeń i wykonanych scenariuszy;
- zanonimizowane zgłoszenia `CT-rrrr-nnn` z decyzją i numerem poprawionej wersji;
- informacje o wersji wskazujące konkretny feedback;
- potwierdzenie retestu przez testerów;
- zielony raport przed opublikowaniem lub opis naprawionych problemów;
- zrzut Vitals bez nierozwiązanych awarii/ANR;
- aktualna polityka, formularz Bezpieczeństwo danych i SDK Index;
- zielone CI z testami, ABI, zależnościami, dostępnością i coverage.

Zasady ponownego dostępu produkcyjnego: [Google Play — wymagania testu](https://support.google.com/googleplay/android-developer/answer/14151465).

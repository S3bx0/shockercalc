# Changelog

Wszystkie istotne zmiany w projekcie **Refrigeration Calc** (`pl.smilczarek.refrigerationcalc`).
Format na podstawie [Keep a Changelog](https://keepachangelog.com/),
wersjonowanie wg [SemVer](https://semver.org/).

## [Unreleased]

### Naprawiono

- Wysokość banera AdMob jest zapamiętywana podczas tworzenia widoku na wątku
  interfejsu. Python może ją teraz bezpiecznie odczytać bez wywoływania metod
  widoku reklamowego poza głównym wątkiem Androida.

### Zmieniono

- Wydzielono integrację Google Play Billing z
  `RefrigerationCalcActivity` do osobnego `BillingService`. Serwis przejął
  połączenie z Google Play, pobieranie produktów, uruchamianie zakupów,
  acknowledge, synchronizację refund/revoke oraz zapis uprawnień PRO i modułu
  zaworów.
- `RefrigerationCalcActivity` zachowuje wyłącznie cienkie metody wywoływane
  przez PyJNIus oraz przekazuje do serwisu zdarzenia cyklu życia.
- Wydzielono eksport plików przez MediaStore i uruchamianie Android Sharesheet
  z `RefrigerationCalcActivity` do osobnego `FileShareService`. Publiczna metoda
  `shareFile` pozostaje zgodnym, cienkim delegatem dla PyJNIus.

### Testy

- Dodano testy kontraktu Billing chroniące identyfikatory produktów i planu,
  zakup subskrypcji i modułu jednorazowego, obsługę anulowania, acknowledge
  oraz cofanie lokalnych uprawnień po utracie zakupu.
- Dodano testy kontraktu udostępniania plików chroniące eksport do katalogu
  Pobrane na Androidzie 10+, starszy fallback URI, MIME, temat, treść i flagę
  odczytu dla aplikacji odbierającej.

## [1.5.11] - 2026-07-20

### Dodano

- Dodano przewijalną kartę kursów PLN, EUR i USD w ustawieniach. Karta pokazuje
  wartość jednej jednostki każdej waluty w PLN, datę danych i źródło NBP.

### Naprawiono

- Bardzo małe, dodatnie koszty nie znikają już z wykresu robocizny przez zbyt
  szeroką minimalną przerwę pomiędzy segmentami.
- Kwota w środku wykresu jest automatycznie zmniejszana zamiast zawijania i
  nachodzenia na etykietę kosztu całkowitego.
- Ustawienia są przewijane na mniejszych ekranach po dodaniu karty kursów.

### Usunięto

- Usunięto całkowicie ograniczenie czasowe wersji testowej oraz ekran blokujący
  aplikację po zapisanej w kodzie dacie.

### Testy

- Dodano test formatu wartości kursów w karcie ustawień i regresje układu karty
  oraz renderowania małych segmentów wykresu.

## [1.5.10] - 2026-07-11

### Naprawiono

- Naprawiono pobieranie kursów NBP na Androidzie przez dołączenie aktualnego
  magazynu certyfikatów CA i jawne użycie go dla połączeń HTTPS.
- Pole kosztów dodatkowych używa teraz wybranej waluty, zachowuje wartość przy
  zmianie waluty i przelicza ją do PLN przed wykonaniem obliczeń.
- Usunięto nakładającą się poświatę małych segmentów wykresu robocizny oraz
  poprawiono kontrast kwoty i etykiety w środku wykresu.
- Poszerzono okno szczegółów wykresu, aby legenda i kwoty nie były ucinane na
  wąskich ekranach.

### Zmieniono

- Segmenty wykresu są renderowane jako precyzyjne wycinki pierścienia zamiast
  grubych linii z zaokrąglonymi końcami.
- Usunięto zdublowaną listę kwot spod kompaktowej legendy wykresu.

### Testy

- Dodano testy konwersji edytowalnych kwot EUR i USD do wewnętrznej wartości
  PLN oraz zabezpieczenia przed obliczeniem bez dostępnego kursu.

## [1.5.9] - 2026-07-11

### Dodano

- Dodano warstwę prezentacji kosztów robocizny w PLN, EUR i USD bez zmiany
  obliczeń źródłowych wykonywanych w PLN.
- Dodano automatyczne pobieranie kursów EUR i USD z NBP, lokalny cache ostatnich
  poprawnych kursów oraz bezpieczny tryb offline z datą kursu.
- Dodano wybór waluty i przełącznik automatycznej aktualizacji kursów w
  ustawieniach aplikacji.

### Zmieniono

- Przebudowano wykres struktury kosztów robocizny w lekkim Kivy Canvas:
  grubszy donut, spokojniejsza paleta, przerwy i subtelny glow segmentów,
  animacja 750 ms oraz koszt całkowity w środku.
- Uporządkowano legendę wykresu i dodano przewijany dialog szczegółów
  dostosowany do mniejszych ekranów.

### Testy

- Dodano testy pustych danych, sumy zero, pojedynczej kategorii, małych i
  ujemnych udziałów oraz długich etykiet wykresu.
- Dodano testy pobierania kursów NBP, cache offline, formatowania walut i
  trwałości ustawień użytkownika.

## [1.5.8] - 2026-07-06

### Zmieniono

- Uczytelniono wykres kosztow robocizny: wiekszy donut, legenda, podpowiedz
  oraz okno szczegolow po dotknieciu wykresu.

### Naprawiono

- Poprawiono wysokosc i padding pol w zakladce Chlodnicze, zeby wpisane
  wartosci nie byly ucinane przy aktywnej klawiaturze.

## [1.5.7] - 2026-07-06

### Dodano

- Dodano lekki wykres kolowy struktury kosztow w zakladce robocizny.

### Naprawiono

- Poprawiono przewijanie pol wejściowych przy widocznej klawiaturze telefonu
  w zakladkach chlodniczych, zaworow i robocizny.
- Wzmocniono regresje edytora stawek PRO, w tym resetu do wartości fabrycznych.

## [1.5.6] - 2026-07-05

### Dodano

- Dodano osiem brakujacych grafik produktow w stylu pop-art:
  `Bataty`, `Chrzan`, `Czosnek`, `Cytryny`, `Kapusta liściasta`,
  `Porzeczki czerwone i białe`, `Seler korzeniowy` i `Seler naciowy`.

### Testy / audyt

- Domknieto pokrycie mobilnego katalogu produktow: test regresyjny wymaga teraz
  zera widocznych produktow bez grafiki.
- Zaktualizowano audyt grafik i rozmiaru po dodaniu brakujacych assetow.

## [1.5.5] - 2026-07-05

### Dokumentacja / audyt

- Zaktualizowano audyt rozmiaru Androida na podstawie aktualnego release AAB
  `1.5.4`: paczka ma 45,37 MiB, a najwiekszym kontrolowalnym skladnikiem
  pozostaje katalog grafik produktow.
- Rozszerzono audyt grafik produktowych o pokrycie katalogu mobilnego:
  widoczne produkty bez grafiki, obrazy bez rekordu produktu i techniczne obrazy
  CTP ukryte w aplikacji mobilnej.

### Testy

- Dodano regresyjne budzety assetow: katalog `assets/images` ponizej 9 MiB,
  pojedyncza grafika produktu ponizej 150 KiB, WebP maksymalnie 512x512 px oraz
  kontrolowana lista brakujacych/technicznych grafik.

## [1.5.4] - 2026-07-05

### Naprawiono

- Odświeżanie motywu po przełączeniu zakładki działa teraz po odblokowaniu
  widoku i jeszcze raz w kolejnej klatce, żeby ukryte wcześniej karty **Zawory**
  i **Robocizna** nie zostawały w ciemnym stylu po zmianie na jasny motyw.

### Zmieniono

- Odchudzono kreski animowanych ikon dolnej nawigacji, aby ikony wyglądały
  lżej i spójniej z obecnym, lodowym stylem aplikacji.

## [1.5.3] - 2026-07-05

### Narzędzia / jakość

- Doprowadzono pełny przebieg `mypy .` do zielonego stanu dla projektu, w tym
  skryptów pomocniczych, generatorów assetów i aplikacji desktopowej.
- Rozszerzono workflow lint o pełny baseline `python -m mypy .`, aby CI pilnowało
  nie tylko czystych modułów, ale też szerszej części repozytorium.

### Naprawiono

- Utwardzono mobilny eksport PDF: jeśli środowisko Androida nie udostępnia
  fontu runtime dla bogatego generatora PDF, aplikacja bezpiecznie przechodzi na
  prosty mobilny generator zamiast ryzykować błąd w eksporcie.

## [1.5.2] - 2026-07-05

### Zmieniono

- Dopasowano przyciski w zakładce **Zawory** do aktualnej palety aplikacji:
  aktywne tryby używają lodowego akcentu, a nieaktywne przyciski dostały
  stonowany wariant zamiast starej szarości.

### Dokumentacja / audyt

- Dodano świeży audyt rozmiaru Androida z podziałem na największe składniki APK,
  runtime Python/Kivy oraz rekomendacje bezpiecznych optymalizacji po stabilizacji
  wersji sklepowej.
- Dodano powtarzalny audyt grafik produktowych oraz CSV z listą kandydatów do
  wymiany na finalny styl pop-art.

### Narzędzia

- Uporządkowano drobne ostrzeżenia `ruff` w skryptach pomocniczych i hookach
  Androida.

## [1.5.1] - 2026-07-03

### Dodano

- Dodano funkcję PRO do edycji stawek kalkulatora **Robocizna**: roboczogodziny,
  dojazdów, opłat, zwyżek, kontenerów, noclegów, diet, posiłków i dni roboczych
  tygodnia.
- Dodano reset stawek Robocizny do wartości fabrycznych na urządzeniu.
- Dodano osobne jednostki AdMob dla zakładki Robocizna: banner oraz rewarded.
- Dodano dokument `docs/MOBILE_REFACTOR_PLAN.md` z planem rozbicia mobilnego
  monolitu na moduły.

### Testy

- Dodano testy zapisu/resetu stawek Robocizny, serializacji konfiguracji stawek
  oraz testy pilnujące dedykowanych jednostek reklamowych Robocizny.

## [1.5.0] - 2026-07-02

### Dodano

- Dodano trzecią zakładkę mobilną **Robocizna** z kalkulatorem kosztów ekipy,
  dojazdów/delegacji, zwyżek, kontenerów, diet, posiłków i kosztów dodatkowych.
- Przeniesiono logikę kalkulatora robocizny do czystego modułu `tpof.labor`,
  zgodnego z testami i niezależnego od UI.
- Dolne menu dostało trzecią animowaną ikonę w formie kalkulatora oraz
  lokalizację PL/EN dla nowego modułu.

### Testy

- Dodano testy rdzenia `tpof.labor` oraz testy źródłowe pilnujące trzeciej
  zakładki w mobilnym pasku nawigacji.

## [1.4.13] - 2026-07-02

### Naprawiono

- Poprawiono opis szacowanego punktu zamarzania: aplikacja nie sugeruje już
  błędnie, że przy braku danych katalogowych przyjmuje `0°C`.
- Kalkulator chłodniczy odrzuca teraz przypadki, w których temperatura końcowa
  jest równa lub wyższa od początkowej, zamiast liczyć ujemne energie/moc.
- Własne produkty PRO mają dodatkową walidację: zakres `T_zam`, nieujemne
  makroskładniki, suma makroskładników do 100% oraz kategorie normalizowane bez
  polskich znaków.
- Lokalny katalog własnych produktów dostał cache w pamięci z invalidacją po
  zapisie, co zmniejsza liczbę odczytów JSON przy pracy z listami.

### Android / Google Play

- Usunięto szerokie uprawnienia `READ_EXTERNAL_STORAGE` i
  `WRITE_EXTERNAL_STORAGE`; eksport PDF na Androidzie używa prywatnego pliku
  roboczego oraz istniejącego mostka MediaStore/Share po stronie Javy.
- Edge-to-edge uwzględnia teraz klawiaturę ekranową (`WindowInsets.Type.ime()`)
  i ustawia ciemne ikony pasków systemowych nad jasnym tłem.
- Dopisano checklistę ręcznych testów edge-to-edge, IME, storage i terminu
  ważności buildów testowych.

## [1.4.12] - 2026-07-01

### Zmieniono

- Dopasowano dolny pasek zakładek, stopkę i slot reklamy do jasnego motywu:
  zamiast czarnej belki używany jest jasny, lodowy wariant kolorystyczny.
- Poprawiono kontrast ikon i podpisów dolnych zakładek w trybie jasnym.

## [1.4.11] - 2026-07-01

### Naprawiono

- Usunięto niewidzialne warstwy dotykowe między zakładkami mobilnymi, które
  mogły blokować kliknięcia w ekranie `Chłodnicze` na części urządzeń.
- Centralny komunikat walidacji po zniknięciu jest zdejmowany z warstwy dotyku,
  więc nie może blokować pól i przycisków.

## [1.4.10] - 2026-07-01

### Dodano

- Centralny komunikat walidacji w kolorach aplikacji: komunikat pojawia sie
  na srodku ekranu, pozostaje czytelny przez 1,5 s i znika plynnie do 2 s.

### Zmieniono

- Odświeżono pierwszą partię grafik produktów w stylu pop-art: buraki,
  marchew, pietruszka, pasternak, rzepa, brukiew, kalarepa, seler, por i cebula.

## [1.4.9] - 2026-07-01

### Naprawiono

- Przywrocono widoczna warstwe lodowego tla za kartami po poprawce dolnych
  zakladek z wersji 1.4.8.
- Zastapiono `MDBottomNavigation` wlasnym, kompaktowym paskiem z animowana
  sniezynka i ruchem ikony zaworu przy przelaczaniu zakladek.
- Poprawiono dialog ustawien jednostek, zeby przyciski Metric/Imperial nie
  uciekaly poza okno na waskich ekranach.

## [1.4.8] - 2026-07-01

### Naprawiono

- Przywrocono poprawny uklad mobilnych zakladek po regresji z wersji 1.4.7:
  dolna nawigacja ponownie dziala jako kontener ekranow, dzieki czemu tresc nie
  zapada sie i nie zjezdza pod dolny pasek.
- Dodano test zrodlowy pilnujacy, zeby `MDBottomNavigation` nie byl ponownie
  skracany jako caly kontener zakladek.

### Zmieniono

- Dopracowano motywowane tlo aplikacji: skosy sa delikatniejsze, wezsze i blizej
  krawedzi, a subtelny efekt poruszajacych sie sniezynek pozostaje bez zmian.

## [1.4.7] - 2026-06-30

### Dodano

- Wstępne ustawienia pod lewą śnieżynką: struktura menu oraz wybór jednostek
  z domyślnym trybem Metric; tryb Imperial/US jest przygotowany, ale wyłączony
  do czasu pełnej konwersji wejść, wyjść i wzorów.
- Walidację skrajnych temperatur z ostrzeżeniami dla nietypowych zakresów oraz
  blokadą wartości poza bezpiecznym zakresem aplikacji.
- Przygotowanie struktury lokalizacji dla PL, EN, ES, FR, IT, PT, JA i ZH z
  angielskim fallbackiem dla języków oczekujących na tłumaczenia.

### Zmieniono

- Zmniejszono wysokość dolnej nawigacji i odstęp do reklamy, zachowując
  minimalny obszar dotyku.
- Ustabilizowano nieprzezroczyste tło aplikacji od pierwszej klatki renderu.
- Poprawiono kierunek animowanego wskaźnika termometru oraz dodano subtelne
  animacje przełączania zakładek dolnego menu.
- Dopasowano przyciski do granatowo-błękitnego motywu aplikacji.

## [1.4.6] - 2026-06-30

### Zmieniono

- Dopasowano mobilny nagłówek do węższych ekranów: śnieżynka jest centrowana
  jak pozostałe ikony, a tytuł aplikacji ma mniejszy font i dwie linie.
- Rozbudowano tło aplikacji o subtelne skośne pasy w kolorach nowego brandu.
- Zastąpiono statyczne ikonki etapów wyniku lekkimi animacjami canvas:
  termometr schładzania, śnieżynka z efektem zamarzania i termometr
  domrażania.

### Dodano

- Testy źródłowe pilnujące nowego układu nagłówka, animowanych ikon wyników
  i brandowego tła.

## [1.4.5] - 2026-06-29

### Zmieniono

- Odświeżono górny panel aplikacji mobilnej: brandowy gradient w kolorach
  nowego logo, lodowa kapsuła śnieżynki oraz półprzezroczyste kapsuły ikon
  akcji.
- Przebudowano ikony etapów w karcie wyników na małe kolorowe badge'e,
  spójne z nową identyfikacją wizualną.
- Delikatnie podkręcono kolory etapów obliczeń, aby lepiej pasowały do
  granatowo-turkusowego motywu aplikacji.

### Dodano

- Test źródłowy pilnujący, aby mobilny nagłówek używał brandowego gradientu,
  a nie starego płaskiego paska.

## [1.4.4] - 2026-06-24

### Zmieniono

- Usunięto właściwości cieplne produktu z mobilnej karty wyników i mobilnego
  PDF. Dane pozostają wewnętrznym wejściem obliczeń i nadal są dostępne w
  aplikacji desktopowej.
- Zmniejszono 39 nadmiarowych grafik produktów z 1024 x 1024 do 512 x 512;
  katalog grafik zmalał z 23,56 do 8,48 MiB.
- Mobilna paczka nie zawiera już materiałów marki i sklepu, znaku wodnego,
  kopii zasobów Androida, kodu desktopowego ani drugiej kopii fontu DejaVu.
- Hook p4a usuwa ze skompresowanego bundla Pythona źródła C i niezgodne
  rozszerzenia natywne `fontTools`, pozostawiając bezpieczny fallback Python.

### Dodano

- Automatyczny raport rozmiaru APK/AAB w artefaktach GitHub Actions.
- Audyt rozmiaru Androida z pomiarami i dalszym planem optymalizacji.

## [1.4.3] - 2026-06-23

### Dodano

- Wyszukiwarkę produktów w nowym, przewijanym oknie wyboru.
- Wyszukiwanie bez rozróżniania wielkości liter i polskich znaków.
- Lokalną sekcję ostatnio używanych produktów dla każdej kategorii.

### Zmieniono

- Długa lista produktów nie jest już klasycznym menu rozwijanym; blokady PRO
  zachowują dotychczasowe zasady i pozycje produktów.

## [1.4.2] - 2026-06-23

### Naprawione

- Skrócono nazwę wyświetlaną pod ikoną do `Refrig Calc`; pełna nazwa marki
  pozostaje bez zmian w aplikacji i Google Play.
- Jawnie włączono edge-to-edge przez aktualne API platformy Android 11+ oraz
  ustawiono bezpieczny tryb wycięcia ekranu `ALWAYS`.
- Zachowano obsługę wcięć pasków systemowych i aparatu bez używania helpera
  AndroidX zawierającego wycofany parametr `SHORT_EDGES`.

## [1.4.1] - 2026-06-22

### Naprawione

- Intro odtwarza teraz zatwierdzony GIF 1:1 przez natywny dekoder Androida,
  bez ponownego rysowania i deformacji logo.
- Pierwsza klatka intro i jego kontener są nieprzezroczyste, dzięki czemu
  interfejs aplikacji nie prześwituje podczas uruchamiania.

### Dodane

- Wydanie testowe działa do końca 15 lipca 2026; po tym terminie blokuje
  funkcje i kieruje do aktualnego wydania w Google Play.
- Dodano finalną grafikę promocyjną Google Play w formacie 1024 x 500 px.

## [1.4.0] - 2026-06-21

### Dodane

- Nowa, zatwierdzona identyfikacja wizualna Refrigeration Calc: warstwowy
  lodowy emblemat, centralny płatek oraz napis `REFRIGERATION CALC`.
- Natywne intro Android trwające 4,6 sekundy z 22 płatkami o różnych
  kierunkach, fazach, rozmiarach i prędkościach. Płatki rosną podczas lotu od
  środka, tworząc efekt głębi.
- Trzy zewnętrzne komety poruszające się po niewidocznych, przesuniętych
  orbitach 8-kątnych. Ich końcowa prędkość została zmniejszona o 30%.
- Gotowe zasoby ikony dla programu uruchamiającego i Google Play oraz podglądy
  najczęstszych masek adaptacyjnych.

### Zmienione

- Systemowy presplash i ikony aplikacji korzystają z jednego zatwierdzonego
  pliku wzorcowego, bez przybliżonych zamienników SVG.
- Zewnętrzne warstwy emblematu zachowują pełne kolory przez całe intro, a
  ścieżki komet nie są rysowane.
- Dokumentacja wydania zawiera aktualną checklistę Play Console, deklaracji
  Firebase i gotowe informacje o wersji w języku polskim i angielskim.

### Naprawione

- Hook Firebase pomija pomocnicze szablony Gradle p4a i konfiguruje wyłącznie
  właściwy projekt aplikacji.
- Log Buildozera jest anonimizowany przed awaryjnym przesłaniem do artefaktów
  GitHub Actions, aby nie zawierał wartości używanych do podpisywania.

## [1.3.2] - 2026-06-21

### Naprawione

- Przełącznik podpowiedzi nie używa już nieobsługiwanej wartości
  `helper_text_mode="none"` w KivyMD 1.2.0, która zamykała aplikację po
  dotknięciu ikony żarówki.
- Skorygowano błędnie przesunięte kolumny danych cieplnych produktów po
  porównaniu wszystkich 206 wierszy z tabelą ASHRAE.
- Workflow debug APK ponawia końcowe pakowanie Gradle z pełnym stack trace,
  jeśli Buildozer zakończy się błędem w `packageDebug`.

### Zmienione

- Techniczne rekordy `*_CTP ALDI` są ukryte wyłącznie na mobilnej liście
  produktów; pozostają dostępne w JSON i aplikacji desktopowej.
- Mobilne menu kategorii pokazuje najpierw owoce i warzywa, następnie
  separator i pozostałe kategorie w kolejności alfabetycznej.
- Uzupełniono katalog o brakujące pozycje ASHRAE i rozdzielono sklejone
  rekordy selera. Szczegóły zawiera `docs/THERMAL_DATA_AUDIT_2026-06-21.md`.

## [1.3.1] - 2026-06-21

### Dodane

- Natywne, responsywne intro Android z animowanym platkiem sniegu, delikatnym
  wirem drobinek, nazwa aplikacji i plynnym przejsciem do interfejsu.
- Intro nie wymaga Lottie ani dodatkowych bibliotek i trwa okolo 1,8 sekundy.
- Subtelne dynamiczne tlo aplikacji: lodowy gradient i wolno dryfujace
  refleksy, zoptymalizowane do 15 klatek na sekunde.
- Nowa ikona aplikacji z przestrzennym lodowo-metalicznym platkiem, przygotowana
  w rozmiarach 512, 192 i 48 px.

### Zmienione

- Systemowy presplash uzywa aktualnej ikony platka i nowego granatowego tla,
  dzieki czemu podczas zimnego startu nie pojawia sie stara nazwa Shocker Calc.
- Obsluga edge-to-edge na Androidzie 15+ korzysta z wymuszanego przez system
  trybu i platformowego `WindowInsets`. Kod aplikacji nie wywoluje juz
  `WindowCompat.enableEdgeToEdge()`, ktory wewnetrznie uzywal wycofanych metod
  kolorowania paskow systemowych.

## [1.3.0] - 2026-06-20

### Dodane

- Opcjonalna, domyslnie wylaczona integracja Firebase Analytics,
  Crashlytics i Remote Config z osobna zgoda uzytkownika.
- Zdarzenia uzycia kalkulatorow i PDF bez przesylania wartosci obliczen,
  nazw produktow ani zawartosci raportow.
- Opcjonalna dystrybucja APK do testerow przez Firebase App Distribution.
- Przelaczane i zapamietywane podpowiedzi dla pol obu kalkulatorow.
- Czerwone oznaczanie brakujacych lub niepoprawnych pol.
- Lokalne produkty uzytkownika dla aktywnej subskrypcji PRO.

### Prywatnosc

- Zbieranie Analytics i Crashlytics pozostaje wylaczone do czasu swiadomej
  zgody i mozna je pozniej wylaczyc w aplikacji.
- Zaktualizowano dwujezyczna polityke prywatnosci oraz instrukcje konfiguracji
  Firebase i deklaracji Play Console.

## [1.2.19] — 2026-06-20

### Techniczne — audyt i odtwarzalny toolchain

- Przypieto stabilne wersje Buildozer `1.6.0`, python-for-android
  `v2026.05.09`, Rust `1.96.0` oraz bezposrednie pakiety Python.
- Zaktualizowano Billing do `9.1.0`, UMP do `4.0.0` i AndroidX Core do
  najwyzszej wersji zgodnej z AGP 8.11 (`1.18.0`).
- Zaktualizowano i przypieto SHA oficjalnych GitHub Actions, eliminujac
  ostrzezenia o wycofaniu runtime Node 20.
- Dodano tygodniowy monitoring aktualizacji Dependabot bez automatycznego
  scalania oraz dokument audytu toolchainu z torem migracji AGP 9.x.

## [1.2.18] — 2026-06-20

### Naprawione — build Android

- Ustawiono AndroidX Core `1.17.0`, czyli pierwsza stabilna wersje z
  `WindowCompat.enableEdgeToEdge()` zgodna z Android Gradle Plugin `8.11`
  dostarczanym przez aktualny python-for-android.

## [1.2.17] — 2026-06-20

### Naprawione — Android 15/16 i Google Play

- Zastapiono wycofane wywolania `setStatusBarColor`,
  `setNavigationBarColor` i reczne `setDecorFitsSystemWindows` przez
  `WindowCompat.enableEdgeToEdge()`, pozostawiajac obsluge wciec paskow
  systemowych i wyciecia ekranu.
- Rozszerzono konfiguracje SDL/Kivy na orientacje pionowa i pozioma (wraz z
  wariantami odwrotnymi), aby uklad mogl adaptowac sie na tabletach i
  urzadzeniach skladanych.
- Hook buildu usuwa odziedziczone `setRequestedOrientation()` z
  `PythonActivity.UnpackFilesTask`, wskazywane przez Play Console jako
  ograniczenie duzych ekranow w Androidzie 16.
- Zaktualizowano Google Mobile Ads SDK do `25.4.0` oraz AndroidX Core do
  wersji zawierajacej nowy interfejs edge-to-edge.

## [1.2.16] — 2026-06-19

### Techniczne — Google Play Console

- Jeśli workflow nie znajdzie osobnych nieobciętych bibliotek `.so`, generuje
  fallback `native-debug-symbols.zip` bezpośrednio z bibliotek obecnych w AAB,
  zachowując poprawną strukturę `lib/arm64-v8a/*.so` dla uploadu testowego w
  Play Console.

## [1.2.15] — 2026-06-19

### Naprawione — Google Play Console

- Generator `native-debug-symbols.zip` filtruje teraz biblioteki po nazwach
  faktycznie obecnych w AAB (`base/lib/.../*.so`) oraz pomija pliki z NDK,
  SDK i cache Gradle. Dzięki temu artefakt symboli nie zawiera bibliotek
  narzędziowych spoza aplikacji.

## [1.2.14] — 2026-06-19

### Techniczne — Google Play Console

- Workflow release generuje teraz `native-debug-symbols.zip` ręcznie z
  nieobciętych bibliotek `.so` znalezionych w katalogach builda p4a, gdy
  Android Gradle Plugin nie utworzy osobnego pliku symboli dla bibliotek
  prebuilt.
- `play-console-diagnostics` zawiera dzięki temu plik możliwy do uploadu w
  osobnej sekcji symboli natywnych Play Console, jeśli ostrzeżenie pozostanie
  po wgraniu samego AAB.

## [1.2.13] — 2026-06-19

### Techniczne — Google Play Console

- Release build dopina `android.buildTypes.release.ndk.debugSymbolLevel =
  SYMBOL_TABLE`, aby App Bundle zawierał natywne symbole debugowania dla
  Android vitals / Play Console.
- Workflow release zbiera dodatkowy artefakt `play-console-diagnostics`
  z plikami diagnostycznymi dla Play Console: `native-debug-symbols.zip`
  (jeśli Gradle wygeneruje go osobno), `mapping.txt` (jeśli R8 zostanie
  włączony) oraz `README.txt`.
- Release p4a/Kivy jawnie pozostaje bez R8-obfuscation (`minifyEnabled false`,
  `shrinkResources false`), więc brak `mapping.txt` nie oznacza utraty danych
  deobfuscation dla obecnego modelu buildu.

## [1.2.12] — 2026-06-19

### Zmienione — Google Play Billing

- PRO przełączono z jednorazowego produktu `pro_no_ads` na miesięczną
  subskrypcję Google Play `refrigeration_pro`.
- Aktywne PRO nadal obejmuje legacy zakup `pro_no_ads`, ale nowy zakup z
  przycisku PRO uruchamia subskrypcję z base planem `monthly-499`.
- Aktywne PRO odblokowuje teraz reklamy-off, pełną listę produktów oraz płatne
  moduły, w tym moduł `module_valves`. Jednorazowy zakup `module_valves`
  pozostaje jako fallback/legacy.
- Zaktualizowano teksty UI na model subskrypcji `PRO 4,99 zł/mies.`.

## [1.2.11] — 2026-06-19

### Naprawione — Google Play Billing

- Synchronizacja płatnego modułu `module_valves` cofa teraz lokalne
  uprawnienie w warstwie Python, gdy Google Play Billing nie zwraca już
  zakupu (np. po zwrocie lub revoke w Play Console). Wcześniej Java czyściła
  flagę Billing, ale lokalny plik uprawnień mógł nadal trzymać moduł jako
  odblokowany.

## [1.2.10] — 2026-06-18

### Techniczne — CI Android

- Rozdzielono instalację Buildozera i Cythona w workflowach Android:
  Buildozer instalowany jest z własnymi zależnościami, a następnie Cython jest
  świadomie nadpisywany do `3.0.11`. Omija to konflikt resolvera pip
  (`buildozer` deklaruje `cython<3.0`, a Kivy 2.3.1 wspiera do `3.0.11`).

## [1.2.9] — 2026-06-18

### Techniczne — CI Android

- Utwardzono krok instalacji zależności systemowych w workflowach Android:
  dodano retry i timeout dla `apt-get`, limit czasu kroku oraz usunięto
  zbędną instalację `openjdk-17-jdk`, ponieważ JDK dostarcza `setup-java`.
  Ma to zapobiegać wielogodzinnym zwisom runnera przed etapem Buildozer.

## [1.2.8] — 2026-06-18

### Techniczne — build Android

- Przypięto Androidowego CPythona do `python3==3.13.14` oraz
  `hostpython3==3.13.14`, aby uniknąć niekompatybilności Kivy z domyślnym
  CPythonem 3.14 w p4a `develop`.
- Podniesiono Kivy z `2.3.0` do `2.3.1` i przypięto Cythona w workflowach
  do `3.0.11`, zgodnie z zakresem wspieranym przez Kivy 2.3.1.
- Ograniczono workflow debugowego APK: tagi `v*` uruchamiają teraz tylko
  workflow podpisanego AAB, żeby nie mnożyć zbędnych runów w GitHub Actions.

## [1.2.7] — 2026-06-18

### Techniczne — build Android

- Dodano brakujące pakiety autotools/libtool (`libtool-bin`, `libltdl-dev`,
  `m4`) do workflowów Android, aby libffi w p4a `develop` mogło przejść
  `autogen.sh` bez błędu `LT_SYS_SYMBOL_USCORE`.

## [1.2.6] — 2026-06-18

### Techniczne — 16 KB page size

- Przełączono Android build na aktualny tor Google Play: `p4a.branch=develop`,
  `android.api=36` oraz `android.ndk=29`, zgodnie z bieżącymi wymaganiami
  Buildozer/python-for-android dla aplikacji publikowanych w sklepie.
- Rozszerzono flagi kompilacji/linkowania dla bibliotek natywnych:
  `LDFLAGS`, `APP_LDFLAGS`, `CFLAGS`, `CXXFLAGS`, `android.extra_cflags`
  i `android.extra_ldflags`, aby wymuszać 16 KB LOAD alignment także tam,
  gdzie biblioteki buduje `ndk-build`.

## [1.2.5] — 2026-06-18

### Techniczne — build Android

- Obniżono `androidx.core:core` z `1.16.0` do `1.15.0`, ponieważ `1.16.0`
  wymaga Android Gradle Plugin `8.6.0`, a obecny stabilny toolchain
  python-for-android generuje projekt z AGP `8.1.1`. `core:1.15.0` obsługuje
  target SDK 35 i jest kompatybilny z obecnym buildem.

## [1.2.4] — 2026-06-18

### Techniczne — build Android

- Poprawiono konfigurację orientacji po nieudanym buildzie `1.2.3`:
  Buildozer nie akceptuje `orientation = all`, więc generator otrzymuje
  poprawną wartość `portrait`, a finalny manifest nadal jest czyszczony przez
  hook p4a z `screenOrientation`, ograniczeń aspect ratio i blokad resize.

## [1.2.3] — 2026-06-18

### Techniczne — uwagi Google Play

- Dodano jawne zależności AndroidX: `androidx.fragment:fragment:1.8.9`
  oraz `androidx.core:core:1.16.0`, aby zastąpić wykrytą przez Play Console
  przestarzałą wersję `androidx.fragment:fragment:1.1.0`.
- Dodano obsługę Android 15 edge-to-edge w natywnej aktywności Android:
  `WindowCompat.setDecorFitsSystemWindows(false)`, przezroczyste system bars
  oraz padding z `WindowInsetsCompat` dla system bars i display cutout.
- Dodano hook p4a, który
  usuwa `screenOrientation`, ograniczenia aspect ratio oraz wymusza
  `resizeableActivity=true` w wygenerowanym `AndroidManifest.xml`.
- Dodano próbę wymuszenia 16 KB LOAD alignment przez linker flag
  `-Wl,-z,max-page-size=16384` oraz raport CI sprawdzający segmenty `LOAD`
  bibliotek natywnych `.so` przez `llvm-readelf`.

## [1.2.2] — 2026-06-15

### Techniczne — Google Play

- Wydanie techniczne bez zmian funkcjonalnych: podbicie wersji aplikacji po tym,
  jak Google Play Console odrzucił ponowny upload pakietu z użytym już
  `versionCode = 11`.
- Nowy release workflow wygeneruje kolejny, wyższy `versionCode`, wymagany przez
  Google Play dla testów zamkniętych i kolejnych ścieżek wydania.
- Ujednolicono wersję pakietu Python (`pyproject.toml`) z wersją Androida i
  stopką aplikacji.

## [1.2.1] — 2026-06-09

### Poprawione — model danych wejściowych kalkulatora zaworów

- **Krytyczna poprawka zgodności z aplikacją referencyjną (desktop)**: zakładka
  zaworów wymagała wcześniej ręcznego podania współczynnika częstości `F`, co
  dawało błędne wyniki. Teraz pola wejściowe odwzorowują aplikację desktopową:
  - przełącznik trybu objętości: **Kubatura** (objętość `V` w m³) /
    **Wymiary** (długość × szerokość × wysokość → `V`),
  - **Ilość chłodnic** (liczba całkowita ≥ 1),
  - **Przepływ na 1 chłodnicę** [m³/h].
- Całkowity przepływ liczony jest jako `F = przepływ_na_1_chłodnicę × ilość_chłodnic`
  i przekazywany do rdzenia `calculate_decompression_valves` (rdzeń bez zmian).
- Wynik pokazuje dodatkowo **przepływ całkowity F [m³/h]**.
- Walidacja: ilość chłodnic ≥ 1, przepływ > 0; nowy pomocnik `_parse_int`.
- i18n PL/EN: nowe klucze (`valve_mode_volume`, `valve_mode_dims`,
  `valve_length`, `valve_width`, `valve_height`, `valve_coolers`,
  `valve_flow_per`, `valve_total_flow`, `valve_coolers_min`,
  `valve_flow_positive`); usunięto `valve_factor`.

## [1.2.0] — 2026-06-09

### Dodane — płatny moduł zaworów (monetyzacja)

- **Gating modułu `module_valves`**: zakładka zaworów jest jednorazowo płatna.
  Dostęp przez: trial (1 dzień, wszystkie moduły), trwały zakup `module_valves`
  albo obejrzenie reklamy rewarded = 1 przeliczenie (token, dzienny limit 8).
  PRO (brak reklam) **nie** odblokowuje modułu — kupowany niezależnie.
- **`entitlements.try_unlock_module_with_token()`** — jednorazowe odblokowanie
  modułu tokenem (token zużywany, moduł nie jest nadawany na stałe). +3 testy
  (suita: 104 testy).
- **Java Billing** (`RefrigerationCalcActivity`): drugi produkt INAPP
  `module_valves` równolegle do `pro_no_ads` — `launchModulePurchase()`,
  `isModuleValvesOwned()`, query/handle/acknowledge/ownership-sync. Gdy produkt
  nie jest jeszcze aktywny w Play Console, zakup pokazuje „niedostępny", a ścieżka
  z reklamą nadal działa.
- **UI zakładki zaworów**: karta blokady z przyciskami „Kup moduł na stałe"
  i „Obejrzyj reklamę (1 przeliczenie)"; synchronizacja własności z warstwą
  Android; lokalizacja PL/EN nowych komunikatów.

## [1.1.0] — 2026-06-09

### Dodane — druga zakładka: zawory dekompresyjne

- **`tpof/core/valves.py`** — czysta logika doboru zaworów dekompresyjnych
  (port z desktopowego repo): `calculate_decompression_valves()` + `ValveResults`,
  słownik `ZAWORY` (Maxi Elebar 4300 l/min, EVO-VERTICAL 1430 l/min), stała `K=3.66`,
  limity bezpieczeństwa i pełna walidacja wejść. Bez pośrednich zaokrągleń.
- **`tests/test_valves.py`** — 22 testy (oba typy zaworów, walidacja, `KeyError`,
  niemutowalność wyniku). Cała suita: 101 testów.
- **Dolna nawigacja** (`MDBottomNavigation`) w stylu Danfoss Ref Tools: zakładki
  **Chłodnicze** (dotychczasowy kalkulator) i **Zawory** (nowy kalkulator).
- Kalkulator zaworów: wybór typu, objętość komory, temperatury przed/po dekompresji,
  współczynnik częstości; wynik = liczba zaworów, ΔT, wymagany przepływ Q.
- Lokalizacja PL/EN nowych etykiet i zakładek.

### Dodane — reklamy per zakładka (AdMob)

- Dedykowane jednostki reklamowe dla zakładki zaworów: baner `/6303778370`,
  rewarded `/1060900411`.
- **`RefrigerationCalcActivity.setActiveAdTab()`** — przy zmianie zakładki baner
  i reklama rewarded przeładowują się na jednostkę przypisaną do aktywnej zakładki
  (`getBannerAdUnitId()` / `getRewardedAdUnitId()` zależne od `activeAdTab`).
- Strona Pythona podpina przełączanie zakładek (`on_switch_tabs`) do mostka Android.
## [Unreleased] — 2026-05-30

### Mobile (Android — Etap A: parytet UI)

#### Dodane
- **`tpof/mobile/main.py`** — pełne UI KivyMD zamiast wcześniejszego stuba:
  - `MDTopAppBar` z przełącznikiem motywu Dark/Light (ikony `weather-night` / `weather-sunny`).
  - Karta **Produkt**: kaskadowy wybór `Kategoria → Produkt` (osobne `MDDropdownMenu`),
    miniaturka produktu (`AsyncImage` z `assets/images/`).
  - Karta **Parametry**: pola masy / T_pocz / T_konc / czasu, przełącznik jednostek
    masy `kg ↔ t` (`MDSwitch`) automatycznie skalujący wartość.
  - Karta **Wynik**: nagłówek z sumą mocy, 3 paski postępu (`MDProgressBar`) dla
    etapów Schładzanie / Zamrożenie / Domrażanie wraz z wartością kW i % udziału,
    siatka właściwości produktu (`c₁`, `c₂`, `L₁`, woda, T_zam z oznaczeniem
    „szacowane" gdy dane brakują).
  - Przyciski **Oblicz** (`MDRaisedButton` z ikoną) i **Wyczyść** (`MDFlatButton`).
  - `Snackbar` dla błędów walidacji zamiast surowych wyjątków na ekranie.
- **`tests/test_mobile_smoke.py`** — 5 testów smoke nie wymagających KivyMD:
  - import `tpof.mobile.main`, istnienie zasobów (`DATA_PATH`, `IMAGES_DIR`),
  - `_safe_image_path` dla istniejących/nieistniejących produktów,
  - poprawne `SystemExit` gdy KivyMD niedostępne.
- **Helper `_safe_image_path()`** — szuka obrazu produktu w `.webp/.png/.jpg/.jpeg`.

#### Zmienione
- Importy KivyMD/Kivy wyizolowane wewnątrz `main()` — dzięki temu pakiet
  `tpof.mobile` można importować na czystym Pythonie (CI, testy, desktop bez Kivy).
- Liczba testów: **47 → 52** (100% pass).

#### Wciąż brakuje do gotowego APK (Etap B + C)
- Pierwszy build Buildozerem w WSL2/Linux (nigdy nie był uruchomiony).
- Testy na fizycznym urządzeniu, podpis release.

### Mobile (Android — Etap A.2: CI + branding + PDF)

#### Dodane
- **`.github/workflows/android.yml`** — pełny workflow buildów APK na GitHub Actions:
  - Ubuntu 22.04 + JDK 17 + Python 3.11 + Buildozer 1.5.0 + Cython 0.29.36.
  - Cache `~/.buildozer`, `~/.gradle` i `.buildozer/` (przyspiesza kolejne buildy ~5×).
  - Uruchamia testy `pytest` przed buildem.
  - Artefakt `shockercalc-debug-apk` (30 dni retencji).
  - Trigger: push do main/master, tag `v*`, PR, oraz manualnie (`workflow_dispatch`).
- **`assets/icon.png`** (512×512) — ikona z płatkiem śniegu, gradient granat → niebieski.
- **`assets/presplash.png`** (1280×1920) — splash screen z logo i napisem
  „Shocker Calc — Obliczenia chłodnicze" (DejaVu Sans).
- **Eksport PDF z mobilnego UI** — nowy przycisk `PDF` w karcie akcji:
  - Używa istniejącego `tpof.core.pdf_report.build_pdf` (pełna zgodność z desktopem).
  - Helper `_pdf_output_dir()` — na Androidzie zapisuje do `/sdcard/Download`,
    z fallbackiem do `ANDROID_PRIVATE`; na desktopie do `cwd`.
  - Nazwa pliku: `ShockerCalc_<Produkt>_<YYYYMMDD_HHMMSS>.pdf`.
  - Snackbar potwierdza ścieżkę zapisu lub raportuje błąd.
- **`tests/test_mobile_smoke.py`** — +1 test (`test_pdf_output_dir_na_desktopie_zwraca_cwd`).

#### Zmienione
- **`buildozer.spec`** — odkomentowane `icon.filename`, `presplash.filename`,
  dodane `android.presplash_color = #1E3C6E` (granatowe tło splasha).
- **`tpof/mobile/main.py`** — karta akcji `Oblicz | PDF | Wyczyść` (3 przyciski
  zamiast 2), `_last_results` zapamiętywane dla eksportu PDF.
- Liczba testów: **52 → 53** (100% pass).

---

## [Unreleased] — 2026-05-29

### Architektura

#### Dodane
- **Pakiet `tpof/`** — nowa, modułowa struktura projektu:
  - `tpof/core/` — czysta logika domenowa (modele, obliczenia, walidacja, I/O, PDF).
  - `tpof/desktop/` — warstwa UI Tkinter + ttkbootstrap (`FreezingCalculatorApp`).
  - `tpof/mobile/` — szkielet pod port KivyMD / Buildozer (Android).
- **`tpof/core/models.py`** — `Product`, `FreezingInputs`, `FreezingResults` jako `@dataclass(frozen=True)` z typami opcjonalnymi.
- **`tpof/core/calculations.py`** — `calculate_freezing()` jako jedyne źródło prawdy dla matematyki.
- **`tpof/core/validators.py`** — `is_positive_number`, `is_valid_temperature`, `parse_number`.
- **`tpof/core/data_loader.py`** — `load_products`, `find_product`, `list_categories`, `list_products`.
- **`tpof/core/formatters.py`** — `format_results_text` (legacy, używany przez PDF).
- **`tpof/core/pdf_report.py`** — generowanie PDF (`build_pdf`, `save_pdf`).
- **`tests/`** — pełen zestaw testów (47 testów, 100% pass).
- **`run.py`** — uruchomienie aplikacji desktop bez instalacji pakietu.
- **`pyproject.toml`** — konfiguracja pakietu (deps, pytest, build).
- **`buildozer.spec`** — szkielet dla przyszłej kompilacji Androida.
- **`archive/backup_pre_refactor_2026-05-29.zip`** — backup stanu sprzed refaktoringu.

#### Usunięte
- Stare pliki na poziomie głównym (po zarchiwizowaniu):
  - `gui.py`, `logika.py`, `obliczenia.py`, `Domrozenie.py`, `cli.py`, `controller.py`, `pdf_generator.py`, `models.py` — przeniesione/przepisane do `tpof/`.
- `project/src/` — eksperymentalny katalog zastąpiony przez `tpof/`.

### UI (desktop)

#### Dodane
- **Modernizacja ttkbootstrap** — przejście z surowego `tk`/`ttk` na ttkbootstrap z motywem `superhero`.
- **Selektor motywów** w nagłówku (`Combobox`) — 10 motywów (5 ciemnych, 5 jasnych).
- **Toggle Dark/Light** — szybki przycisk `☾ Dark / ☀ Light` przełączający między `superhero` ↔ `flatly`.
- **Selektor jednostki masy** kg/t (`Combobox`) obok pola masy — automatyczna konwersja w `_read_inputs`.
- **Floodgauge dla każdego etapu** (Schładzanie / Zamrożenie / Domrażanie) z animacją od poprzedniej do nowej wartości i etykietą `"X.X kW (Y%)"`.
- **Meter** (gauge analogowy) dla mocy całkowitej z auto-skalowaniem (skala podnoszona gdy wynik > 80%).
- **Treeview** z 4 kolumnami (Etap / Q [MJ] / P [kW] / Udział [%]) z:
  - zebra (`stage` / `stage_alt`),
  - wierszem **SUMA** wyróżnionym kolorem `primary` z białą czcionką,
  - ikonami etapów (❄ 🧊 ⛄) i symbolem `Σ` przy SUMA,
  - wysokością wiersza 38 px i czcionką 11 pt.
- **Panel "Parametry produktu"** (po prawej w Wynikach) — Labelframe z dynamicznie generowanymi parami `etykieta : wartość` (c₁, c₂, T_zam, woda, L, skład %).
- **Karta "Produkt"** — zdjęcie produktu, nazwa w bocie info, 3 odznaki (Badge): kategoria / T_zam / H₂O%.
- **Nagłówek aplikacji** — logo (72 px), tytuł 26 pt `primary`, podtytuł kursywą `info`, separator pod nagłówkiem.
- **Pasek statusu** z kolorową kropką ● (zielona/niebieska/żółta/czerwona) zmieniającą się wg poziomu (`success/info/warn/error`) + autor w czerwonym kursywie.
- **Tooltips** (`_add_tooltip`) — żółte dymki nad polami formularza, opisujące co wpisać.
- **Placeholder text** w `Entry` (szary tekst znikający przy focus).
- **`_animate_meter` / `_animate_gauge`** — płynne przejścia wskaźników (20 kroków po 20 ms).
- **`_apply_global_style`** + per-widget `style.configure(tree_style_name, rowheight=38)` — wymusza wysokość wiersza Treeview niezależnie od motywu ttkbootstrap.

#### Zmienione
- Layout główny: `Header → Separator → TopPanels (Form | Product | Meter) → Results (Floodgauges + Treeview + Props)` zamiast monolitycznego pola Text.
- Paddingi: `outer=16`, `top_panels gap=12`, `card padding=10-16`.
- Typografia: jednolity Segoe UI (H1 26, H2 11-12, body 10-11).

#### Usunięte
- **Pole `Text` z wynikami** — zastąpione tabelą Treeview.
- **Funkcje obsługi tagów Text** — `_tag_pattern`, `_tag_full_line_containing`, `_configure_text_tags`, `_apply_text_theme_colors`.
- **Chipy etapów** (proste Label-pigułki) — zastąpione przez `Floodgauge`.

### Logika / matematyka

#### Dodane
- **`_estimate_T_zam(woda_procent)`** — szacowanie punktu zamarzania ze wzoru `T_zam ≈ -0.6 · (100/woda%)` gdy produkt nie ma `T_zam`:
  - 100 % wody → −0.6 °C
  - 50 % → −1.2 °C
  - 20 % → −3.0 °C
  - brak wody → fallback −0.6 °C
- **Walidacja `czas_h > 0`** w `calculate_freezing` — rzuca `ValueError` z czytelnym komunikatem zamiast cichego zwrotu `P=0`.

#### Zmienione
- `calculate_freezing` — gdy `product.T_zam is None`, używa `_estimate_T_zam(product.wodaprocent)` zamiast hardkodowanego `0.0`. Flaga `T_zam_szacunkowy=True` nadal jest ustawiana.

#### Naprawione
- Konwersja masy `t → kg` (×1000) w `_read_inputs` w zależności od `mass_unit_var`.
- `Meter.configure(amountused=...)` — poprawna nazwa atrybutu (`amountusedvar`, nie `amountusedvariable`).
- Floodgauge `mask="{}"` usunięty — blokował wyświetlanie pełnego tekstu `"X.X kW (Y%)"`.
- Treeview `rowheight` — `style.configure("Treeview", ...)` nie działał, bo ttkbootstrap nadaje style typu `success.Treeview`; teraz odczytujemy `cget("style")` i konfigurujemy właściwy styl + reapply przez `after(100)`.
- Sieroty `return card` w `_render_props` (resztka po starym kodzie) — usunięte (powodowały `NameError`).
- Wartości produktu — poprawione mapowanie polskich kluczy JSON na ASCII (`T_zam`, `wodaprocent`, `L1` zamiast `punkt_zamarzania`, `wilgotnosc`).

### Testy

#### Dodane (47 testów, było 26)
- **`TestEdgeCases`** (7 testów): `T_konc=T_zam`, `T_pocz=T_zam`, `T_pocz=T_konc`, brak L1, brak c2, wszystkie dane `None`, masa = 0.
- **`TestSkalowalnoscIProporcje`** (3): podwójna masa → 2× energia, podwójny czas → ½ mocy, suma etapów = `Q_total`.
- **`TestJednostekIKonwersji`** (2): ręczne sprawdzenie `kJ → kW` na próbce 1 kg / 1 h, 1 h vs 24 h.
- **`test_parametryzowane_realne_przypadki`** (2): pełne cykle ze znanymi wynikami liczbowymi.
- **`TestProperties`** (2): nieujemność wszystkich `Q`, monotoniczność względem ΔT.
- **`TestEstimateTzam`** (5): brak wody → fallback, 100 % → −0.6, 50 % → −1.2, monotoniczność.

#### Zmienione
- `test_produkt_bez_punktu_zamarzania_uzywa_zera` → `test_produkt_bez_punktu_zamarzania_szacuje_z_wody` (dostosowane do `_estimate_T_zam`).
- `test_zerowy_czas_daje_zerowa_moc` → `test_zerowy_czas_rzuca_wyjatek` (`pytest.raises(ValueError)`).
- `test_ujemny_czas_traktowany_jak_zero` → `test_ujemny_czas_rzuca_wyjatek`.
- `test_wszystkie_dane_zerowe_lub_None` — sprawdza teraz fallback −0.6 zamiast 0.0.

### Build / packaging
- **`requirements.txt`** + **`requirements-dev.txt`** — rozdzielenie zależności runtime/dev (pytest, pytest-cov).
- **`pyproject.toml`** — `pytest` skonfigurowany (`testpaths`, `rootdir`).
- **`.gitignore`** — Python build artifacts, venv, IDE.
- **`buildozer.spec`** — szkielet dla `pl.smilczarek.refrigerationcalc` (Android).

---

## Pre-refactor (stan zarchiwizowany)
- Monolityczny `gui.py` (Tkinter, ~1500 linii) z logiką, walidacją i I/O wymieszanymi z UI.
- Brak testów.
- Brak struktury pakietu.
- Brak motywów i animacji.
- Brak rozdzielenia core / desktop / mobile.

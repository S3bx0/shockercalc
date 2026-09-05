# Zapis sesji audytowej — 2026-09-05 (handoff dla agentów, np. Codex)

Ten plik jest skondensowanym, ale kompletnym zapisem sesji, w której powstał
[`ARCHITECTURE_PRODUCT_AUDIT_2026-09-05.md`](ARCHITECTURE_PRODUCT_AUDIT_2026-09-05.md).
Służy jako punkt wejścia dla kolejnego agenta lub osoby, która ma kontynuować
prace bez dostępu do oryginalnej rozmowy.

## Linki

| Co | Gdzie |
|---|---|
| Pełny audyt (raport + decyzje + mapa poprawek) | [`docs/ARCHITECTURE_PRODUCT_AUDIT_2026-09-05.md`](ARCHITECTURE_PRODUCT_AUDIT_2026-09-05.md) |
| Ten zapis sesji | `docs/AUDIT_SESSION_2026-09-05.md` |
| Pull request z audytem | <https://github.com/S3bx0/shockercalc/pull/33> |
| Gałąź | `docs/architecture-product-audit-2026-09-05` |
| Audytowany commit `main` | `27bb34a` (tag `v1.5.15`) |
| Surowy odczyt (do czasu scalenia PR) | `https://raw.githubusercontent.com/S3bx0/shockercalc/docs/architecture-product-audit-2026-09-05/docs/ARCHITECTURE_PRODUCT_AUDIT_2026-09-05.md` |
| Surowy odczyt po scaleniu | `https://raw.githubusercontent.com/S3bx0/shockercalc/main/docs/ARCHITECTURE_PRODUCT_AUDIT_2026-09-05.md` |

## Kontekst sesji

- Narzędzie: GitHub Copilot Chat w VS Code (tryb agenta), praca na lokalnej,
  czystej kopii `main` = `27bb34a`; PowerShell na Windows.
- Zlecenie Autora: pełny audyt techniczny i produktowy w 14 etapach z raportem
  w 25 sekcjach (pełna treść zlecenia — Załącznik A). Wyraźny zakaz
  implementowania zmian przed przygotowaniem analizy i roadmapy.
- Zasady pracy obowiązujące w repozytorium, których agent ma się trzymać:
  - **push do `origin` tylko za jawną zgodą Autora**; lokalne commity są
    dozwolone;
  - bramka jakości Python = pełny `pytest` (z progiem pokrycia 50% w
    `pyproject.toml`) + `ruff` + `mypy` (lista `files=` w `pyproject.toml` —
    nowe czyste moduły trzeba tam dopisać); **nie** `compileall`;
  - **realna bramka Kivy/Android = zielony build APK/AAB na GitHub Actions**
    (~15 min); lokalnie Kivy nie jest testowane;
  - moduły `tpof.mobile.*` nie importują klasy aplikacji; Kivy/KivyMD/PyJNIus
    importowane leniwie wewnątrz `open()`/`build()`; typy aplikacji tylko pod
    `TYPE_CHECKING`; dzięki temu 500 testów działa bez Kivy;
  - stałe współdzielone w `tpof/mobile/constants.py` (liść);
  - wzorzec: czysta funkcja/kontroler w module + cienki wrapper w aplikacji;
  - każda zmiana dostaje testy behawioralne; testy asertujące na tekście
    źródła (`... in source`) wymieniać na behawioralne przy okazji, nie
    dodawać nowych;
  - klucze i18n dodawać jednocześnie do słowników PL i EN w
    `tpof/mobile/i18n.py`; polska nazwa produktu z `Table3.json` jest
    kanonicznym kluczem, etykiety EN w `product_labels.py`;
  - wersja występuje w 5 miejscach (`pyproject.toml`, `buildozer.spec`,
    `tpof/__init__.py`, `README.md`, `tests/test_android_build_config.py`);
  - w mypy nie włączać `warn_unused_ignores` (zależne od środowiska).

## Przebieg sesji (chronologicznie)

1. **Rozpoznanie repozytorium.** Weryfikacja stanu Git (`main` =
   `origin/main` = `27bb34a`, drzewo czyste), mapa plików z liczbą linii,
   lektura `README.md`, `pyproject.toml`, `buildozer.spec`, `ROADMAP.md`,
   wybranych dokumentów w `docs/`.
2. **Lektura kodu.** W całości: `tpof/core`, `tpof/labor`, kompozycja mobilna
   (`app.py`, `app_controllers.py`, `shell.py`, `navigation.py`,
   `localization.py`, `layout.py`, `form_interactions.py`, `accessibility.py`),
   stan i dane (`entitlements.py`, `user_data.py`, `settings_state.py`,
   `currency.py`, `telemetry.py`, `android_bridge.py`, `pdf_export.py`,
   `catalog.py`, `product_labels.py`, `constants.py`, `paths.py`),
   koordynatory i workflowy `tabs/`, kontrolery `dialogs/` i `services/`,
   wszystkie klasy Java w `android/src/`, konfiguracja CI i `p4a_hooks.py`.
3. **Pomiary lokalne.** `pytest --no-cov` → 500 passed / 5.05 s; i18n PL 253 /
   EN 253 kluczy bez różnic; `Table3.json` 19 kategorii / 215 produktów
   (7 rekordów `*_CTP ALDI` ukrytych w mobile); 223 commity, 1 autor;
   ~200 asercji testowych na tekście źródła; churn ostatnich 60 commitów
   zdominowany przez `ROADMAP.md`, `test_android_build_config.py`,
   `CHANGELOG.md`, `pyproject.toml`.
4. **Trzy równoległe rozpoznania pomocnicze** (subagenci read-only): desktop
   Tkinter, pipeline CI/łańcuch dostaw, inwentarz testów + i18n. Jedna
   korekta po weryfikacji: teza „0 wpisów CHANGELOG o desktopie” była za
   mocna — poprawnie: ostatnia zmiana `tpof/desktop` 2026-07-05 (baseline
   lint), CHANGELOG od 1.5.4 bez wpisów o desktopie.
5. **Raport** w 25 sekcjach → Część I audytu. Kluczowe wnioski poniżej.
6. **Pytania strategiczne (16)** → Autor odpowiedział na 1, 2, 3 i 6
   (Załącznik B).
7. **Zrewidowany plan** (co zmieniają odpowiedzi, priorytety, kształt F2,
   pierwsze 5 PR) → Część II audytu.
8. **Decyzja Autora: „nic nie poprawiaj, stwórz mapę”** + akceptacja
   parametrów F2 (token = produkt/moduł na 24 h, trial 7 dni, limit
   8 reklam/dobę) → **Mapa poprawek** (bloki A–E) → Część III audytu.
   W tej sesji **nie zmieniono ani jednej linii kodu**.
9. **Publikacja.** Gałąź `docs/architecture-product-audit-2026-09-05`,
   commit `b84c2c0` (audyt + odsyłacz w `ROADMAP.md`), push, PR #33.
   Wybrano PR zamiast pushu na `main`, bo tak wygląda dotychczasowy proces
   repozytorium (PR → zielone checki → merge).
10. **Diagnoza checków PR #33** — dwa czerwone, oba niezależne od treści PR;
    jeden jest blokadą całego pipeline'u (sekcja poniżej).
11. **Ten zapis sesji** dodany do tej samej gałęzi i PR.

## Decyzje podjęte w sesji

| Obszar | Decyzja | Skutek |
|---|---|---|
| Persona | projektant w biurze | rośnie waga historii, wieloproduktu, PDF „dokumentacyjnego”, modułu obciążenia komory; Tkintera nie reaktywować, opcja Kivy-on-Windows później |
| Dane o konwersji | brak (aplikacja w teście zamkniętym) | parametry monetyzacji w jednym `MonetizationPolicy`, lejek Analytics przed produkcją; trial 7 dni jako hipoteza |
| Rynek | 100% pobrań z Polski | PDF i18n → P2 (ale `lang` w modelu raportu od razu), imperialne i 3. język poza roadmapą |
| Tokeny za reklamy | realna ścieżka użycia | F2 hojne; niezawodność reklam rewarded = P0 |
| Parametry F2 | token = produkt/moduł na 24 h, trial 7 dni, limit 8/dobę | do wdrożenia w PR #4 (E1) |
| Zakres tej sesji | tylko analiza i mapa, bez zmian w kodzie | implementacja zaczyna się od bloku A po zgodzie Autora |
| Remote Config | **nie** używać do parametrów monetyzacji | `getRemoteConfigLong` zwraca fallback bez zgody na telemetrię → różne warunki handlowe dla użytkowników bez zgody |

## Najważniejsze ustalenia techniczne (skrót — szczegóły w audycie §7)

1. Brak kanału zdarzeń Java → Python; stan Billing/AdMob/UMP odpytywany
   timerami (`monetization.py:28-29`, `rewarded_access.py:39-40`,
   12× `Clock.schedule_once` w `app.py:248-267`).
2. Token reward zużywany przy każdym przeliczeniu; `pick_valve_type` →
   `calculate()` zużywa token przy zmianie dropdownu.
3. `AdvertisingService.setActiveAdTab` niszczy baner i porzuca załadowaną
   reklamę rewarded przy każdej zmianie karty.
4. PDF tylko po polsku i tylko dla kalkulatora chłodniczego; dwa silniki
   (reportlab / fpdf2); mobilny PDF ukrywa flagę „T_zam szacunkowe”.
5. `settings_state.worker()` nie łapie `http.client.HTTPException` →
   `_refresh_running` zostaje `True` do restartu.
6. Kursy NBP pobierane przy każdym starcie (brak TTL); brak sanity range.
7. Dwa mosty PyJNIus (`telemetry.py` i `android_bridge.py`).
8. `FileShareService`: kopia PDF do publicznych Pobranych przy każdym share;
   `file://` + globalny reset `StrictMode.VmPolicy` na API 24–28.
9. Composition root przez ~150 lambd; 30-argumentowe konstruktory.
10. ~200 asercji testowych na tekście źródła.
11. Własny produkt o nazwie istniejącego zastępuje rekord ASHRAE
    (`user_data.merge_into`); brak edycji/usuwania własnych produktów.
12. Domena robocizny zwraca polskie stringi jako identyfikatory
    (`TRAVEL_MODE_DAILY = "Dojazd dzienny"` trafia do Analytics).
13. Nieatomowy zapis `entitlement.json`; trzy implementacje JSON storage.
14. Martwy kod: `ADMOB_*`, `PRO_SUBSCRIPTION_PRODUCT_ID`,
    `TEMP_LOW_EXTREME_WARNING_C`, `hints.py`, `widgets/menus.py`,
    `services/telemetry_ui.py`.
15. `p4a_hooks.py`: regexy na XML/Java/Gradle bez testów jednostkowych;
    `p4a.branch = master` (commit przypięty).

## Nowe ustalenia z etapu publikacji (nie było ich w audycie)

### B0 — Pipeline APK/AAB jest obecnie trwale czerwony (P0, blokuje wszystko)

Objaw w PR #33 (zmiana wyłącznie `.md`): job „Buildozer (debug APK)” kończy
się po ~2 min komunikatem
`sdkmanager path ".../android-sdk/tools/bin/sdkmanager" does not exist`.

Mechanizm (potwierdzony w logu przebiegu `33953024408` i w workflow):

1. `actions/cache/restore` (`android.yml:102`, `android-release.yml:92`) —
   **tylko restore**, nigdzie nie ma `actions/cache/save`; ostatni zielony
   build `main` był 2026-08-09, GitHub usuwa cache nieużywany przez 7 dni;
   `gh cache list` zwraca pustą listę → cache jest **na stałe zimny**.
2. Krok „Pre-accept Android SDK licenses” (`android.yml:137-145`,
   `android-release.yml:130-137`) robi
   `mkdir -p ~/.buildozer/android/platform/android-sdk/licenses` **przed**
   uruchomieniem Buildozera.
3. Buildozer widzi istniejący katalog → loguje „Android SDK found at …” →
   pomija pobranie SDK → brak `tools/bin/sdkmanager` → błąd.

Do czasu naprawy **każdy** build debug i release będzie czerwony, więc nie ma
działającej bramki Kivy dla żadnego PR z kodem. Proponowana naprawa (mała,
w obu workflowach):

- zapisywać licencje tylko wtedy, gdy SDK faktycznie istnieje
  (`if [ -x ~/.buildozer/android/platform/android-sdk/tools/bin/sdkmanager ]`),
  a w przeciwnym razie pozwolić Buildozerowi pobrać SDK — `( yes || true ) |
  buildozer …` już akceptuje licencje interaktywnie; **albo** pobrać SDK jawnie
  (commandline-tools) przed krokiem licencji;
- rozważyć przywrócenie zapisu cache dla `~/.buildozer/android/platform/
  {android-sdk,android-ndk-r29,apache-ant-1.9.4}` (uwaga na limit dysku
  runnera opisany w `ROADMAP.md` P0.4) — bez zapisu krok restore jest martwy;
- dodać test charakteryzujący workflow (parser YAML) pilnujący, że krok
  licencji jest warunkowy.

### Dependency audit — 3 nowe CVE w pypdf 6.15.0

`pip-audit` zgłasza CVE-2026-84309, CVE-2026-84310, CVE-2026-84311 (poprawka
w 6.16.1). Dependabot otworzył już PR #32 (`pypdf 6.15.0 → 6.16.1`). Do czasu
scalenia #32 job „Dependency audit” będzie czerwony także na `main`. Uwaga
z audytu (E2): docelowo pypdf i reportlab mają zniknąć z zależności na rzecz
jednego silnika fpdf2.

### Stan checków PR #33 w chwili zapisu

| Check | Wynik | Uwaga |
|---|---|---|
| Tests + Ruff + mypy | pass | |
| Secret scan | pass | |
| Dependency Review | pass | |
| CodeQL (python, java-kotlin) | pass | |
| Dependency audit | **fail** | pypdf CVE — PR #32 |
| Buildozer (debug APK) | **fail** | B0 — zimny cache + krok licencji |

Otwarte PR Dependabota w chwili zapisu: #32 (pypdf), #31 (akcje GitHub),
#30 (grupa python minor/patch), #3 (`actions/cache` 6.1.0).

## Następne kroki dla kolejnego agenta (kolejność)

0. **Naprawić B0** w `android.yml` i `android-release.yml` (osobny, mały PR),
   scalić PR #32 (pypdf) i uzyskać zielony build APK na `main`. Bez tego nie
   ma bramki dla żadnego PR z kodem. Nie łączyć tej naprawy z PR #33.
1. Scalić PR #33 (dokumentacja).
2. **PR #1 — blok A** z audytu (tylko Python, bramka lokalna
   pytest/ruff/mypy): A1 fail-safe worker kursów, A2 TTL na `fetched_at`,
   A3 sanity range, A4 `calculate(enforce_access=False)` w
   `pick_valve_type`, A5 atomowy `Entitlements._save`, A6 ASCII nazwa PDF,
   A7 martwy kod, A8 `log.warning` w moście. Każda pozycja z testem.
3. **PR #2 — blok B1/B2/B3** (Java + CI; bramka = APK + urządzenie).
4. **PR #3 — blok C** (`events.py`, `NativeEventQueue`, `NativeEventPump`,
   porty, usunięcie timerów).
5. **PR #4 — E1** (sesje odblokowania 24 h, `MonetizationPolicy` z trialem
   7 dni, auto-kontynuacja, lejek Analytics).
6. **PR #5 — E2** (`tpof/reports`, fpdf2, `lang` w modelu, pola projektu,
   PDF dla zaworów i robocizny).
7. Potem E3 historia → E4 wieloprodukt → E5 moduł komory.

Reguły: jeden blok = jeden PR; żadnej nowej funkcji (blok E) przed C3 i E1;
wymieniać testy tekstowe w PR, który je rusza; push tylko za zgodą Autora.

## Pułapki, na które agent powinien uważać

- Testy w `tests/test_mobile_smoke.py` i `tests/test_mobile_app_composition.py`
  asertują na **tekście** `app.py`, `app_controllers.py`, `layout.py`,
  `shell.py` itd. — każda zmiana w tych plikach może wymagać aktualizacji
  asercji; zamieniać je na testy zachowania, nie dopisywać kolejnych.
- `tests/test_android_build_config.py` asertuje na tekście Javy i
  `buildozer.spec`; test `test_release_version_is_consistent` pilnuje wersji
  w 3 plikach.
- Indeks „darmowego produktu” liczony jest w dwóch miejscach na dwóch różnych
  listach (przefiltrowana vs surowa) — zgadza się tylko przypadkiem (D1).
- `FirebaseTelemetryService.getRemoteConfig*` zwraca fallback bez zgody na
  telemetrię — nie sterować tym niczym handlowym.
- `p4a_hooks.py` łata `AndroidManifest.xml`, `PythonActivity.java` i
  `build.gradle` regexami; zmiany w manifeście (np. `FileProvider` w B2)
  dodawać przez istniejący wzorzec `_patch_*` i najpierw pokryć testem na
  fixture.
- Na Windows skrypty pomocnicze uruchamiać w PowerShell (brak `bash`
  heredoc); wieloliniowe komunikaty commitów przez plik (`git commit -F`).

## Załącznik A — oryginalne zlecenie Autora (treść bez zmian, formatowanie Markdown)

<details>
<summary>Rozwiń pełną treść zlecenia</summary>

Chcę, żebyś wcielił się w rolę Senior Software Architect + Staff Engineer +
Product Engineer + Code Reviewer i przeprowadził bardzo dokładny audyt mojego
projektu znajdującego się w repozytorium GitHub.

Repozytorium: https://github.com/S3bx0/shockercalc

**GŁÓWNY CEL**

Nie chcę powierzchownej analizy ani ogólnych porad. Twoim zadaniem jest:

1. pobrać / otworzyć całe repozytorium,
2. bardzo dokładnie zapoznać się z projektem,
3. zrozumieć jego architekturę,
4. zrozumieć przepływ danych i logikę biznesową,
5. znaleźć problemy techniczne i architektoniczne,
6. ocenić istniejące funkcjonalności,
7. wskazać funkcje, które należy poprawić,
8. znaleźć funkcje, które są źle zintegrowane z resztą programu,
9. zaproponować lepszy sposób ich integracji,
10. znaleźć brakujące funkcjonalności,
11. zaproponować kierunek dalszego rozwoju projektu,
12. przygotować konkretną roadmapę rozbudowy.

Nie oceniaj projektu wyłącznie na podstawie README. Musisz przeanalizować
rzeczywisty kod.

**ETAP 1 — ZROZUMIENIE PROJEKTU**

Najpierw dokładnie przejrzyj strukturę repozytorium. Przeanalizuj między
innymi: wszystkie główne katalogi, pliki konfiguracyjne, package.json /
requirements / pyproject / composer / Cargo / inne zależności, backend,
frontend, bazę danych, modele danych, API, routing, middleware, autoryzację,
system użytkowników, integracje zewnętrzne, komponenty UI, state management,
utility functions, serwisy, hooki, kolejki, cache, cron jobs, WebSockety,
AI / LLM integrations (jeżeli występują), testy, Docker, CI/CD, deployment,
zmienne środowiskowe, obsługę błędów, logging, monitoring, bezpieczeństwo.
Jeżeli projekt jest duży, analizuj go modułami. Nie pomijaj plików tylko
dlatego, że na pierwszy rzut oka wydają się mało istotne.

**ETAP 2 — WYJAŚNIJ MI, JAK DZIAŁA MÓJ PROGRAM**

Po analizie przedstaw mi projekt tak, jakbyś tłumaczył go nowemu Senior
Developerowi dołączającemu do zespołu. Opisz: 1. Architektura (jak zbudowany
jest projekt, główne moduły, za co odpowiadają, jak się komunikują). 2. Flow
aplikacji (główne ścieżki wykonywania, np. user → frontend → API → service →
database → response; dla najważniejszych funkcjonalności dokładny przepływ).
3. Zależności (które moduły zależą od których, zbyt mocne sprzężenie,
rozproszona logika, nachodzące odpowiedzialności). 4. Model danych
(najważniejsze encje, relacje, problemy struktury danych, miejsca trudne do
skalowania).

**ETAP 3 — AUDYT KODU**

Bardzo szczegółowy code review. Każdy problem oznacz priorytetem: 🔴 CRITICAL,
🟠 HIGH, 🟡 MEDIUM, 🟢 LOW / NICE TO HAVE. Dla każdego problemu podaj: plik,
funkcję / klasę / komponent, na czym polega problem, dlaczego jest problemem,
możliwe konsekwencje, proponowane rozwiązanie, czy wymaga refaktoryzacji, jak
duży jest zakres zmian. Szukaj między innymi: spaghetti code, duplicated code,
God Objects, God Components, zbyt dużych funkcji, źle nazwanych funkcji,
niepotrzebnej złożoności, złego podziału odpowiedzialności, mieszania logiki
biznesowej z UI i z kontrolerami, błędnego zarządzania stanem, circular
dependencies, niepotrzebnych zależności, dead code, nieużywanych funkcji,
powtarzalnych requestów, N+1 queries, problemów z async, race conditions,
memory leaks, niepoprawnego cache, złego error handling, silent errors, złego
logowania, potencjalnych security vulnerabilities, problemów wydajnościowych,
miejsc utrudniających rozwój projektu.

**ETAP 4 — FUNKCJONALNOŚCI, KTÓRE JUŻ ISTNIEJĄ**

Tabela wszystkich istotnych funkcjonalności: co robi, gdzie jest
implementacja, jakość implementacji 1–10, integracja z resztą systemu 1–10,
UX 1–10, wydajność 1–10, skalowalność 1–10, testowalność 1–10, czy wymaga
przebudowy. Następnie wybierz funkcjonalności do przebudowy w pierwszej
kolejności.

**ETAP 5 — FUNKCJE ŹLE ZINTEGROWANE Z PROGRAMEM**

Znajdź funkcjonalności, które działają, ale wyglądają jak „doklejone”,
duplikują logikę, mają własne mechanizmy zamiast wspólnej architektury,
omijają wspólne serwisy, mają niewłaściwy przepływ danych, powinny korzystać
z eventów / service layer / API / shared state / cache / kolejki, są zbyt
mocno powiązane z UI, nie wykorzystują istniejących danych programu, powodują
niespójność UX lub logiki. Dla każdej pokaż: OBECNIE (A → B → C), PROBLEM,
LEPIEJ (A → Shared Service → B → C). Następnie szczegółowo wyjaśnij
proponowaną architekturę.

**ETAP 6 — CO MOŻNA UPROŚCIĆ**

Kod do znaczącego skrócenia, niepotrzebne abstrakcje, nadmiarowe warstwy,
własne rozwiązania problemów rozwiązanych przez framework, zbyt wiele
requestów, zbyt wiele stanów, duplikowanie danych, miejsca gdzie jedna dobra
abstrakcja zastąpi wiele implementacji. Każda zmiana musi mieć praktyczny
powód.

**ETAP 7 — BRAKUJĄCE FUNKCJONALNOŚCI**

Podział: MUST HAVE, HIGH IMPACT, UX IMPROVEMENTS, POWER USER FEATURES,
AUTOMATION, AI FEATURES (jeżeli mają sens; nie na siłę), ADMIN / ANALYTICS,
SCALABILITY (10× / 100× użytkowników).

**ETAP 8 — DLA KAŻDEJ NOWEJ FUNKCJI POKAŻ INTEGRACJĘ**

Dla każdej funkcji: nazwa, jaki problem rozwiązuje, dlaczego warto, jak
działa z perspektywy użytkownika, jak działa technicznie, z jakimi modułami
się integruje, przepływ danych, zmiany backend / frontend / baza danych,
background jobs / cache / WebSocket / queue / cron, edge-case'y, problemy
bezpieczeństwa, trudność S / M / L / XL, wartość biznesowa 1–10, priorytet
P0 / P1 / P2 / P3.

**ETAP 9 — ARCHITEKTURA DOCELOWA**

Ewolucyjna refaktoryzacja, nie rewrite. OBECNA vs PROPONOWANA architektura,
struktura katalogów dostosowana do projektu.

**ETAP 10 — ROADMAPA**

Techniczna roadmapa: FAZA 0 QUICK WINS, FAZA 1 STABILIZACJA, FAZA 2
REFAKTORYZACJA FUNDAMENTÓW, FAZA 3 POPRAWA ISTNIEJĄCYCH FUNKCJI, FAZA 4 NOWE
FUNKCJE, FAZA 5 SKALOWANIE. Dla każdego zadania: priorytet, zależności,
ryzyko, trudność, wartość, zakres zmian, konkretne pliki lub moduły.

**ETAP 11 — TOP 20 NAJWAŻNIEJSZYCH ZMIAN**

Ranking 20 rzeczy, które zrobiłbyś jako Lead Developer od jutra (dlaczego,
wpływ, trudność, ryzyko, co zmienić). Uwzględnić zmiany strategiczne.

**ETAP 12 — RZECZY, KTÓRYCH NIE POWINIENEM TERAZ ROBIĆ**

Unikać overengineeringu, przepisywania działającego systemu, przedwczesnych
mikroserwisów, niepotrzebnych abstrakcji, migracji technologii bez korzyści.

**ETAP 13 — RYZYKA**

Techniczne (scalability, security, maintainability, performance, reliability,
data integrity) i produktowe (UX, brakujące funkcje, skomplikowany flow,
funkcjonalności o niskiej wartości).

**ETAP 14 — PYTANIA, KTÓRE POWINIENEM SOBIE ZADAĆ**

10–20 pytań strategicznych.

**BARDZO WAŻNE ZASADY**

1. Nie zgaduj — jeśli czegoś nie można potwierdzić z kodu, napisać „Nie mogę
   tego potwierdzić na podstawie obecnego kodu.” 2. Nie dawać generycznych
   porad — konkretny plik, funkcja, skutek, propozycja. 3. Odwoływać się do
   konkretnych plików i funkcji. 4. Patrzeć na projekt jako całość.
5. Nie proponować mikroserwisów. 6. Nie proponować zmiany frameworka bez
   bardzo mocnego uzasadnienia. 7. Nie proponować pełnego rewrite'u bez
   krytycznego powodu. 8. Preferować rozwiązania proste, modularne, skalowalne,
   testowalne, łatwe w rozwoju. 9. Oddzielać BUG / TECH DEBT / ARCHITECTURE
   PROBLEM / UX PROBLEM / PERFORMANCE PROBLEM / SECURITY PROBLEM / NEW FEATURE.
10. Uwzględniać zależności między zmianami.

**TRYB PRACY**

Kolejność: 1. Repository discovery, 2. Architecture discovery, 3. Feature
discovery, 4. Data-flow discovery, 5. Dependency analysis, 6. Code-quality
audit, 7. Security audit, 8. Performance audit, 9. Existing feature analysis,
10. Product-gap analysis, 11. Architecture recommendations, 12. Roadmap.
Najpierw pełny obraz, dopiero potem ocena.

**FORMAT KOŃCOWEGO RAPORTU**

1. Executive Summary, 2. Co robi aplikacja, 3. Architecture Map,
4. Repository Map, 5. Najważniejsze przepływy danych, 6. Ocena obecnej
architektury, 7. Największe problemy, 8. Security, 9. Performance, 10. Code
Quality / Technical Debt, 11. Ocena istniejących funkcjonalności, 12. Funkcje
wymagające przebudowy, 13. Funkcje źle zintegrowane, 14. Jak poprawić
integrację funkcji, 15. Brakujące funkcjonalności, 16. Proponowane nowe
funkcjonalności, 17. Docelowa architektura, 18. Proponowana struktura
projektu, 19. Quick Wins, 20. Roadmapa rozwoju, 21. TOP 20 zmian, 22. Czego
obecnie nie robić, 23. Największe ryzyka, 24. Pytania strategiczne,
25. Rekomendowana kolejność prac.

**NAJWAŻNIEJSZE**

Traktować to jako: „Dostałeś istniejący produkt i od teraz odpowiadasz za
jego stronę techniczną. Musisz zrozumieć go na tyle dobrze, aby zaplanować
jego rozwój na kolejne miesiące bez niszczenia tego, co już działa.” Nie
zaczynać implementować zmian. Najpierw pełna analiza i roadmapa. Po
zakończeniu raportu wskazać „Pierwsze 5 zmian, które powinniśmy wspólnie
zaimplementować” i dla każdej napisać, dlaczego od niej warto zacząć.

</details>

## Załącznik B — odpowiedzi i polecenia Autora w trakcie sesji (pisownia ujednolicona)

1. *Kto jest głównym użytkownikiem: serwisant/instalator na obiekcie czy
   projektant w biurze?* — **projektant w biurze**.
2. *Czy 1-dniowy trial ma dane potwierdzające konwersję?* — **nie ma; nie ma
   jak sprawdzić, program nie wyszedł z testów**.
3. *Jaki jest udział EN w instalacjach?* — **nie ma miarodajnej liczby pobrań;
   na razie wszystkie pobrania z Polski**.
4. *Czy tokeny za reklamy mają być realną ścieżką użycia, czy tylko „nudge”
   do PRO?* — **realna ścieżka**.
5. Na propozycję rozpoczęcia PR #1: **„Nic nie poprawiaj, stwórz tylko mapę,
   co należy poprawić i ewentualnie jakie techniki zastosować.”**
6. Parametry F2: wybrano **„Token = produkt/moduł na 24 h, trial 7 dni,
   limit 8/dobę”**.
7. **„Wstaw mi to wszystko na GitHuba jako nowy audyt.”** → PR #33.
8. **„Zapisz całą dzisiejszą sesję z linkiem do odczytu, np. przez Codex.”**
   → ten plik.

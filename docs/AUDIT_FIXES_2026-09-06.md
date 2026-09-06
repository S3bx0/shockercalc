# Pierwszy pakiet poprawek audytu — 2026-09-06

Zakres: preflight CI, A1 (odświeżanie kursów), A3 (walidacja kursów/cache).
Baza: `27bb34a85db47f81647410b776c74f1211956734` (`main`, v1.5.15).
Gałąź: `codex/audit-preflight-currency`. Bez scalenia, tagowania i publikacji
w Google Play; kontrolny debug APK wymaga osobnej bramki CI.

## Zmiany i niezmienniki

1. `settings_state.py`: błędy loadera kończą się callbackiem z zachowanym
   snapshotem, bez niechronionego ponownego odczytu cache. Obsłużono błędy
   startu wątku, planowania i callbacku. Worker nie wywołuje funkcji UI.
   Generacja żądania odrzuca spóźnione callbacki po zmianie ustawień; blokada
   serializuje pobranie/zapis kolejnych żądań. Wyłączenie auto-update nie
   anuluje już rozpoczętego połączenia HTTP, ale unieważnia jego wynik dla UI.
2. `currency.py`: sieć i cache korzystają ze wspólnej walidacji dodatniego,
   skończonego Decimal i rzeczywistej daty ISO. Wymagane są kod odpowiedzi
   zgodny z żądaniem oraz komplet PLN/EUR/USD w cache (PLN = 1). Niepoprawny
   snapshot nie nadpisuje poprawnego pliku. Obsłużono `HTTPException`, w tym
   `IncompleteRead` i `BadStatusLine`. Nie stosujemy zakresu 2–10 PLN.
3. CI Android: usunięto krok tworzący `android-sdk/licenses` przed instalacją
   SDK. Buildozer 1.6.0 sprawdza tylko istnienie katalogu SDK, więc taki krok
   blokował pobranie narzędzi na pustym cache. Nowy helper nie tworzy katalogu
   na cache miss, zachowuje kompletny SDK, a niekompletny przenosi pod unikalną
   nazwę w tym samym katalogu platformy. Niczego nie usuwa; odmawia przenoszenia
   przekierowanej ścieżki. `android.accept_sdk_license = True` przekazuje
   obsługę licencji Buildozerowi po pobraniu narzędzi.

Źródło kontraktu SDK:
[Buildozer 1.6.0, android.py](https://github.com/kivy/buildozer/blob/1.6.0/buildozer/targets/android.py).
Schemat odpowiedzi kursów: [API NBP](https://api.nbp.pl/).

## Poprawka znanej podatnej zależności PDF

Status lokalny: **fixed — przypięta zależność**, nie dowód usunięcia
osiągalnego exploita aplikacji. Trzy aktywne deklaracje pypdf zostały
zaktualizowane z 6.15.0 do 6.16.1 (`pyproject.toml`, `requirements.txt`,
`requirements-mobile.txt`), razem z wpisem pypdf w `THIRD_PARTY_NOTICES`.
Jest to ten sam trójplikowy update co Dependabot PR #32; tego PR nie scalamy
ani nie zamykamy automatycznie.

Zakres upstream:

- [CVE-2026-84309](https://github.com/py-pdf/pypdf/security/advisories/GHSA-jp53-mhqp-8xcg): cykliczne drzewa, poprawka od 6.16.0;
- [CVE-2026-84310](https://github.com/py-pdf/pypdf/security/advisories/GHSA-23w6-3w8w-8484): kosztowne przechodzenie outline, poprawka od 6.16.1;
- [CVE-2026-84311](https://github.com/py-pdf/pypdf/security/advisories/GHSA-763m-79hh-57f2): kosztowne XForms przy ekstrakcji tekstu, poprawka od 6.16.1.

W aplikacji `PdfReader` przetwarza wewnętrznie wygenerowane przez ReportLab
bajty raportu/znaku wodnego. Nie znaleziono importu zewnętrznych PDF ani
produkcyjnych wywołań outline/ekstrakcji tekstu. Nie wykazano zatem osiągalnej
ścieżki ataku w aplikacji; poprawka usuwa zadeklarowaną podatną wersję.
Natywny Android nadal używa fpdf2 i nie zawiera pypdf w manifeście zależności.

Zachowano publiczne API raportu, opcjonalny znak wodny, zachowanie brakującej
grafiki i zgodność sygnatur szyfrowania. Hasło właściciela nadal nie wymaga
hasła do otwarcia raportu i nie stanowi ochrony poufności. Nie zmieniano
fallbacku `PyPDF2` w niezarządzanych starszych instalacjach.

## Weryfikacja lokalna

Python 3.13.12, osobny venv z przypiętymi wymaganiami i pypdf 6.16.1:

- 83 testy skupione na kursach, kontrolerze ustawień, bootstrapie i PDF PASS;
- pełny pytest: 565 PASS, coverage 57,81% przy wymaganych 50%;
- Ruff PASS; mypy skonfigurowany 52 pliki PASS, pełny projekt 163 pliki PASS;
- pip-audit: shared, mobile, Android oraz dev — bez znanych podatności;
  dla mobile/Android sprawdzane są bezpośrednie piny, tak jak w istniejącym CI;
- rzeczywisty eksport PDF: z grafiką produktu, bez/z watermarkiem, bez/z hasłem
  właściciela; odczyt stron i polskiej nazwy produktu oraz otwarcie z pustym
  hasłem użytkownika PASS;
- testy uszkodzonego cache, NaN/sNaN/Infinity, dat i kodów walut, częściowej
  odpowiedzi HTTP, wyjątków workera/UI oraz spóźnionych callbacków PASS.

Nie uruchamiano złośliwych PDF ani testu DoS. Kontrolą bezpieczeństwa są
zgodność wszystkich pinów z poprawką upstream i audyt zależności; kontrolą
regresji są prawdziwe raporty oraz dotychczasowe testy kompatybilności.

Niezależny przegląd tylko do odczytu nie wykazał regresji produkcyjnej,
ale wykrył zbyt słabą asercję watermarku: sama ikona produktu spełniała test
obecności obrazu. Test zaostrzono do wymagania dodatkowego obrazu watermarku.

Pozostałe ograniczenia: pypdf ostrzega o przyszłym usunięciu sposobu scalania
stron w wersji 7.0 (dwa DeprecationWarning w testach watermarku); przy obecnym
przypięciu 6.16.1 testy przechodzą. Przed migracją na 7.x potrzebny osobny PR.
Sukces lokalnych testów nie potwierdza budowy/uruchomienia APK, AAB, urządzenia
ani procesu testów zamkniętych Google Play. Wersja aplikacji pozostaje 1.5.15.

## Dalsza kolejność

A2 (TTL 6 h jako decyzja aplikacji, nie wymóg NBP) z jawną akcją odświeżania;
pozostałe poprawki bloku A; osobno migracja uprawnień/tokenów i cykl reklam.
Poprawki audytu dokumentacyjnego w PR #33 pozostają oddzielone od tego pakietu.

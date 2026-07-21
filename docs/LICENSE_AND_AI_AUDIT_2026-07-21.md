# Audyt licencji i zastrzeżenia AI/TDM — 2026-07-21

## Decyzja

Refrigeration Calc pozostaje oprogramowaniem własnościowym udostępnionym
źródłowo wyłącznie do ograniczonego wglądu. Projekt nie przechodzi na GPL-3.0,
ponieważ GPL przyznawałaby odbiorcom prawo do uruchamiania, modyfikowania i
rozpowszechniania programu oraz nie pozwalałaby dodać ogólnego zakazu AI jako
dalszego ograniczenia.

## Wprowadzony podział

- `LICENSE` — prawa do materiałów należących do Autora i ograniczony wgląd w
  kod źródłowy.
- `EULA` — prawo użytkownika do instalowania i używania oficjalnej aplikacji.
- `AI_USAGE_POLICY` — wyraźne zastrzeżenie AI i text-and-data mining.
- `THIRD_PARTY_NOTICES` — komponenty, wersje, licencje i źródła.
- `legal/GPL-3.0-only` i `legal/LGPL-3.0-only` — pełne teksty wymagane przez
  LGPL-3.0 używaną przez `fpdf2`.
- `REUSE.toml`, `LICENSES/` i `.well-known/tdmrep.json` — oznaczenia
  maszynowo czytelne.

Dokumenty są dostępne offline z ustawień aplikacji. Workflow wydania sprawdza,
czy wymagane pliki rzeczywiście znalazły się w `assets/private.tar` wewnątrz
AAB.

## Najważniejsze zależności Androida

| Komponent | Wersja | Licencja / warunki |
| --- | ---: | --- |
| Kivy | 2.3.1 | MIT oraz osobne licencje zasobów |
| KivyMD | 1.2.0 | MIT oraz osobne licencje fontów/ikon |
| Pillow | 11.3.0 | MIT-CMU |
| fpdf2 | 2.8.7 | LGPL-3.0-only |
| fontTools | 4.63.0 | MIT |
| defusedxml | 0.7.1 | PSF |
| certifi | 2026.6.17 | MPL-2.0 |
| Google/Android SDK | wersje z `buildozer.spec` | warunki Google/Android i licencje komponentów |

Licencje zależności przechodnich Pythona pozostają również osadzone w ich
katalogach `*.dist-info` w `libpybundle.so`.

## Ograniczenia zastrzeżenia AI

Żaden plik w repozytorium nie może technicznie wymusić odmowy każdego modelu
AI. Polityka zwiększa czytelność zastrzeżenia i podstawę prawną, ale jej
egzekwowanie zależy od prawa, umowy i zachowania operatora systemu.

Publiczne repozytorium GitHub podlega również warunkom GitHuba. Zgodnie z
aktualnymi warunkami publiczne udostępnienie pozwala użytkownikom korzystać z
funkcji wyświetlania i forkowania w ramach platformy, a GitHub otrzymuje
określone prawa do treści. Własna licencja nie cofa praw udzielonych w umowie z
platformą.

Jeżeli nadrzędnym celem stanie się maksymalne ograniczenie pobierania przez
zewnętrzne systemy, repozytorium powinno zostać ustawione jako prywatne, a do
portfolio należy publikować osobny, ograniczony materiał.

## Pozostałe działania

1. Przed publikacją nowych warunków na głównej gałęzi zlecić krótki przegląd
   prawnikowi zajmującemu się prawem autorskim i licencjami oprogramowania.
2. Przy każdej zmianie zależności aktualizować `THIRD_PARTY_NOTICES`.
3. Dla każdej wersji wydanej użytkownikom zachować odpowiadający tag źródłowy
   i skrypty budowania wymagane do realizacji praw LGPL.
4. Rozważyć zastąpienie `fpdf2` biblioteką na licencji permisywnej, jeśli
   obsługa obowiązków LGPL okaże się nieproporcjonalnie kosztowna.
5. Nie traktować samej licencji jako zabezpieczenia sekretów — klucze, dane
   uwierzytelniające i niepubliczna logika powinny pozostawać poza publicznym
   repozytorium.

Dokument jest audytem techniczno-licencyjnym, a nie opinią prawną.

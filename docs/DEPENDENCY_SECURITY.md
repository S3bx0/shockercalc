# Bezpieczeństwo zależności

## Ustawienia GitHub

Stan potwierdzony 8 sierpnia 2026 r. dla `S3bx0/shockercalc`:

- Dependency Graph jest aktywny i zasila analizę manifestów;
- Dependabot Alerts są aktywne;
- Dependabot Security Updates są aktywne;
- automatyczne poprawki bezpieczeństwa mogą otwierać PR, ale nie są
  automatycznie scalane;
- Secret Scanning i Push Protection pozostają aktywne.

Zmiana tych ustawień odbywa się w `Settings -> Advanced Security`. Plik
`dependabot.yml` steruje aktualizacjami wersji, ale nie zastępuje włączenia
alertów oraz Security Updates w ustawieniach repozytorium.

## Polityka PR

Workflow `Dependency Review` uruchamia się dla każdego PR do `main` lub
`master` i blokuje dodanie zależności ze znaną podatnością o poziomie
`moderate`, `high` albo `critical`.

Akcja ma wyłącznie uprawnienie `contents: read`. Nie publikuje komentarzy,
nie zmienia kodu i nie scala PR. Jej wersja jest przypięta do pełnego SHA
commita, aby tag akcji nie mógł zmienić wykonywanego kodu.

Kontrola licencji pozostaje informacyjna. Nie ustawiamy jeszcze globalnej
allowlisty ani denylisty, ponieważ najpierw trzeba zatwierdzić kompletną
politykę licencyjną dla zależności Kivy, python-for-android i Android SDK.

## Dependabot

Zwykłe aktualizacje `minor` i `patch` są grupowane osobno dla Pythona i
GitHub Actions. Reguły mają jawne `applies-to: version-updates`, dzięki czemu
pilne poprawki bezpieczeństwa pozostają osobnymi, łatwymi do przejrzenia PR.
Aktualizacje główne oraz wszystkie PR-y bezpieczeństwa wymagają testów i
ręcznej decyzji o scaleniu.

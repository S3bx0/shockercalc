# Android Size Audit - 2026-07-05

Cel: ustalic realne zrodla rozmiaru aplikacji przed kolejnymi zmianami wizualnymi i refaktorem UI.

## Aktualny punkt odniesienia

- Artefakt: `refrigerationcalc-1.5.4-arm64-v8a-release.aab`
- Workflow: GitHub Actions `Build Android Release (AAB)`, run `28747278167`
- Commit: `30e371f`
- Rozmiar release AAB: **45.37 MiB**

To jest aktualny artefakt sklepowy. Rozmiar instalacji na telefonie bedzie wiekszy, bo Android wypakowuje biblioteki natywne, dane aplikacji i moze tworzyc zoptymalizowane pliki ART/DEX.

## Najwieksze skladniki AAB

| Grupa ZIP | Compressed | Raw | Wniosek |
|---|---:|---:|---|
| `base/lib` | 24.39 MiB | 39.69 MiB | natywne biblioteki Android/Kivy/Python; najwiekszy blok, ale najtrudniejszy do bezpiecznego ruszenia |
| `base/assets` | 8.85 MiB | 8.84 MiB | glownie `private.tar`, czyli kod Python + obrazy aplikacji |
| `base/dex` | 7.15 MiB | 18.93 MiB | Java/Kotlin dependencies: Firebase, Ads, Billing, Play Core, AndroidX |
| `base/res` | 4.78 MiB | 4.87 MiB | zasoby Android / Firebase / Google Play services |
| `base/resources.pb` | 0.11 MiB | 0.29 MiB | metadata zasobow Android App Bundle |

## `private.tar` / kod Python i assety

`private.tar` ma **8.84 MiB gzip** i **9.31 MiB extracted**.

Najwieksze elementy:

| Element | Rozmiar |
|---|---:|
| `assets/images` | 8.97 MiB |
| `tpof/mobile` | 0.30 MiB |
| `assets/Table3.json` | 0.06 MiB |
| `tpof/core` | 0.03 MiB |
| `p4a_hooks.pyc` | 0.02 MiB |
| `tpof/labor` | 0.02 MiB |

Wniosek: w naszym kodzie i danych najwiekszy skladnik, ktory mozemy kontrolowac bez ryzykownej zmiany runtime, to katalog grafik produktow.

## Runtime Python/Kivy

Z raportu CI:

| Element runtime | Rozmiar extracted |
|---|---:|
| Kivy | 10.09 MiB |
| KivyMD | 4.74 MiB |
| fontTools | 4.35 MiB |
| stdlib.zip | 3.81 MiB |
| setuptools | 2.46 MiB |
| PIL | 2.08 MiB |
| fpdf | 1.25 MiB |
| chardet | 0.98 MiB |
| jnius | 0.77 MiB |

Wniosek: usuwanie pojedynczych plikow aplikacji da male zyski. Duzy zysk wymagalby decyzji architektonicznej: ograniczenie zaleznosci PDF/fontow albo zmiana sposobu pakowania/runtime. To zostawiamy po stabilizacji wersji sklepowej.

## Co jest juz dobrze

`buildozer.spec` wyklucza ciezkie assety nieruntime:

- `assets/brand/**`
- `assets/store/**`
- `assets/fonts/**`
- `assets/watermark.png`
- `assets/icon.png`, `assets/icon-192.png`, `assets/icon-48.png`
- `assets/presplash.png`
- `android/**`
- `tpof/desktop/**`

Dzieki temu materialy do Play Console, grafiki brandowe, fonty desktopowe i watermark nie trafiaja do mobilnej paczki.

## Budzety kontrolne dodane w testach

Nowe testy regresyjne pilnuja, zeby stabilizacja assetow nie popsula paczki:

- caly katalog `assets/images` musi zostac ponizej **9 MiB**,
- pojedyncza grafika produktu musi zostac ponizej **150 KiB**,
- obrazy musza pozostac w formacie WebP i maksymalnie **512x512 px**,
- lista widocznych produktow bez grafiki musi pozostac pusta,
- techniczne obrazy CTP sa nadal wykrywane jako ukryte w aplikacji mobilnej.

## Rekomendacje bezpieczne na teraz

1. **Grafiki produktow** - wymieniac stare/szablonowe obrazy na finalny styl pop-art, ale trzymac WebP 512x512 i cel 70-110 KiB na plik.
2. **Batchowanie assetow** - podmieniac po 20-40 plikow, potem szybki test UI i build. Nie robic masowej podmiany 160+ obrazow w jednym patchu.
3. **Raportowac rozmiar po kazdym release AAB** - porownywac AAB z tym baseline, zeby nie wprowadzic przypadkowo duzych zasobow.
4. **Nie ruszac runtime przed wersja sklepowa** - `Kivy`, `KivyMD`, `fontTools`, `PIL` i `fpdf` sa najwieksze, ale ich ograniczanie wymaga mocnych testow PDF/UI.

## Rekomendacje odlozone

1. **PDF/fontTools** - potencjalny zysk kilku MiB, ale ryzyko regresji PDF; ruszyc dopiero po stabilizacji sklepowej.
2. **R8/shrinkResources** - moze zmniejszyc `base/dex` i `base/res`, ale wymaga ostroznych testow z Firebase, Ads, Billing, Play Core i Kivy.
3. **Zdalne lub opcjonalne obrazy** - najwiekszy potencjal w przyszlosci, ale pogarsza offline i komplikuje UX.

## Decyzja dla najblizszego patcha

Nie ruszamy runtime ani duzego refaktoru UI. W tej paczce stabilizujemy aplikacje, dodajemy budzety testowe dla grafik produktow i aktualizujemy punkt odniesienia rozmiaru na release AAB.

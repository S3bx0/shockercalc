# Android Size Audit - 2026-07-05

Cel: ustalic realne zrodla rozmiaru aplikacji przed kolejnymi zmianami wizualnymi i refaktorem UI.

## Aktualny punkt odniesienia

- Artefakt: `refrigerationcalc-1.5.1-arm64-v8a-debug.apk`
- Workflow: GitHub Actions `Build Android APK`, run `28735032997`
- Commit: `fd1c743`
- Rozmiar APK: **48.41 MiB**

To jest debug APK z CI. Dla decyzji sklepowych ostatecznym punktem odniesienia pozostaje release AAB, ale debug APK dobrze pokazuje proporcje skladnikow.

## Najwieksze skladniki APK

| Grupa ZIP | Compressed | Raw | Wniosek |
|---|---:|---:|---|
| `lib` | 25.37 MiB | 39.69 MiB | natywne biblioteki Android/Kivy/Python; najwiekszy blok, ale najtrudniejszy do bezpiecznego ruszenia |
| `assets` | 8.85 MiB | 8.84 MiB | glownie `private.tar`, czyli kod Python + obrazy aplikacji |
| `res` | 4.90 MiB | 4.92 MiB | zasoby Android / Firebase / Google Play services |
| `classes8.dex` | 3.81 MiB | 9.37 MiB | Java/Kotlin dependencies |
| `classes.dex` | 3.70 MiB | 9.41 MiB | Java/Kotlin dependencies |
| `classes9.dex` | 1.28 MiB | 3.23 MiB | Java/Kotlin dependencies |

## `private.tar` / kod Python i assety

`private.tar` ma **8.84 MiB compressed** i **9.31 MiB extracted**.

Najwieksze elementy:

| Element | Rozmiar |
|---|---:|
| `assets/images` | 8.67 MiB |
| `tpof/mobile` | 0.30 MiB |
| `assets/Table3.json` | 0.06 MiB |
| `tpof/core` | 0.03 MiB |

Wniosek: w naszym kodzie i danych największy, sensowny do kontroli skladnik to katalog grafik produktow.

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

## Rekomendacje bezpieczne na teraz

1. **Grafiki produktow** - wymieniac stare/szablonowe obrazy na finalny styl pop-art, ale trzymac WebP 512x512 i cel 70-110 KiB na plik.
2. **Batchowanie assetow** - podmieniac po 20-40 plikow, potem szybki test UI i build. Nie robic masowej podmiany 160+ obrazow w jednym patchu.
3. **Raportowac rozmiar po kazdym release AAB** - porownywac AAB/APK z tym baseline, zeby nie wprowadzic przypadkowo duzych zasobow.

## Rekomendacje odlozone

1. **PDF/fontTools** - potencjalny zysk kilku MiB, ale ryzyko regresji PDF; ruszyc dopiero po stabilizacji sklepowej.
2. **R8/shrinkResources** - moze zmniejszyc `classes*.dex` i `res`, ale wymaga ostroznych testow z Firebase, Ads, Billing i Kivy.
3. **Zdalne lub opcjonalne obrazy** - najwiekszy potencjal w przyszlosci, ale pogarsza offline i komplikuje UX.

## Decyzja dla najblizszego patcha

Nie ruszamy runtime ani duzego refaktoru UI. W tej paczce stabilizujemy aplikacje, dopasowujemy przyciski zaworow do nowej palety i przygotowujemy kontrolowana liste assetow do wymiany.

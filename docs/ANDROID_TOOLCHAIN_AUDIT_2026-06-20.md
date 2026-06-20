# Audyt toolchainu Android/Python - 2026-06-20

## Cel

Zestaw produkcyjny ma byc jednoczesnie aktualny, odtwarzalny i zgodny z
python-for-android. Najnowsza wersja pojedynczego narzedzia nie zawsze jest
najlepsza: AndroidX Core 1.19.0 jest stabilny, ale wymaga AGP 9.1, podczas gdy
stabilny python-for-android dostarcza AGP 8.11.

## Rekomendowany zestaw produkcyjny

| Warstwa | Wersja | Decyzja |
|---|---:|---|
| Ubuntu runner | 24.04 | pozostawic |
| JDK | Temurin 17 | pozostawic; wymagany rowniez przez AGP 9.x |
| Python host/runtime | 3.13 / 3.13.14 | pozostawic do testow migracji 3.14 |
| Buildozer | 1.6.0 | przypiac stabilne wydanie z PyPI |
| python-for-android | v2026.05.09, commit `58d2114...` | przypiac stabilny release |
| AGP | 8.11.0 | dostarczany przez przypiety p4a |
| Gradle Wrapper | 8.14.3 | dostarczany przez przypiety p4a |
| Android API | compile/target 36, min 24 | pozostawic |
| Android NDK | r29 (`29.0.14206865`) | pozostawic; AAB i raport 16 KB sa zielone |
| Rust | 1.96.0 | przypiac zamiast ruchomego `stable` |
| Cython | 3.0.11 | pozostawic; zgodny z ograniczeniem pyjnius `<3.2` |

Ten zestaw zostal zweryfikowany przez testy jednostkowe i podpisany AAB.

## Biblioteki Android

| Biblioteka | Rekomendacja | Uzasadnienie |
|---|---:|---|
| Google Mobile Ads | 25.4.0 | najnowsza stabilna; poprawki wydajnosci i bledow |
| Play Billing | 9.1.0 | najnowsza stabilna; wymaganie Play to co najmniej 8 |
| Google UMP | 4.0.0 | najnowsza stabilna; minSdk 23, aplikacja ma 24 |
| AndroidX Core | 1.18.0 | najwyzsza sprawdzona zgodna z AGP 8.11; AAR wymaga AGP 8.9.1 |
| AndroidX Fragment | 1.8.9 | najnowsza stabilna; 1.9 jest alpha |

Core 1.19.0 nie jest obecnie dopuszczony do toru produkcyjnego, poniewaz jego
metadane AAR wymagaja AGP 9.1.0. Core 1.18.0 zachowuje nowy interfejs
`WindowCompat.enableEdgeToEdge()` i jest kompatybilny z AGP 8.11.

## Biblioteki Python

Pakiety bezposrednie zostaly przypiete, aby kolejny build nie pobral innych
wersji bez zmiany w repozytorium.

| Zastosowanie | Wersje |
|---|---|
| Android | Kivy 2.3.1, KivyMD 1.2.0, Pillow 11.3.0, fpdf2 2.8.7, fonttools 4.63.0, defusedxml 0.7.1 |
| Desktop/core | Pillow 12.2.0, ReportLab 5.0.0, pypdf 6.13.3, ttkbootstrap 1.20.3 |
| Testy | pytest 9.1.1, pytest-cov 7.1.0 |
| Narzedzia pip | pip 26.1.2, setuptools 82.0.1, wheel 0.47.0, legacy-cgi 2.6.4 |

Pillow ma dwie wersje celowo: Android korzysta z receptury p4a 11.3.0, a
desktop/CI z aktualnego kola PyPI 12.2.0.

## GitHub Actions

Workflow nie korzysta juz z akcji opartych o wycofywany runtime Node 20.
Oficjalne akcje zostaly przypiete do pelnych SHA z komentarzem wersji:

- checkout 7.0.0,
- setup-python 6.2.0,
- setup-java 5.3.0,
- cache 5.0.5,
- upload-artifact 7.0.1.

Dependabot raz w tygodniu przygotuje PR-y z aktualizacjami pip i GitHub
Actions. Nie ma automatycznego scalania: kazda zmiana musi przejsc testy i AAB.

## Tor nastepnej generacji

AGP 9 nie powinien byc podmieniany w produkcyjnym buildzie bez migracji p4a:

| Tor | AGP | Gradle | API | Status |
|---|---:|---:|---:|---|
| Produkcja | 8.11 | 8.14.3 | 36 | aktywny i zweryfikowany |
| Kandydat migracyjny | 9.2 | >=9.4.1 | 36.1/37 | testowac na osobnej galezi |
| Laboratorium | 9.3 RC | >=9.5 | 37 | nie publikowac |

AGP 9 zmienia DSL, Variant API i domyslna integracje Kotlin. Migracja musi
objac szablony p4a, hooki Gradle, podpisywanie, pakowanie AAB, Billing/AdMob,
symbole natywne i test na Androidzie 15-17.

Python 3.14 jest obslugiwany przez stabilny p4a i ma wsparcie do 2030 roku,
ale produkcja pozostaje na 3.13.14 do czasu osobnego testu AAB i testow PDF/UI.
Python 3.13 jest wspierany do pazdziernika 2029, wiec nie ma presji na ryzykowna
migracje przed testami zamknietymi.

## Procedura aktualizacji

1. Dependabot lub reczny audyt wykrywa nowe wydanie.
2. Sprawdzic oficjalna macierz AGP/Gradle/JDK/SDK/NDK.
3. Sprawdzic `minAndroidGradlePluginVersion` w AAR AndroidX.
4. Zmienic jedna warstwe kompatybilnosci na raz.
5. Uruchomic testy jednostkowe, debug APK i podpisany AAB.
6. Sprawdzic raport 16 KB, manifest i ostrzezenia Play Console.
7. Dopiero wtedy podniesc wersje na sciezce testowej.

## Zrodla

- [Tabela zgodnosci AGP/Gradle/API](https://developer.android.com/build/releases/about-agp?hl=pl)
- [AGP 9.0 - wymagania i zmiany DSL](https://developer.android.com/build/releases/agp-9-0-0-release-notes?hl=pl)
- [AGP 9.3 - status RC i wymagania](https://developer.android.com/build/releases/agp-9-3-0-release-notes?hl=pl)
- [AndroidX Core releases](https://developer.android.com/jetpack/androidx/releases/core)
- [AndroidX Fragment releases](https://developer.android.com/jetpack/androidx/releases/fragment)
- [Android NDK downloads](https://developer.android.com/ndk/downloads)
- [Google Mobile Ads release notes](https://developers.google.com/admob/android/rel-notes)
- [Play Billing release notes](https://developer.android.com/google/play/billing/release-notes)
- [Google UMP release notes](https://developers.google.com/admob/android/privacy/release-notes)
- [Python version lifecycle](https://devguide.python.org/versions/)
- [python-for-android v2026.05.09](https://github.com/kivy/python-for-android/releases/tag/v2026.05.09)
- [Buildozer 1.6.0](https://github.com/kivy/buildozer/releases/tag/1.6.0)

# Audyt rozmiaru Androida - 2026-06-24

## Punkt odniesienia: 1.4.3

| Element | Skompresowany | Po rozpakowaniu |
|---|---:|---:|
| AAB | 74,91 MiB | 102,23 MiB zawartości ZIP |
| APK | 77,96 MiB | - |
| `private.tar` | 37,17 MiB | 38,73 MiB |
| Biblioteki natywne AAB | 25,61 MiB | 40,91 MiB |
| DEX AAB | 7,15 MiB | 18,93 MiB |
| Zasoby Androida AAB | 4,78 MiB | 4,87 MiB |
| `libpybundle.so` | 18,92 MiB | 45,87 MiB |

Największe elementy `private.tar`:

| Element | Rozmiar |
|---|---:|
| 211 grafik produktów | 23,56 MiB |
| materiały `assets/brand` | 6,67 MiB |
| druga kopia GIF intra | 3,23 MiB |
| znak wodny desktopowego PDF | 1,60 MiB |
| kopie ikony i presplash | 1,60 MiB |
| materiały Google Play | 0,75 MiB |
| druga kopia DejaVuSans | 0,72 MiB |

Największe elementy rozpakowanego bundla Pythona:

| Pakiet | Rozmiar |
|---|---:|
| `fontTools` | 10,66 MiB |
| Kivy | 10,09 MiB |
| KivyMD | 4,74 MiB |
| biblioteka standardowa Python | 3,81 MiB |
| `setuptools` | 2,45 MiB |
| Pillow | 2,08 MiB |
| FPDF2 | 1,25 MiB |

## Dlaczego instalacja zajmuje około 300 MB

AAB i APK są archiwami. Android podczas instalacji rozpakowuje biblioteki
natywne i dane aplikacji, a ART może utworzyć zoptymalizowane kopie kodu DEX.
Kivy dodatkowo uruchamia pełny runtime Pythona. Ekran systemowy może sumować
APK, rozpakowane dane, biblioteki, kod zoptymalizowany i cache, dlatego jego
wartość nie jest równa rozmiarowi pobieranego AAB.

## Zmiany wdrożone w 1.4.4

1. 39 obrazów 1024 x 1024 zmniejszono do 512 x 512 WebP quality 85. Katalog
   obrazów spadł z 23,56 do 8,48 MiB, czyli o 15,07 MiB.
2. Z mobilnego archiwum źródeł wykluczono materiały marki i sklepu, znak
   wodny, kopie ikon, kopię fontu, kod desktopowy i zasoby Androida dodawane
   już osobnym mechanizmem Gradle.
3. `libpybundle.so` jest czyszczony przed podpisaniem. Pomiar na bundlu 1.4.3
   wykazał spadek 18,92 -> 17,70 MiB oraz 45,87 -> 39,54 MiB po rozpakowaniu.
4. CI generuje dla każdego APK/AAB raport `package-size-report.txt`.

Szacowany AAB po tych zmianach to około 44-46 MiB. Dokładny wynik musi zostać
potwierdzony przez GitHub Actions, ponieważ ostateczny sposób kompresji ustala
Buildozer, python-for-android i Gradle.

## Dalsze możliwości

### Etap 2: R8 i shrinkResources

Potencjalna oszczędność dotyczy głównie 7,15 MiB skompresowanego DEX. Wymaga
reguł `keep` dla własnej aktywności, PyJNIus, Kivy, reklam, Billing i Firebase
oraz testu na fizycznym telefonie. Nie należy łączyć tego z pierwszą redukcją,
bo utrudniłoby wykrycie regresji zakupów i telemetrii.

### Etap 3: lżejszy generator PDF

FPDF2 wymaga `fontTools`. Zastąpienie stosu własnym generatorem mogłoby usunąć
kilka kolejnych MiB, ale niesie ryzyko problemów z polskimi znakami, osadzaniem
fontów i zgodnością PDF. Obecnie usuwane są wyłącznie bezpieczne pliki budowy.

### Etap 4: obrazy dostarczane na żądanie

Największa dalsza redukcja byłaby możliwa przez pobieranie grafik po instalacji
lub Play Asset Delivery. Pogorszyłoby to pracę offline, dlatego zachowano pełny
katalog produktów w podstawowej aplikacji.

### Zmiana frameworka

Kivy, KivyMD, Python i biblioteki SDL odpowiadają za znaczną część minimalnego
rozmiaru. Przepisanie aplikacji natywnie zmniejszyłoby instalację najbardziej,
ale jest osobnym projektem i nie jest uzasadnione jako poprawka rozmiaru.

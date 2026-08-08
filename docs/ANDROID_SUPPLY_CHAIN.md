# Łańcuch dostaw podpisanego AAB

Workflow `.github/workflows/android-release.yml` tworzy dla każdego poprawnego,
podpisanego Android App Bundle dwa kryptograficznie podpisane poświadczenia:

1. poświadczenie pochodzenia zgodne z SLSA Provenance v1;
2. poświadczenie SBOM, którego predykatem jest CycloneDX 1.6.

Poświadczenia generuje oficjalna akcja `actions/attest` 4.1.0 przypięta pełnym
SHA commita. Certyfikat jest wystawiany dla krótkotrwałej tożsamości OIDC
konkretnego przebiegu GitHub Actions, a publiczne repozytorium korzysta z
publicznego rejestru przejrzystości Sigstore.

## Zakres SBOM

`tools/generate_android_sbom.py` nie kopiuje wyłącznie deklaracji projektu.
Dokument jest wyliczany z gotowego, podpisanego AAB i obejmuje:

- nazwę pliku AAB, SHA-256, package ID, `versionName` i `versionCode` odczytane
  z finalnego manifestu Bundletool;
- wszystkie dystrybucje Pythona znalezione w rzeczywistym `libpybundle.so`,
  również zależności przechodnie i pakiety dostarczone przez python-for-android;
- kontrolę, że każdy pin z `requirements-android-audit.txt` rzeczywiście
  występuje w bundle w oczekiwanej wersji;
- pełne rozwiązane drzewo Maven z konfiguracji Gradle
  `releaseRuntimeClasspath`, a nie tylko bezpośrednie wpisy z
  `buildozer.spec`;
- każdą bibliotekę natywną `.so` wraz z ABI, ścieżką w AAB i SHA-256.

Generator jest deterministyczny dla tych samych wejść. Numer seryjny dokumentu
wynika z identyfikatora aplikacji, wersji i skrótu AAB; nie zawiera lokalnego
czasu wykonania.

## Bramka wydania

Po zbudowaniu AAB workflow wykonuje następującą sekwencję:

1. rozwiązuje zależności Gradle w trybie offline z cache użytego podczas
   kompilacji;
2. sprawdza podpis, Bundletool, legal bundle, ABI, Python, backup, uprawnienia,
   sieć, inicjalizację Firebase/AdMob i wyrównanie 16 KB;
3. generuje `refrigerationcalc-android.cdx.json`;
4. publikuje osobne poświadczenia provenance i SBOM;
5. natychmiast weryfikuje je przez `gh attestation verify`, wymagając:
   - repozytorium `S3bx0/shockercalc`,
   - workflow `.github/workflows/android-release.yml`,
   - dokładnego SHA źródłowego commita,
   - właściwego typu predykatu;
6. zachowuje SBOM, raport Gradle, oba bundle poświadczeń i wyniki weryfikacji
   w artefakcie `refrigerationcalc-aab-supply-chain`.

Brak któregokolwiek elementu lub błąd weryfikacji zatrzymuje wydanie.

## Weryfikacja pobranego AAB

Po pobraniu AAB z przebiegu release:

```powershell
gh attestation verify .\refrigerationcalc-1.5.13-arm64-v8a-release.aab `
  --repo S3bx0/shockercalc `
  --signer-workflow S3bx0/shockercalc/.github/workflows/android-release.yml

gh attestation verify .\refrigerationcalc-1.5.13-arm64-v8a-release.aab `
  --repo S3bx0/shockercalc `
  --signer-workflow S3bx0/shockercalc/.github/workflows/android-release.yml `
  --predicate-type https://cyclonedx.org/bom
```

Weryfikacja provenance potwierdza integralność pliku i tożsamość procesu,
który go zbudował. Weryfikacja SBOM dodatkowo potwierdza, że dokument został
podpisany dla dokładnie tego samego skrótu AAB.

## Granice gwarancji

Poświadczenie dowodzi, który workflow podpisał twierdzenie o artefakcie; nie
zastępuje audytu kodu ani ochrony gałęzi. Zawartość predykatu tworzy sam
workflow, dlatego krytyczne są przegląd zmian workflow, pełne SHA używanych
akcji, minimalne uprawnienia zadania i brak wykonywania nieufnego kodu przed
podpisaniem. Obecny workflow pozostaje uruchamiany wyłącznie ręcznie lub przez
tag `v*` i korzysta z sekretów podpisu przechowywanych w GitHub Actions.

# Play Console - wydanie testowe 1.4.1

## Plik do przesłania

Do ścieżki testów zamkniętych przesyłamy wyłącznie plik `.aab` z artefaktu
`refrigerationcalc-release-aab`. Raporty diagnostyczne z GitHub Actions nie są
pakietami aplikacji.

## Najważniejsze zmiany

- intro korzysta bezpośrednio z zatwierdzonej animacji GIF 720 x 720,
  92 klatki, 4,9 sekundy;
- usunięto deformację logo powodowaną ponownym rysowaniem go w Javie;
- nieprzezroczyste tło okna i intro usuwa chwilowe prześwitywanie interfejsu;
- wydanie testowe działa do końca 15 lipca 2026 czasu polskiego;
- od 16 lipca wydanie testowe blokuje funkcje i otwiera stronę aplikacji w
  Google Play.

## Termin bezpieczeństwa

Przed 16 lipca 2026 należy opublikować wydanie produkcyjne z wyższym
`versionCode` i usuniętą stałą `TEST_BUILD_EXPIRES_AT_EPOCH_MS`. W przeciwnym
razie testerzy, którzy nie pobiorą aktualizacji, zobaczą ekran przekierowania do
Google Play zgodnie z założeniem tej wersji.

## Materiały sklepu

- ikona 512 x 512: `assets/store/play-icon-512.png`;
- grafika 1024 x 500: `assets/store/feature-graphic-1024x500.png`.

## Ostrzeżenia edge-to-edge

Wersja 1.4.0 wskazuje wyłącznie klasy bibliotek Google:

- `com.google.android.gms.ads.internal.overlay.zzm.zzj`;
- `com.google.android.play.core.hsdp.service.HsdpShimActivity.onCreate`.

Na dzień 22 czerwca 2026 aplikacja używa najnowszego stabilnego Google Mobile
Ads SDK 25.4.0. Jego oficjalny POM dołącza `play-services-ads-api:25.4.0`, a ten
z kolei najnowszy `com.google.android.play:hsdp:2.0.1`. Nie wykluczamy HSDP i
nie cofamy SDK, ponieważ są to zarządzane zależności aktualnej biblioteki reklam.
Ostrzeżenie nie blokuje testu ani publikacji; sprawdzamy je ponownie po kolejnym
wydaniu Google Mobile Ads SDK.

Źródła:

- https://developers.google.com/admob/android/rel-notes
- https://developer.android.com/about/versions/15/behavior-changes-15#edge-to-edge

## Proponowane informacje o wersji

```text
<pl-PL>
Poprawiono intro aplikacji: zatwierdzona animacja jest teraz odtwarzana bez
deformacji i bez prześwitywania ekranu głównego. Dodano kontrolowany termin
ważności zamkniętego wydania testowego.
</pl-PL>
```

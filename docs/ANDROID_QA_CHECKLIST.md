# Android QA Checklist

Checklist przed wysłaniem kolejnego AAB do Google Play.

## Edge-to-edge i paski systemowe

- Emulator lub telefon z Androidem 15 / API 35 oraz Androidem 16 / API 36.
- Sprawdzić jasny i ciemny motyw aplikacji.
- Ikony status bar i navigation bar muszą być czytelne na jasnym tle systemowym.
- Treść nie może wchodzić pod notch, aparat, pasek statusu ani pasek nawigacji.
- Obrócić ekran na telefonie/tablecie i sprawdzić, czy układ nie traci przycisków.

## Klawiatura ekranowa

- Otworzyć pola masy, temperatury początkowej, temperatury końcowej i czasu.
- Po pojawieniu się klawiatury aktywne pole ma pozostać widoczne.
- Dolna nawigacja i stopka nie mogą przykrywać aktywnego inputu.

## PDF i storage

- Aplikacja nie wymaga szerokich uprawnień do plików użytkownika.
- `buildozer.spec` powinien zawierać tylko `INTERNET` i `ACCESS_NETWORK_STATE`.
- Finalny manifest zawiera również zwykłe uprawnienia dodane przez AdMob,
  Google Play Billing, Firebase/DataTransport i WorkManager. Ich jawna allowlista
  jest sprawdzana w CI; każde nowe uprawnienie zatrzymuje build do audytu.
- Aplikacja nie może żądać dostępu do aparatu, mikrofonu, kontaktów, dokładnej
  lokalizacji ani współdzielonych plików i zdjęć użytkownika.
- Końcowy manifest musi jawnie ustawiać `android:usesCleartextTraffic="false"`
  i nie może odwoływać się do niezaudytowanego Network Security Config.
- Własne endpointy aplikacji muszą używać HTTPS; obecnie jedynym takim
  endpointem jest API kursów NBP.
- Eksport PDF na Androidzie tworzy roboczy plik w prywatnym katalogu aplikacji,
  a finalny zapis/udostępnienie przechodzi przez natywny most MediaStore/Share.
- Do Play Console przesyłać wyłącznie plik `.aab`; raporty diagnostyczne z CI nie
  są pakietami aplikacji.

## Build testowy

- Blokada terminu testowego została całkowicie usunięta z Activity.
- `tests/test_android_build_config.py` sprawdza, że stała, gate, overlay i tekst
  wygasania nie wróciły do kodu.
- Każdy build wysyłany do Google Play nadal musi mieć rosnący `versionCode`.

## Bramka podpisanego AAB

- Workflow musi potwierdzić podpis JAR pakietu przez `jarsigner`.
- Pobrany z oficjalnego wydania, przypięty sumą SHA-256 Bundletool musi wykonać
  `validate` na dokładnie tym AAB, który trafia do artefaktów.
- AAB może zawierać wyłącznie kompletny runtime `arm64-v8a`.
- Każdy segment `PT_LOAD` każdej biblioteki `.so` musi mieć wyrównanie co
  najmniej 16 KB. Wykrycie 4 KB jest błędem workflow, nie ostrzeżeniem.
- Wynikowy manifest musi mieć `allowBackup=false`, wyłączone domyślne kolekcje
  Firebase oraz nie może zawierać `FirebaseInitProvider` ani
  `MobileAdsInitProvider`.

## TODO techniczne

- Docelowo przekazywać insety z Androida do warstwy Kivy zamiast nakładać padding
  na cały `android.R.id.content`, jeśli po testach na tabletach okaże się to
  potrzebne.
- `tpof/mobile/main.py` jest cienkim launcherem, a składanie kontrolerów jest
  już w niezależnym od Kivy `tpof/mobile/app_controllers.py`. Kolejne kroki
  zmniejszające `app.py` wykonywać jako osobne checkpointy, bez łączenia z
  patchem hotfixowym.
- Nie podbijać `androidx.core:core` do linii wymagającej AGP 9 bez pełnej
  migracji toolchainu python-for-android/Buildozer.

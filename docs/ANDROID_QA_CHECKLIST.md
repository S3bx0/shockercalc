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
- Eksport PDF na Androidzie tworzy roboczy plik w prywatnym katalogu aplikacji,
  a finalny zapis/udostępnienie przechodzi przez natywny most MediaStore/Share.
- Do Play Console przesyłać wyłącznie plik `.aab`; raporty diagnostyczne z CI nie
  są pakietami aplikacji.

## Build testowy

- Blokada terminu testowego została całkowicie usunięta z Activity.
- `tests/test_android_build_config.py` sprawdza, że stała, gate, overlay i tekst
  wygasania nie wróciły do kodu.
- Każdy build wysyłany do Google Play nadal musi mieć rosnący `versionCode`.

## TODO techniczne

- Docelowo przekazywać insety z Androida do warstwy Kivy zamiast nakładać padding
  na cały `android.R.id.content`, jeśli po testach na tabletach okaże się to
  potrzebne.
- Rozbijać `tpof/mobile/main.py` stopniowo: tło, toolbar, mosty Ads/Billing i
  eksport PDF jako osobne moduły. Nie robić tego w patchu hotfixowym.
- Nie podbijać `androidx.core:core` do linii wymagającej AGP 9 bez pełnej
  migracji toolchainu python-for-android/Buildozer.

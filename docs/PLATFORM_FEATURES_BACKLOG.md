# Platform features backlog

Stan na 2026-07-21. Ten dokument porządkuje pomysły z `Platformowe JAVA.docx`
względem aktualnej architektury Refrigeration Calc. Nadrzędną zasadą pozostaje
zmniejszanie `tpof/mobile/main.py` i `RefrigerationCalcActivity.java`; nowa
funkcja platformowa nie może dokładać kolejnego podsystemu bezpośrednio do
Activity.

## Korekty względem dokumentu źródłowego

- Tryb ciemny jest już dostępny.
- Edycja pojedynczego zestawu stawek robocizny PRO jest już dostępna. Osobnym
  przyszłym zadaniem mogą być nazwane profile stawek.
- Blokada czasowa buildów testowych została całkowicie usunięta. Test
  `test_android_activity_has_no_test_expiry_gate` chroni przed jej powrotem.
- Aplikacja ma już Remote Config dla wartości `boolean` i `long`; brakującym,
  małym rozszerzeniem jest getter `string`, ale dopiero po wydzieleniu Firebase
  z Activity.
- Mechanizm In-App Updates nadal ma wartość, ale nie jest już zależny od
  wygasania buildów. Powinien służyć do zwykłych aktualizacji z Google Play.

## Bramka architektoniczna

`RefrigerationCalcActivity.java` ma obecnie około 1300 linii i łączy cykl życia,
Firebase, Remote Config, zgodę UMP, AdMob, Billing oraz udostępnianie plików.
Przed dodaniem Review, Updates, FCM lub Integrity należy wydzielić:

1. `FirebaseTelemetryService` — inicjalizacja Firebase, Analytics, Crashlytics
   i Remote Config.
2. `PrivacyConsentService` — UMP i formularz opcji prywatności.
3. `AdsService` — banner, reklama nagradzana i aktywne placementy.
4. `BillingService` — połączenie, produkty, zakupy, acknowledge i zapis
   uprawnień.
5. `FileShareService` — MediaStore i Android Sharesheet.

Activity ma zachować publiczne metody używane przez pyjnius jako cienkie
delegaty oraz przekazywać serwisom zdarzenia `onCreate`, `onResume`, `onPause`
i `onDestroy`.

## Rekomendowana kolejność funkcji platformowych

### Po rozbiciu Activity

1. **App Shortcuts** — mały zakres, widoczna poprawa UX, osobny handler intencji.
2. **In-App Review** — niski koszt i małe ryzyko; uruchamianie po kilku udanych
   działaniach, z lokalnym throttlingiem i bez nagradzania za ocenę.
3. **In-App Updates** — osobny `AppUpdateService`; najpierw tryb elastyczny,
   dopiero później ewentualny tryb natychmiastowy.
4. **Remote Config string** — małe rozszerzenie po utworzeniu
   `FirebaseTelemetryService`, bez logiki eksperymentów w Activity.

### Później, gdy pojawi się realna potrzeba

- **FCM** — dopiero gdy istnieje regularna treść do komunikowania i kompletny
  opt-in dla powiadomień.
- **Play Integrity** — dopiero przy potwierdzonym problemie nadużyć; wymaga
  weryfikacji serwerowej i nie powinno być ochroną wyłącznie po stronie klienta.
- **Widget ekranu głównego** — kosztowny osobny interfejs `RemoteViews`; App
  Shortcuts dają wcześniej większość wartości.

## Funkcje domenowe po stabilizacji modułów

Największą wartość biznesową mają historia obliczeń/projekty oraz wspólny
kosztorys PDF łączący chłodnictwo, robociznę i przyszły koszt energii. Kolejne
sensowne moduły to bilans komory, izolacja i czas zamrażania. Jednostki
imperialne powinny powstać jako czysty moduł konwersji na granicy UI, bez zmian
wzorów liczonych wewnętrznie w SI.

## Kryterium rozpoczęcia następnej funkcji

- bieżący checkpoint przeszedł test wewnętrzny na urządzeniu,
- odpowiedzialny serwis lub kontroler ma jawny interfejs,
- istnieją testy charakteryzujące dotychczasowe zachowanie,
- pełne testy, lint, mypy, APK i AAB przechodzą przed połączeniem zmian.

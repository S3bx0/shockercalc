# Audyt ponownego testu zamkniętego Google Play — 2026-07-30

Dokument opisuje stan sprawdzony bezpośrednio w Konsoli Play oraz czynności,
które trzeba wykonać przed drugim wnioskiem o dostęp produkcyjny. Nie stanowi
podstawy do deklarowania fikcyjnej aktywności ani opinii.

> Aktualizacja 2026-08-01: techniczny superaudyt wykazał, że obecna
> inicjalizacja Firebase może utworzyć Firebase Installation ID i lokalne dane
> sesji przed dobrowolną zgodą na Analytics/Crashlytics. Szczegóły i bramka
> naprawcza znajdują się w
> `docs/GOOGLE_PLAY_RELEASE_QUALITY_AUDIT_2026-08-01.md`. Do czasu wdrożenia
> lazy opt-in nie należy opisywać wszystkich identyfikatorów Firebase jako
> zbieranych wyłącznie po zgodzie.

## Stan potwierdzony w Konsoli Play

- pierwszy wniosek został odrzucony 30 lipca 2026 o 16:25;
- Konsola wymaga kolejnych 14 dni testu z co najmniej 12 testerami, liczonych
  od daty sprawdzenia;
- ścieżka zamknięta Alpha jest aktywna;
- wersja 96 (1.5.11) jest dostępna testerom od 30 lipca 2026, 19:59;
- wybrana lista e-mail zawiera 18 testerów;
- kanał opinii ścieżki to `MILCZAREK.SEBASTIAN1988@GMAIL.COM`;
- sekcja „Opinie z testów” zawiera jedną starszą, prywatną ocenę 5/5
  „Super” z 24 czerwca 2026, przesłaną z Samsung Galaxy M35 / Android 16;
  Konsola nie przypisuje jej do konkretnej wersji aplikacji, a sama treść nie
  zawiera szczegółów przydatnych do wdrożenia;
- „Stan zgodności z zasadami” pokazuje „Nie znaleziono problemów”;
- wszystkie 10 deklaracji zawartości jest oznaczonych jako zrealizowane;
- raport przed opublikowaniem nie został jeszcze wygenerowany;
- Android Vitals nie ma jeszcze danych o awariach i ANR;
- Konsola pokazuje dwa zalecenia dotyczące edge-to-edge dla wersji 96.

Szczegół drugiego zalecenia wskazuje
`LAYOUT_IN_DISPLAY_CUTOUT_MODE_SHORT_EDGES` w klasach dostawców:

- `com.google.android.gms.ads.internal.overlay.zzm.zzj`;
- `com.google.android.play.core.hsdp.service.HsdpShimActivity.onCreate`.

Pierwsza klasa pochodzi z aktualnego Google Mobile Ads SDK 25.4.0. Druga jest
komponentem Google Play. Zalecenie nie wskazuje kodu własnej Activity i nie jest
obecnie naruszeniem zasad, ale po przesłaniu następnego AAB trzeba sprawdzić,
czy nadal występuje.

## Warunki konieczne przed drugim wnioskiem

1. Nie wstrzymywać Alpha i nie usuwać wybranej listy testerów.
2. Utrzymać co najmniej 12 osób zapisanych nieprzerwanie przez cały okres.
3. Nie składać wniosku przed odblokowaniem przycisku przez Konsolę Play.
   Operacyjnie sprawdzić go 14 sierpnia 2026.
4. Przekazać testerom konkretne scenariusze i kanał zgłaszania uwag.
5. Zebrać rzeczywiste opinie, odpowiedzieć na nie i zapisać je bez danych
   osobowych w `docs/CLOSED_TEST_FEEDBACK_LOG.md`.
6. Wydać co najmniej jedną uzasadnioną aktualizację wynikającą z prawdziwej
   opinii. Nie przypisywać wcześniejszej poprawki opinii, której nie było.
7. Po każdym AAB sprawdzić raport przed opublikowaniem, a przed wnioskiem także
   Android Vitals, awarie, ANR i ostrzeżenia zgodności.
8. Utrzymywać formularz „Bezpieczeństwo danych” zgodny z faktyczną
   konfiguracją SDK i każdorazowo sprawdzać go przed nowym wydaniem.
9. W formularzu produkcyjnym podawać wyłącznie fakty: sposób rekrutacji,
   rzeczywiste użyte funkcje, otrzymane uwagi i wdrożone na ich podstawie
   zmiany.

Google nie publikuje wymagania codziennego uruchamiania aplikacji przez każdego
testera ani minimalnej liczby opinii. Wymaga natomiast ciągłego zapisu testerów
przez 14 dni i ocenia ich realne zaangażowanie. Dlatego nie organizujemy
pozornych otwarć aplikacji, tylko rozłożone w czasie testy jej funkcji.

## Scenariusze dla testerów

Tester powinien zainstalować i aktualizować aplikację wyłącznie przez Google
Play oraz wykonać możliwie wiele z poniższych zadań na swoim urządzeniu:

1. Uruchomienie po instalacji, przejście przez zgody i ponowne uruchomienie.
2. Obliczenie chłodzenia, zamrażania i domrażania dla poprawnych danych.
3. Próba pustych, błędnych i granicznych wartości oraz ocena komunikatów.
4. Wyszukanie produktu, zmiana produktu i sprawdzenie sumy mocy.
5. Eksport PDF i otwarcie lub udostępnienie pliku.
6. Obliczenie zaworów w dostępnych wariantach.
7. Obliczenie robocizny, kosztów dodatkowych i sprawdzenie wykresu.
8. Zmiana PLN/EUR/USD oraz sprawdzenie pobrania i zapisu kursu.
9. Zmiana języka, motywu, wskazówek oraz ponowne uruchomienie aplikacji.
10. Obrót ekranu lub zmiana rozmiaru okna, jeśli urządzenie to obsługuje.
11. Sprawdzenie reklam, zgody prywatności oraz przywracania zakupu bez
    wykonywania niepotrzebnych transakcji.
12. Użycie „Wyślij opinię / Zgłoś błąd” w ustawieniach albo prywatnej opinii
    Google Play.

W wiadomości dla testerów należy poprosić o: model urządzenia, wersję Androida,
wersję aplikacji, wykonane kroki, oczekiwany i faktyczny rezultat. Nie należy
prosić o dane obliczanych klientów, zdjęcia dokumentów ani inne dane osobowe.

## Audyt formularza „Bezpieczeństwo danych”

Deklaracja z 4 czerwca 2026 miała zaznaczony tylko jeden typ:
„Identyfikatory urządzenia i inne”. Nie odpowiadało to obecnej konfiguracji
wydania:

- `play-services-ads:25.4.0`;
- `firebase-analytics:23.2.0`;
- `firebase-crashlytics:20.0.6`;
- `firebase-config:23.1.0`;
- aktywny sekret `FIREBASE_GOOGLE_SERVICES_JSON_BASE64` w GitHub Actions.

30 lipca 2026 formularz został poprawiony i zapisany. Zadeklarowano sześć
typów danych:

| Typ w Konsoli Play | Źródło | Charakter | Typowe cele |
| --- | --- | --- | --- |
| Lokalizacja > Przybliżona lokalizacja | adres IP: AdMob, Analytics/Remote Config/Firebase Installations | AdMob przy żądaniu reklam; Firebase dopiero po zgodzie | reklamy, analityka, zapobieganie oszustwom |
| Aktywność w aplikacjach > Interakcje z aplikacją | AdMob i Analytics | AdMob automatycznie; Analytics po zgodzie | reklamy, analityka, zapobieganie oszustwom |
| Informacje o aplikacjach i ich działaniu > Dzienniki awarii | Crashlytics | opcjonalnie po zgodzie | funkcje aplikacji, analityka |
| Informacje o aplikacjach i ich działaniu > Diagnostyka | AdMob, Google Play Billing i Crashlytics | AdMob i techniczna telemetria Billing; Crashlytics po zgodzie | funkcje aplikacji/płatności, reklamy, analityka, zapobieganie oszustwom |
| Identyfikatory urządzenia i inne | AdMob, Analytics, Firebase Installations/Crashlytics | AdMob automatycznie; Firebase dopiero po zgodzie | reklamy, analityka, bezpieczeństwo |
| Informacje finansowe > Historia zakupów | Google Play Billing oraz automatyczne zdarzenia Analytics | podstawowa obsługa płatności; dodatkowa analityka po zgodzie | funkcje aplikacji/płatności, analityka |

Dla danych wysyłanych przez AdMob oficjalna dokumentacja SDK mówi o zbieraniu
i udostępnianiu. Dla Firebase należy rozróżnić dane zbierane od
„udostępnianych” według wyjątków Google Play dla dostawcy usług. W formularzu
trzeba zachować dotychczasową prawdziwą odpowiedź dla AdMob, a nie oznaczać
wszystkich danych Firebase automatycznie jako udostępniane.

Zbieranie przez AdMob nie jest opcjonalne tylko dlatego, że UMP pozwala odmówić
personalizacji; ograniczone reklamy nadal mogą wymagać danych technicznych.
Analytics, raportowanie Crashlytics i pobieranie Remote Config są w aplikacji
domyślnie wyłączone i użytkownik może je włączyć lub wyłączyć. Test z
1 sierpnia po usunięciu providerów automatycznego startu potwierdził brak FID i
plików Firebase przed zgodą. Zdarzenia wysłane wspólnym Google DataTransport
miały wyłącznie nazwę `PLAY_BILLING_LIBRARY`, dlatego sekcję Diagnostyka trzeba
ponownie porównać z aktualnym formularzem. Ostateczne odpowiedzi muszą
uwzględniać ustawienia AdMob, Billing, Analytics i Firebase Console oraz wynik
testu na świeżej instalacji.

W formularzu zaznaczono również szyfrowanie danych podczas przesyłania, brak
tworzenia kont użytkowników oraz możliwość żądania usunięcia danych przez:

`https://s3bx0.github.io/privacy.html#data-deletion`

Polityka prywatności zawiera teraz polskie i angielskie instrukcje przesłania
żądania oraz termin realizacji do 30 dni.

## Wydanie Alpha 1.5.12

30 lipca 2026 przesłano do istniejącej ścieżki „Test zamknięty - Alpha”:

- AAB `versionCode 98`, `versionName 1.5.12`;
- docelowy pakiet SDK 36;
- pełne wdrożenie na dotychczasowej ścieżce, bez zmiany listy testerów i
  regionu;
- informacje o wersji opisujące poprawki robocizny i wykresu, formularz opinii
  i zgłaszania błędów oraz aktualizacje prywatności i stabilności.

Konsola przyjęła pakiet i pokazała tylko dwa nieblokujące ostrzeżenia:

- brak pliku mapowania deobfuskacji;
- brak symboli debugowania kodu natywnego.

Wersję 98 i zaktualizowany formularz „Bezpieczeństwo danych” przesłano razem
do sprawdzenia. Bezpośrednio po wysłaniu Konsola pokazywała stan „Zmiany w
trakcie sprawdzania” oraz wykonywanie szybkich testów.

## Raport przed opublikowaniem

Raport jest generowany automatycznie w miarę dostępności urządzeń laboratorium.
Jeżeli nie pojawi się w ciągu dwóch dni od przesłania AAB, należy przesłać nowe
wydanie testowe. Aplikacja nie wymaga konta, więc ustawienie „Nie podawaj danych
logowania” jest poprawne. Po pierwszym raporcie warto wybrać języki polski i
angielski. Skrypt Robo jest opcjonalny; dla niestandardowego interfejsu Kivy
może poprawić pokrycie, ale nie zastępuje ręcznych testów.

## Źródła

- [Wymagania testów dla nowych kont osobistych](https://support.google.com/googleplay/android-developer/answer/14151465?hl=pl)
- [Konfiguracja testu zamkniętego](https://support.google.com/googleplay/android-developer/answer/9845334?hl=pl)
- [Bezpieczeństwo danych](https://support.google.com/googleplay/android-developer/answer/10787469?hl=pl)
- [Raport przed opublikowaniem](https://support.google.com/googleplay/android-developer/answer/9842757?hl=pl)
- [Dane Google Mobile Ads SDK](https://developers.google.com/admob/android/privacy/play-data-disclosure)
- [Dane Firebase SDK](https://firebase.google.com/docs/android/play-data-disclosure)
- [Dane Google Analytics for Firebase](https://support.google.com/analytics/answer/11582702?hl=pl)

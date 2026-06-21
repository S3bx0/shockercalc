# Play Console - wydanie 1.4.0

Dokument przygotowany 21 czerwca 2026 r. dla pakietu
`pl.smilczarek.refrigerationcalc`.

## 1. Plik do przesłania

Do ścieżki testu zamkniętego przesyłamy wyłącznie podpisany plik `.aab` z
artefaktu workflow `Build Android Release (AAB)`. Raporty diagnostyczne i APK
nie są pakietami publikowanymi w Play Console.

Przed utworzeniem tagu sprawdź w `GitHub > Settings > Secrets and variables >
Actions`, czy istnieje sekret `FIREBASE_GOOGLE_SERVICES_JSON_BASE64`. Bez niego
AAB nadal się zbuduje, ale Firebase pozostanie wyłączony.

## 2. Informacje o wersji do wklejenia

### Polski (`pl-PL`)

```text
Nowa identyfikacja Refrigeration Calc: nowa ikona i płynne intro z efektem
lotu płatków. Dodano dobrowolną telemetrię Firebase, przełączane podpowiedzi,
walidację pól i własne produkty PRO. Poprawiono katalog danych cieplnych,
kolejność kategorii oraz błąd ikony podpowiedzi.
```

### English (`en-US`)

```text
Introducing the new Refrigeration Calc identity, app icon and smooth
snowflake-flight intro. Added opt-in Firebase telemetry, optional field hints,
input validation and custom PRO products. Improved thermal data, category
ordering and fixed the hint button crash.
```

## 3. Nowa ikona Google Play

Ścieżka w Play Console:

`Zwiększaj liczbę użytkowników > Obecność w sklepie > Główne informacje o aplikacji > Grafika`

Prześlij:

`assets/store/play-icon-512.png`

Plik ma 512 x 512 px, format PNG RGBA i rozmiar poniżej 1024 KB. Nie zastępuje
on ikony launchera zawartej w AAB; obie wersje pochodzą jednak z tego samego
zatwierdzonego wzorca.

## 4. Firebase i Bezpieczeństwo danych

Ścieżka:

`Zasady i programy > Zawartość aplikacji > Bezpieczeństwo danych`

Nie usuwaj wcześniejszych deklaracji dotyczących AdMob, UMP i Google Play
Billing. Dla aktywnego Firebase sprawdź lub dodaj następujące pozycje:

| Typ danych | Funkcja | Cel | Wymagane ustawienie |
|---|---|---|---|
| Aktywność w aplikacji > Interakcje z aplikacją | Analytics | Analityka | Zbierane opcjonalnie |
| Informacje o aplikacji i jej działaniu > Dzienniki awarii | Crashlytics | Funkcje aplikacji / analityka | Zbierane opcjonalnie |
| Informacje o aplikacji i jej działaniu > Diagnostyka | Crashlytics | Funkcje aplikacji / analityka | Zbierane opcjonalnie |
| Identyfikatory urządzenia lub inne | Firebase Installation ID, Analytics, Crashlytics | Analityka / zapobieganie oszustwom i bezpieczeństwo | Zbierane opcjonalnie dla Firebase |
| Przybliżona lokalizacja | Analytics i usługi reklamowe, jeśli wynika z adresu IP | Analityka / reklamy | Zachowaj zgodność z konfiguracją SDK |

W formularzu zaznacz szyfrowanie danych podczas przesyłania. Telemetria
Firebase jest wyłączona domyślnie i uruchamia się dopiero po świadomej zgodzie,
więc jej zbieranie jest opcjonalne. Wyłączenie zgody w aplikacji zatrzymuje
dalsze zbieranie Analytics i Crashlytics oraz pobieranie Remote Config.

Samo przekazanie danych do Firebase jako dostawcy przetwarzającego dane na
zlecenie nie musi oznaczać „udostępniania” w definicji formularza Google Play.
Nie zmieniaj jednak istniejącej odpowiedzi o udostępnianiu związanej z AdMob.

## 5. Polityka prywatności

Przed wysłaniem wydania sprawdź, czy publiczny adres Play Console wskazuje na
aktualny `docs/privacy.html`. Dokument opisuje Analytics, Crashlytics, Remote
Config, AdMob, zgodę UMP, płatności i lokalne produkty użytkownika.

## 6. Firebase Console po instalacji testowej

1. Zainstaluj wydanie z testu zamkniętego, nie APK z pominięciem Google Play.
2. Zaakceptuj dobrowolną telemetrię w aplikacji testowej.
3. Sprawdź zdarzenia w `Analytics > DebugView` lub raporcie czasu rzeczywistego.
4. Sprawdź, czy Remote Config zwraca bezpieczne wartości domyślne:
   `custom_products_limit = 250` i `show_beta_features = false`.
5. Test Crashlytics wykonaj wyłącznie na urządzeniu testowym i potwierdź raport
   w konsoli po ponownym uruchomieniu aplikacji.
6. Nie wysyłaj w zdarzeniach mas, temperatur, nazw produktów użytkownika ani
   treści raportów PDF.

## 7. Kontrola końcowa

- numer `versionCode` jest większy od wszystkich wcześniejszych wydań;
- subskrypcja `refrigeration_pro` i abonament `monthly-499` są aktywne;
- testerzy są przypisani do ścieżki `alpha`;
- reklamy testowe nie są wymuszone w buildzie release;
- zakup PRO usuwa reklamy, odblokowuje PDF, moduł zaworów i własne produkty;
- przy cofnięciu subskrypcji uprawnienia PRO są odbierane;
- ikona, intro, język PL/EN, podpowiedzi i układ na telefonie/tablecie zostały
  sprawdzone przed wysłaniem zmian do weryfikacji.

## Oficjalne źródła

- [Google Play - formularz Bezpieczeństwo danych](https://support.google.com/googleplay/android-developer/answer/10787469?hl=pl)
- [Firebase - ujawnianie danych na Androidzie](https://firebase.google.com/docs/android/play-data-disclosure?hl=pl)
- [Firebase - prywatność i bezpieczeństwo](https://firebase.google.com/support/privacy)
- [Google Play - wymagania zasobów graficznych](https://support.google.com/googleplay/android-developer/answer/9866151?hl=pl)

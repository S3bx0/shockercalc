# Firebase - konfiguracja projektu

Integracja jest opcjonalna dla buildow deweloperskich. Bez poprawnego
`google-services.json` aplikacja buduje sie normalnie, a Firebase pozostaje
wylaczony. Zbieranie Analytics i Crashlytics jest dodatkowo domyslnie
wylaczone do czasu zgody uzytkownika.

## 1. Projekt i aplikacja Android

1. Utworz projekt w Firebase Console.
2. Dodaj aplikacje Android z dokladnym package name:
   `pl.smilczarek.refrigerationcalc`.
3. Pobierz `google-services.json`.
4. Lokalnie umiesc go jako `.firebase/google-services.json`. Katalog jest
   ignorowany przez Git i pliku nie wolno commitowac.
5. W GitHub Actions dodaj sekret `FIREBASE_GOOGLE_SERVICES_JSON_BASE64` z
   zawartoscia pliku zakodowana Base64.

PowerShell:

```powershell
[Convert]::ToBase64String(
  [IO.File]::ReadAllBytes("C:\sciezka\google-services.json")
) | Set-Clipboard
```

## 2. Uslugi

W Firebase Console wlacz:

- Google Analytics,
- Crashlytics,
- Remote Config,
- opcjonalnie App Distribution.

Remote Config ma bezpieczne wartosci domyslne w aplikacji:

| Klucz | Typ | Domyslnie | Znaczenie |
|---|---|---:|---|
| `custom_products_limit` | Number | `250` | Maksymalna liczba wlasnych produktow PRO |
| `show_beta_features` | Boolean | `false` | Rezerwowy przelacznik funkcji testowych |

Remote Config jest pobierany tylko po wlaczeniu dobrowolnej telemetrii.

## 3. Firebase App Distribution

To dodatkowa droga dystrybucji APK, a nie zamiennik wymaganego testu
zamknietego Google Play.

Dodaj sekrety GitHub Actions:

- `FIREBASE_ANDROID_APP_ID` - App ID z ustawien aplikacji Firebase,
- `FIREBASE_SERVICE_ACCOUNT_JSON_BASE64` - klucz konta uslugi w Base64.

Opcjonalnie dodaj zmienna repozytorium `FIREBASE_TESTER_GROUPS`, np.
`android-testers`. Workflow `Build Android APK` ma reczny parametr
`distribute_to_firebase`; po jego wlaczeniu gotowy APK zostanie przekazany
testerom z wybranej grupy.

## 4. Play Console i prywatnosc

Przed publikacja buildu z aktywnym Firebase:

1. Opublikuj zaktualizowany `docs/privacy.html`.
2. Zaktualizuj formularz Bezpieczenstwo danych. Analytics/Crashlytics moga
   obejmowac aktywnosc w aplikacji, informacje o aplikacji i jej dzialaniu,
   identyfikatory urzadzenia lub instalacji oraz dane diagnostyczne.
3. Zaznacz, ze zbieranie w aplikacji jest dobrowolne i mozna je wylaczyc.
4. Zweryfikuj DebugView Analytics i wymusz testowy blad Crashlytics dopiero
   na koncie/testowym urzadzeniu, nie w wydaniu produkcyjnym.

## 5. Zasady zdarzen

Aplikacja wysyla jedynie zdarzenia o uzyciu funkcji, m.in.
`calculation_started`, `calculation_finished`, `pdf_generated`,
`report_shared`, `settings_opened` i `custom_product_saved`.

Nie wolno dodawac do zdarzen wartosci obliczen, temperatur, mas, nazw
produktow uzytkownika ani zawartosci raportow PDF.

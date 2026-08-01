# Przewodnik rzeczywistego testu zamkniętego Google Play

Ten przewodnik pomaga testerom wykonać realistyczny test Refrigeration Calc i
przekazać użyteczną opinię. Nie służy do generowania pozornej aktywności.
Zapisuj wyłącznie faktyczne użycie i prawdziwe zgłoszenia.

## Wiadomość do przekazania testerom

> Zainstaluj lub zaktualizuj Refrigeration Calc wyłącznie przez link testu
> zamkniętego Google Play. Użyj aplikacji tak, jak używałbyś jej w praktyce.
> Sprawdź interesujące Cię obliczenia i napisz szczerze, co działa, co jest
> nieczytelne albo czego brakuje. W Ustawieniach wybierz „Otwórz raport testowy
> / opinię” albo prześlij prywatną opinię przez Google Play. Nie wpisuj danych
> klientów, danych wrażliwych ani prawdziwych parametrów poufnego zlecenia.

Nie wymagaj pozytywnej oceny. Potwierdzenie, że funkcja zadziałała, jest
przydatne, ale błąd, uwaga o użyteczności i pomysł na poprawę mają taką samą
wartość.

## Scenariusze do podziału między testerów

Każdy tester wybiera scenariusze odpowiadające jego sposobowi korzystania.
Grupa jako całość powinna pokryć:

1. Instalację i późniejszą aktualizację przez Google Play.
2. Chłodzenie, zamrażanie i domrażanie różnych produktów.
3. Wyszukiwanie produktu, ostatnie wybory i własny produkt.
4. Dobór zaworów w trybie kubatury oraz wymiarów.
5. Koszt robocizny z dojazdem, zwyżkami, kontenerami i kosztami dodatkowymi.
6. Wykres kosztów oraz przełączenie PLN, EUR i USD.
7. Eksport i udostępnienie przykładowego PDF bez danych klienta.
8. Jasny i ciemny motyw, język polski i angielski oraz obrót ekranu.
9. Zamknięcie i ponowne uruchomienie aplikacji oraz skróty z ikony launchera.
10. Zachowanie reklam, dostępu nagradzanego i ekranu PRO bez wykonywania
    niepotrzebnego zakupu.

Test powinien obejmować więcej niż jedno uruchomienie, jeśli odpowiada to
normalnemu użyciu testera. Bezcelowe klikanie lub sztuczne sesje nie stanowią
wartościowego testu.

## Plan operacyjny na 14 dni

To harmonogram pokrycia grupy, a nie nakaz codziennego, sztucznego uruchamiania
aplikacji przez każdą osobę:

- przed startem: zachować zapas ponad 12 osób, potwierdzić opt-in, instalację z
  Google Play, właściwą wersję i działający kanał kontaktu;
- dni 1–3: instalacja, pierwsze uruchomienie, chłodzenie/zamrażanie i ustawienia;
- dni 4–6: zawory, robocizna, waluty, obrót ekranu oraz ponowne uruchomienie;
- dzień 7: zebrać i sklasyfikować pierwszą turę prawdziwych opinii, odpowiedzieć
  testerom i wybrać możliwą do zweryfikowania poprawkę;
- dni 8–10: opublikować poprawkę na tej samej ścieżce, opisać ją w informacjach
  o wersji i poprosić o aktualizację przez Google Play;
- dni 11–13: ponowny test poprawki, PDF, reklamy/PRO i scenariusze pominięte w
  pierwszej turze;
- dzień 14 lub później: uzupełnić rejestr, sprawdzić Vitals, ANR, raport przed
  opublikowaniem i ciągłość opt-in; wiążący pozostaje stan Konsoli Play.

Nie obiecuj konkretnej poprawki przed otrzymaniem opinii. Aktualizacja musi
wynikać z rzeczywistego zgłoszenia, a harmonogram można przesunąć, jeśli jego
odtworzenie lub bezpieczna naprawa wymaga więcej czasu.

## Kanały opinii

- prywatna opinia na stronie testu w Google Play,
- ustrukturyzowany raport e-mail otwierany z Ustawień aplikacji,
- bezpośrednia rozmowa z testerem, następnie zanonimizowany wpis w rejestrze.

In-App Review można wdrożyć w trakcie testu jako dodatkowe wejście do prywatnej
opinii Google Play. Nie wolno jednak traktować samego wywołania API jako dowodu
feedbacku: Google może nie pokazać okna, a dowodem jest dopiero rzeczywista
opinia widoczna w Play Console i udokumentowana reakcja na jej treść.

W konfiguracji ścieżki testu zamkniętego należy pozostawić adres feedbacku:
`MILCZAREK.SEBASTIAN1988@GMAIL.COM`. Testerzy powinni wiedzieć o obu kanałach,
ponieważ Google Play nie publikuje ich prywatnych opinii jako ocen sklepu.

## Obsługa każdego rzeczywistego zgłoszenia

1. Potwierdź testerowi otrzymanie opinii.
2. Nadaj anonimowy identyfikator, np. `CT-2026-001`.
3. Zapisz obszar, wersję, kanał, częstotliwość i wpływ problemu bez danych
   identyfikujących testera.
4. Spróbuj odtworzyć zgłoszenie i zapisz wynik.
5. Podejmij jawną decyzję: przyjęte, odłożone albo odrzucone z powodem.
6. Jeśli wprowadzono zmianę, opublikuj ją na tej samej ścieżce testu i poproś
   autora zgłoszenia lub inną osobę o ponowną weryfikację.
7. Zapisz wersję, commit lub wydanie będące dowodem działania na opinii.
8. Odpowiedz również na prywatną opinię w Play Console, jeżeli pochodzi stamtąd.

## Dowody przed ponownym wnioskiem

- co najmniej 12 realnych testerów zapisanych nieprzerwanie przez okres
  wskazany w Konsoli Play,
- rzeczywiste pokrycie najważniejszych scenariuszy,
- zanonimizowany rejestr opinii i odpowiedzi,
- co najmniej jedna uzasadniona aktualizacja wynikająca z prawdziwej opinii,
- wynik ponownego testu poprawki,
- brak nierozwiązanych istotnych awarii i ANR w Android Vitals,
- spójne informacje o wersji opisujące poprawki wdrożone podczas testu.

Nie wpisuj do wniosku liczb ani działań, których nie potwierdzają Konsola Play,
wiadomości testerów lub historia wydań.

## Oficjalne materiały Google

- [Wymagania dotyczące testowania aplikacji dla nowych kont osobistych](https://support.google.com/googleplay/android-developer/answer/14151465)
- [Konfigurowanie testu otwartego, zamkniętego lub wewnętrznego](https://support.google.com/googleplay/android-developer/answer/9845334)
- [Testowanie In-App Review](https://developer.android.com/guide/playcore/in-app-review/test)

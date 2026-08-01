# Rejestr opinii z testu zamkniętego

Ten dokument służy do zapisywania wyłącznie rzeczywistych opinii testerów
Refrigeration Calc. Nie wpisuj imion, adresów e-mail ani innych danych
pozwalających zidentyfikować testera. Każdy wpis powinien mieć potwierdzone
źródło i prowadzić do jawnej decyzji.

## Jak prowadzić rejestr

1. Zapisz datę otrzymania opinii, kanał i testowany obszar.
2. Opisz problem własnymi słowami, bez danych osobowych testera.
3. Zapisz decyzję: przyjęte, odłożone albo odrzucone wraz z krótkim powodem.
4. Po wdrożeniu dodaj numer wersji, commit lub odnośnik do wydania.
5. Nie twórz wpisów pozornych. Google Play należy przekazywać wyłącznie
   prawdziwe informacje o testach i wprowadzonych zmianach.

Każdemu nowemu zgłoszeniu nadaj anonimowy identyfikator `CT-rrrr-nnn` i zapisz
także wynik próby odtworzenia, priorytet, datę odpowiedzi oraz wynik ponownego
testu poprawki. Szczegółowy proces i wiadomość dla testerów znajdują się w
[`CLOSED_TESTER_GUIDE.md`](CLOSED_TESTER_GUIDE.md).

## Zgłoszenia

| Data | Kanał | Obszar | Opinia / problem | Decyzja i uzasadnienie | Wersja / dowód wdrożenia |
| --- | --- | --- | --- | --- | --- |
| 2026-06-24 | prywatna opinia Google Play | ogólna ocena; Samsung Galaxy M35 / Android 16 | Ocena 5/5, treść „Super”; wersja aplikacji niedostępna | Brak szczegółów umożliwiających zmianę; w 1.5.12 udostępniono formularz do zbierania bieżących, ustrukturyzowanych opinii | opinia widoczna w Konsoli Play; 1.5.12 (98) |
| _rrrr-mm-dd_ | _e-mail / prywatna opinia Google Play_ | _np. Robocizna_ | _opis rzeczywistego zgłoszenia_ | _przyjęte / odłożone / odrzucone + powód_ | _np. 1.5.12 / commit / release_ |

## Weryfikacja i odpowiedzi

| ID | Odtworzenie | Priorytet | Data odpowiedzi | Ponowny test | Wynik |
| --- | --- | --- | --- | --- | --- |
| _CT-rrrr-nnn_ | _tak / nie + środowisko_ | _niski / średni / wysoki / blokujący_ | _rrrr-mm-dd_ | _wersja + data_ | _potwierdzone / nadal występuje_ |

## Podsumowanie przed kolejnym wnioskiem produkcyjnym

- Decyzja Google rozpoczynająca kolejny okres: 2026-07-30, 16:25
- Wersja 96 (1.5.11) dostępna na aktywnej ścieżce Alpha: 2026-07-30, 19:59
- Wersja 98 (1.5.12) i formularz „Bezpieczeństwo danych” przesłane razem do
  sprawdzenia: 2026-07-30
- Najwcześniejszy bezpieczny dzień sprawdzenia przycisku ponownego wniosku:
  2026-08-14; wiążący jest stan przycisku w Konsoli Play
- Liczba osób na wybranej liście testerów na początku okresu: 18
- Minimalna liczba testerów nieprzerwanie zapisanych w całym okresie:
  _uzupełnić po zakończeniu_
- Najważniejsze przetestowane scenariusze: _do uzupełnienia_
- Liczba otrzymanych rzeczywistych opinii: 1 starsza ocena ogólna bez
  szczegółów wdrożeniowych; liczbę nowych opinii z bieżącego okresu uzupełnić
- Wersje opublikowane na podstawie opinii: _do uzupełnienia_
- Stan Android Vitals, awarii i ANR: _do uzupełnienia_

Nie uznawaj samego zaproszenia lub instalacji za opinię. W podsumowaniu podaj
rzeczywiste kanały, powtarzające się uwagi i konkretne decyzje. Nie wpisuj
minimalnej liczby testerów jako 18, dopóki Konsola nie potwierdzi, że co najmniej
12 osób pozostało zapisanych nieprzerwanie przez cały wymagany okres.

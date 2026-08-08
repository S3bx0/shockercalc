# Plan weryfikacji dostępności Android — 2026-08-02

## Zakres wdrożony automatycznie

- lokalizowany opis aktywnej karty na natywnej powierzchni Android;
- komunikaty TalkBack o zmianie karty, wyniku obliczeń i błędzie;
- minimalne cele interaktywne 48 dp dla głównych akcji, nawigacji i ustawień;
- automatyczny próg kontrastu 4,5:1 dla palet przycisków oraz wartości wyników;
- układ reagujący na systemowy font scale 100%, 130%, 150% i 200%;
- kompaktowe odstępy pionowe w orientacji landscape.

## Uczciwe ograniczenie techniczne

Kivy renderuje interfejs jako jedną natywną powierzchnię. Obecny mostek
udostępnia TalkBackowi opis całego ekranu i komunikaty live region, ale nie
tworzy jeszcze osobnego węzła `AccessibilityNodeInfo` dla każdego widżetu.
Dlatego nie wolno oznaczać pełnej nawigacji TalkBack jako zakończonej przed
POC wirtualnego drzewa semantycznego albo migracją kluczowych formularzy do
natywnych kontrolek.

## Checklista ręczna — kandydat AAB

Wykonać na fizycznym urządzeniu ARM oraz, pomocniczo, emulatorze API 35/36:

1. Włączyć TalkBack, uruchomić aplikację i potwierdzić odczyt opisu karty
   Chłodnicze po zakończeniu intro.
2. Przejść przez trzy dolne karty i potwierdzić pojedynczy, lokalizowany
   komunikat o każdej zmianie.
3. Wykonać poprawne obliczenie w każdej karcie; wynik powinien zostać
   odczytany raz, bez przerywania bieżącego komunikatu.
4. Wywołać błąd walidacji; treść błędu powinna zostać odczytana.
5. Powtórzyć punkty 1–4 po zmianie języka PL/EN i motywu jasny/ciemny.
6. Ustawić rozmiar tekstu kolejno na 100%, 130%, 150% i 200%. Sprawdzić brak
   uciętych etykiet, dostępność przewijania i widoczność aktywnego pola nad IME.
7. Powtórzyć kluczowe formularze w landscape; dolna nawigacja i przyciski
   akcji nie mogą nachodzić na treść ani reklamę.
8. Włączyć Switch Access i Accessibility Scanner. Zanotować wszystkie cele
   poniżej 48 dp, brakujące etykiety i problemy kolejności fokusu.
9. Sprawdzić kontrast obu motywów na ekranie urządzenia, w tym stany aktywne,
   nieaktywne, błędy i wynik.
10. Zapisać urządzenie, API, skalę tekstu, wynik oraz zrzuty w rejestrze testu.

## Kryterium zamknięcia P1.1

Użytkownik korzystający wyłącznie z TalkBack lub Switch Access potrafi wybrać
produkt, wypełnić pola, uruchomić obliczenie, odczytać wynik, zmienić kartę i
otworzyć ustawienia bez pomocy wzroku. Obecny etap poprawia komunikaty, ale sam
nie spełnia jeszcze tego pełnego kryterium.

## Audyt kontrolny emulatora — 2026-08-08

Audyt wykonano na czystym debug APK dla `x86_64`, Android API 30,
1080 × 2280 px i gęstości 440 dpi. Przed poprawką zachowany zrzut bazowy
potwierdził rzeczywiste regresje przy font scale 200%: wielowierszowy tytuł,
nakładanie obrazu produktu i akcji oraz kolizję stopki z treścią.

PR #25 wprowadza następujące korekty:

- pełne skalowanie wysokości przewijalnej treści do 200%;
- pionowy układ karty produktu i grup akcji przy dużym tekście;
- przewijalną treść pierwszego dialogu prywatności/telemetrii;
- minimalną wysokość 48 dp dla akcji w dialogach;
- łagodniejsze skalowanie jednowierszowych kontrolek, aby długie etykiety nie
  były obcinane przy systemowym powiększeniu tekstu;
- ukrycie niekrytycznej stopki w landscape i jej podpisu przy dużym tekście.

Bramka automatyczna po zmianach: 497 testów, co najmniej 56% pokrycia przy wymaganym
minimum 50%, Ruff i mypy bez błędów. Test emulatorowy obejmuje font scale 100%
i 200%, orientację portrait/landscape, trzy karty oraz pierwszy dialog zgody.

Audyt emulatora **nie zamyka** P1.1: obraz systemowy nie zawiera TalkBack,
Switch Access ani Accessibility Scanner, a lokalnie nie ma AVD API 35/36.
Pełna kolejność fokusu, osobne węzły semantyczne i zachowanie kandydata AAB
muszą zostać sprawdzone ręcznie na fizycznym ARM oraz API 35/36 zgodnie z
checklistą powyżej.

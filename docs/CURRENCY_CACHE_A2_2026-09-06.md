# A2 — cache kursów i ręczne odświeżanie

Baza: PR #34, commit `a17958b2fee6b1a46be14367a05f3ee38338b045`.
Zmiany pozostają na osobnej gałęzi `codex/currency-cache-ttl`, bez merge
do `main` i bez publikacji aplikacji.

## Zachowanie

- `ExchangeRates.fetched_at` przechowuje chwilę zakończenia poprawnego pobrania
  całego zestawu. Zapis/odczyt cache zachowuje ten znacznik.
- Automatyczne sprawdzenie korzysta z cache dla wieku `0 <= age < 6 h`.
  Data publikacji kursu NBP nie wpływa na ten warunek. TTL 6 h jest decyzją
  aplikacji, a nie wymogiem API NBP. Nie dodano cyklicznego zadania w tle;
  istniejące zdarzenia uruchamiają sprawdzenie wieku danych.
- Brak znacznika, ujemna/niefinitywna wartość, błędny typ lub znacznik z
  przyszłości oznacza potrzebę odświeżenia. Same poprawne kursy nadal nadają
  się do pracy offline. Cofnięcie zegara nie przedłuża świeżości cache.
- Ręczne odświeżanie przekazuje jawne `force=True`. Ustawienie
  `auto_update=False` zawsze ma pierwszeństwo — nawet wymuszenie nie uruchamia
  wtedy sieci. Przycisk jest wyłączony również podczas trwającego pobrania.
- Zmiana waluty wyniku i start aplikacji nie wymuszają pobierania świeżego
  cache. Odczyt ani nieudana próba pobrania nie aktualizuje znacznika.
- Zachowano z PR #34 obsługę błędów i spóźnionych callbacków oraz serializację
  zapisów po przełączeniu preferencji.
- Nowy przycisk ma tłumaczenia PL/EN i wysokość 48 dp. Karta kursów korzysta
  z `minimum_height` zamiast stałej wysokości, aby pomieścić dodatkową akcję
  i objaśnienie. Pozostała kolejność sekcji ustawień bez zmian.

## Sprawdzenia lokalne

Python 3.13.12, te same zależności co w PR #34:

- pełny pytest: **592 PASS**, coverage **58,90%** przy wymaganych 50%;
- Ruff PASS; mypy skonfigurowany: 52 pliki PASS; pełny projekt: 164 pliki PASS;
- testy braku sieci przy świeżym cache, granicy dokładnie 6 h, wymuszenia,
  wyłączenia aktualizacji, legacy cache oraz nieprawidłowych timestampów;
- test czasu zakończenia pobrania i braku zapisu przy nieudanej aktualizacji;
- testy kontrolera oraz budowy dialogu z atrapami widgetów: podpięcie akcji,
  blokada przycisku, wysokość 48 dp i dopasowanie karty do zawartości.

Test z atrapami nie jest wizualnym testem Kivy ani Androida. Przed wydaniem
pozostaje kontrola przycisku na urządzeniu (PL/EN, motyw, większy tekst,
landscape, offline). Nie zmieniono wersji 1.5.15, zależności, cen, uprawnień,
formuł ani mechanizmów reklam. Wcześniejszy APK z PR #34 nie zawiera A2.

# Audyt danych cieplnych produktów - 2026-06-21

## Zakres

Porównano `assets/Table3.json` z tabelą 3 na stronach 9.3-9.6 dokumentu
`Thermal properties of Foodsv2.pdf` (2006 ASHRAE Handbook - Refrigeration,
rozdział 9). Dla każdego rekordu sprawdzono 10 pól: wilgotność, białko,
tłuszcz, węglowodany, błonnik, popiół, punkt zamarzania, `c1`, `c2` i `L1`.

## Wynik

- PDF zawiera 206 rekordów produktów.
- Wszystkie 206 rekordów ma po korekcie dokładny odpowiednik w JSON.
- `Chleb pszenny` i `Płyta TKT` pozostają rozszerzeniami katalogu spoza tabeli.
- Siedem technicznych rekordów `*_CTP ALDI` pozostaje w JSON i aplikacji
  desktopowej. Są odfiltrowane wyłącznie w selektorze aplikacji mobilnej.

## Dodane pozycje

- Warzywa: Bataty, Chrzan, Czosnek, Kapusta liściasta.
- Owoce: Cytryny, Porzeczki czerwone i białe.
- Rozdzielono sklejony rekord `Seler` na `Seler korzeniowy` i `Seler naciowy`.

Obecność brakujących produktów potwierdzono także w oficjalnej bazie USDA
FoodData Central: [czosnek](https://fdc.nal.usda.gov/fdc-app.html#/food-details/1104647/nutrients),
[chrzan](https://fdc.nal.usda.gov/fdc-app.html#/food-details/173472/nutrients),
[bataty](https://fdc.nal.usda.gov/fdc-app.html#/food-details/2346404/nutrients),
[kapusta liściasta](https://fdc.nal.usda.gov/fdc-app.html#/food-details/2685574/nutrients),
[porzeczki czerwone i białe](https://fdc.nal.usda.gov/fdc-app.html#/food-details/173964/nutrients)
oraz [cytryna](https://fdc.nal.usda.gov/fdc-app.html#/food-details/2709168/nutrients).
Wartości cieplne pochodzą z tabeli ASHRAE, nie z bieżących danych USDA.

## Skorygowane rekordy

Poprawiono przesunięte, sklejone lub błędnie przepisane kolumny dla:
Bakłażan, Brokuły, Brukiew, Buraki, Cebula, Dynia, Jarmuż, Kabaczek,
Ogórki, Papryka, Pory, Rabarbar, Rzepa, Rzodkiewka, Salsify, Szpinak,
Ziemniaki, Ananas, Podgardle, dwie pozycje szynki wieprzowej, Całe jajko,
Żółtko solone, Cheddar, trzy smaki lodów oraz dwa napoje.

Usunięto wadliwy duplikat `Rzepa2`; poprawny rekord występuje jako `Rzepa`.


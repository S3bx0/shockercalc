# Product Asset Audit - 2026-07-05

Cel: przygotowac bezpieczna liste grafik produktow do podmiany bez mieszania tego z duzym refaktorem UI.

## Podsumowanie

- Pliki WebP: 211
- Laczy rozmiar katalogu `assets/images`: 8.67 MiB
- Kandydaci high priority: 162
- Kandydaci medium priority: 1
- Kandydaci low priority: 7
- Obrazy wygladajace jak szablon/karta: 162
- Widoczne produkty mobilne: 208
- Widoczne produkty bez grafiki: 8
- Obrazy bez rekordu produktu: 4

## Rekomendacja

1. Najpierw podmieniac obrazy `high`: to glownie grafiki z widoczna ramka/etykieta karty, ktore odcinaja sie od finalnego stylu.
2. Nowe grafiki trzymac jako WebP 512x512, cel 70-110 KiB; 120 KiB traktowac jako sygnal do przegladu, a 150 KiB jako twardy limit testow.
3. Nie podmieniac automatycznie wszystkich obrazow naraz. Robic batchami po 20-40 sztuk i sprawdzac UI na telefonie.
4. Zachowac nazwy plikow, zeby nie ruszac mapowania produktow ani logiki aplikacji.

## Pierwsza kolejka do recznej wymiany

| Priorytet | Plik | Rozmiar | Heurystyka | Powody |
|---|---:|---:|---|---|
| high | `Agrest.webp` | 56.5 KiB | card-template | widoczny szablon karty lub biala etykieta |
| high | `Tuńczyk błękitnopłetwy.webp` | 33.5 KiB | card-template | widoczny szablon karty lub biala etykieta |
| high | `Makrela atlantycka.webp` | 32.7 KiB | card-template | widoczny szablon karty lub biala etykieta |
| high | `Śledź wędzony.webp` | 32.5 KiB | card-template | widoczny szablon karty lub biala etykieta |
| high | `Mintaj atlantycki.webp` | 32.5 KiB | card-template | widoczny szablon karty lub biala etykieta |
| high | `Łosoś różowy.webp` | 32.4 KiB | card-template | widoczny szablon karty lub biala etykieta |
| high | `Winogrona amerykańskie.webp` | 32.2 KiB | card-template | widoczny szablon karty lub biala etykieta |
| high | `Całe jajko suszone.webp` | 32.1 KiB | card-template | widoczny szablon karty lub biala etykieta |
| high | `Witlinek.webp` | 31.4 KiB | card-template | widoczny szablon karty lub biala etykieta |
| high | `Brzoskwinie suszone.webp` | 31.4 KiB | card-template | widoczny szablon karty lub biala etykieta |
| high | `Żółtko solone.webp` | 31.3 KiB | card-template | widoczny szablon karty lub biala etykieta |
| high | `Białko suszone.webp` | 31.3 KiB | card-template | widoczny szablon karty lub biala etykieta |
| high | `Łupacz.webp` | 31.2 KiB | card-template | widoczny szablon karty lub biala etykieta |
| high | `Halibut.webp` | 31.2 KiB | card-template | widoczny szablon karty lub biala etykieta |
| high | `Żółtko słodzone.webp` | 31.2 KiB | card-template | widoczny szablon karty lub biala etykieta |
| high | `Suszone śliwki.webp` | 31.1 KiB | card-template | widoczny szablon karty lub biala etykieta |
| high | `Białko jaja.webp` | 31.0 KiB | card-template | widoczny szablon karty lub biala etykieta |
| high | `Melon miodowy.webp` | 30.9 KiB | card-template | widoczny szablon karty lub biala etykieta |
| high | `Porzeczka czarna.webp` | 30.9 KiB | card-template | widoczny szablon karty lub biala etykieta |
| high | `Wiśnie słodkie.webp` | 30.9 KiB | card-template | widoczny szablon karty lub biala etykieta |
| high | `Całe jajko.webp` | 30.8 KiB | card-template | widoczny szablon karty lub biala etykieta |
| high | `Okoń.webp` | 30.7 KiB | card-template | widoczny szablon karty lub biala etykieta |
| high | `Dorsz.webp` | 30.5 KiB | card-template | widoczny szablon karty lub biala etykieta |
| high | `Żółtko.webp` | 30.5 KiB | card-template | widoczny szablon karty lub biala etykieta |
| high | `Papryka (słodka, główna odmiana).webp` | 30.1 KiB | card-template | widoczny szablon karty lub biala etykieta |
| high | `Homar amerykański.webp` | 30.0 KiB | card-template | widoczny szablon karty lub biala etykieta |
| high | `Przegrzebki.webp` | 29.1 KiB | card-template | widoczny szablon karty lub biala etykieta |
| high | `Fasola szparagowa.webp` | 29.0 KiB | card-template | widoczny szablon karty lub biala etykieta |
| high | `Ostrygi.webp` | 28.8 KiB | card-template | widoczny szablon karty lub biala etykieta |
| high | `Drożdże piekarnicze, sprasowane.webp` | 28.7 KiB | card-template | widoczny szablon karty lub biala etykieta |
| high | `Kukurydza cukrowa.webp` | 28.5 KiB | card-template | widoczny szablon karty lub biala etykieta |
| high | `Indyk.webp` | 28.5 KiB | card-template | widoczny szablon karty lub biala etykieta |
| high | `Popcorn, prażony na powietrzu.webp` | 28.4 KiB | card-template | widoczny szablon karty lub biala etykieta |
| high | `Papryka liofilizowana.webp` | 28.3 KiB | card-template | widoczny szablon karty lub biala etykieta |
| high | `Kaczka.webp` | 28.3 KiB | card-template | widoczny szablon karty lub biala etykieta |
| high | `Rukiew wodna.webp` | 28.3 KiB | card-template | widoczny szablon karty lub biala etykieta |
| high | `Krewetki.webp` | 28.2 KiB | card-template | widoczny szablon karty lub biala etykieta |
| high | `Sałata lodowa.webp` | 28.1 KiB | card-template | widoczny szablon karty lub biala etykieta |
| high | `Cebula suszona.webp` | 28.1 KiB | card-template | widoczny szablon karty lub biala etykieta |
| high | `Kurczak.webp` | 28.1 KiB | card-template | widoczny szablon karty lub biala etykieta |
| high | `Groszek zielony.webp` | 28.0 KiB | card-template | widoczny szablon karty lub biala etykieta |
| high | `Małże.webp` | 27.9 KiB | card-template | widoczny szablon karty lub biala etykieta |
| high | `Liście rzepy.webp` | 27.9 KiB | card-template | widoczny szablon karty lub biala etykieta |
| high | `Napój żurawinowo-winogronowy.webp` | 27.8 KiB | card-template | widoczny szablon karty lub biala etykieta |
| high | `Popcorn, prażony na oleju.webp` | 27.8 KiB | card-template | widoczny szablon karty lub biala etykieta |
| high | `Kabaczek zimowy.webp` | 27.8 KiB | card-template | widoczny szablon karty lub biala etykieta |
| high | `Serek wiejski, bez śmietany.webp` | 27.7 KiB | card-template | widoczny szablon karty lub biala etykieta |
| high | `Rzodkiewka.webp` | 27.7 KiB | card-template | widoczny szablon karty lub biala etykieta |
| high | `Sok winogronowy, niesłodzony.webp` | 27.7 KiB | card-template | widoczny szablon karty lub biala etykieta |
| high | `Mleko czekoladowe, 2% tłuszczu.webp` | 27.7 KiB | card-template | widoczny szablon karty lub biala etykieta |
| high | `Napój żurawinowo-jabłkowy.webp` | 27.6 KiB | card-template | widoczny szablon karty lub biala etykieta |
| high | `Sok grejpfrutowy, słodzony.webp` | 27.6 KiB | card-template | widoczny szablon karty lub biala etykieta |
| high | `Kapusta.webp` | 27.6 KiB | card-template | widoczny szablon karty lub biala etykieta |
| high | `Sok ananasowy, niesłodzony.webp` | 27.5 KiB | card-template | widoczny szablon karty lub biala etykieta |
| high | `Pomidory zielone.webp` | 27.5 KiB | card-template | widoczny szablon karty lub biala etykieta |
| high | `Bakłażan.webp` | 27.5 KiB | card-template | widoczny szablon karty lub biala etykieta |
| high | `Jarmuż.webp` | 27.5 KiB | card-template | widoczny szablon karty lub biala etykieta |
| high | `Szpinak.webp` | 27.5 KiB | card-template | widoczny szablon karty lub biala etykieta |
| high | `mieso i kielbasa_CTP ALDI.webp` | 27.4 KiB | card-template | widoczny szablon karty lub biala etykieta |
| high | `Szparagi.webp` | 27.3 KiB | card-template | widoczny szablon karty lub biala etykieta |

## Najwieksze pliki

| Plik | Rozmiar | Priorytet |
|---|---:|---|
| `Jabłka suszone.webp` | 141.0 KiB | medium |
| `Pomarańcze.webp` | 133.2 KiB | low |
| `Winogrono amerykańskie.webp` | 126.2 KiB | low |
| `Daktyle suszone.webp` | 123.1 KiB | low |
| `Figi suszone.webp` | 121.6 KiB | low |
| `Oliwki.webp` | 121.3 KiB | low |
| `Pomidory dojrzałe.webp` | 120.5 KiB | low |
| `Mandarynki.webp` | 120.2 KiB | low |
| `Woda gazowana.webp` | 119.1 KiB | ok |
| `Limonka.webp` | 116.5 KiB | ok |
| `Brokuły.webp` | 114.6 KiB | ok |
| `Grejpfrut.webp` | 113.7 KiB | ok |
| `Brzoskwinie świeże.webp` | 112.4 KiB | ok |
| `Kantalupa.webp` | 112.1 KiB | ok |
| `Truskawki.webp` | 111.5 KiB | ok |

## Pokrycie katalogu mobilnego

- Wszystkie produkty w bazie: 215
- Produkty widoczne w aplikacji mobilnej: 208
- Produkty techniczne ukryte w aplikacji mobilnej: 7
- Produkty widoczne bez obrazu: 8
- Obrazy bez rekordu produktu: 4

### Widoczne produkty bez grafiki

- `Bataty`
- `Chrzan`
- `Cytryny`
- `Czosnek`
- `Kapusta liściasta`
- `Porzeczki czerwone i białe`
- `Seler korzeniowy`
- `Seler naciowy`

### Obrazy bez rekordu produktu

- `Cukinia`
- `Rzepa2`
- `Seler`
- `Winogrono amerykańskie`

### Obrazy produktow technicznych ukrytych w mobile

- `chleb_CTP ALDI`
- `lody_CTP ALDI`
- `mieso i kielbasa_CTP ALDI`
- `nabial_CTP ALDI`
- `pizza_CTP ALDI`
- `ryby_CTP ALDI`
- `zerowka_CTP ALDI`

## Dane szczegolowe

Pelna tabela CSV: `docs/product_asset_audit_2026-07-05.csv`

Uwaga: klasyfikacja jest heurystyczna. Ostateczna decyzja zostaje wizualna, szczegolnie przy produktach dodanych poza ksiazka.

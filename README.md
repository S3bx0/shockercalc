# Shocker Calc

Kalkulator zapotrzebowania chłodu dla procesu zamrażania produktów spożywczych.

## Struktura projektu

```
tpof/                  # pakiet źródłowy
├── core/              # czysta logika (działa też na Androidzie)
│   ├── models.py
│   ├── validators.py
│   ├── calculations.py
│   ├── data_loader.py
│   ├── formatters.py
│   └── pdf_report.py
└── desktop/           # warstwa Tkinter + ttkbootstrap
    ├── app.py
    └── paths.py

assets/                # zasoby aplikacji
├── Table3.json        # baza produktów
├── fonts/             # DejaVuSans.ttf
├── images/            # zdjęcia produktów (.webp)
└── watermark.png      # znak wodny do PDF

tests/                 # testy pytest dla `tpof.core`
archive/               # backupy przed-refaktorowe
```

## Uruchomienie (desktop)

```powershell
# Instalacja zależności (jednorazowo)
python -m pip install -r requirements-desktop.txt

# Start aplikacji
python run.py
# albo
python -m tpof.desktop
```

## Testy

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest
```

## Plany rozwoju

- **Etap 4**: warstwa mobilna (KivyMD) + szablon `buildozer.spec` do publikacji w Google Play.

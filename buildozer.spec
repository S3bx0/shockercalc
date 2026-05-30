[app]

# Nazwa aplikacji widoczna na ekranie urządzenia
title = Shocker Calc

# Nazwa pakietu (musi być unikalna w Google Play)
package.name = shockercalc
package.domain = pl.mdpuch

# Katalogi źródłowe
source.dir = .
source.include_exts = py,png,jpg,jpeg,webp,ttf,json,kv,atlas
source.include_patterns = assets/*,assets/**/*,tpof/**/*
source.exclude_dirs = tests, archive, .venv, .pytest_cache, .mypy_cache, project, dejavu-fonts-ttf-2.37, Zdjęcia

# Wersja aplikacji
version = 2.0.0

# Zależności (uwaga: kivymd musi być w wersji kompatybilnej z kivy)
# UWAGA: reportlab/pypdf usunięte z buildu Android — ich C-rozszerzenia nie kompilują się
# pod Python 3.14 wybierany przez najnowszego python-for-android.
# PDF jest dostępny w wersji desktop. Na Androidzie pokażemy komunikat informacyjny.
requirements = python3,kivy==2.3.0,kivymd==1.2.0,pillow

# Punkt wejścia: p4a uruchamia main.py z source.dir.
# Plik main.py w korzeniu jest cienkim launcherem -> tpof.mobile.main:main

# Orientacja
orientation = portrait
fullscreen = 0

# Uprawnienia Android
android.permissions = INTERNET, WRITE_EXTERNAL_STORAGE, READ_EXTERNAL_STORAGE

# Min / target API (Google Play wymaga targetSdk >= 34 w 2026)
android.api = 34
android.minapi = 24
android.ndk = 25b
android.archs = arm64-v8a, armeabi-v7a

# Pin python-for-android do znanego dobrego release'u.
# Nowsze p4a domyślnie buduje Python 3.14, pod którym Kivy 2.3.0 / reportlab
# nie chcą się skompilować (deprecated CPython C-API).
# Tag 2024.01.21 -> Python 3.11.6, Kivy 2.3.0 buduje czysto.
p4a.fork = kivy
p4a.branch = 2024.01.21

# Ikona i splash
icon.filename = %(source.dir)s/assets/icon.png
presplash.filename = %(source.dir)s/assets/presplash.png
android.presplash_color = #1E3C6E

# Logowanie
log_level = 2

[buildozer]

# Zapobiega przypadkowemu uruchomieniu jako root
warn_on_root = 1

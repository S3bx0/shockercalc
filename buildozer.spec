[app]

# Nazwa aplikacji widoczna na ekranie urządzenia
title = Refrigeration Calc

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

# Autor / metadane (komentarz; widoczne w stopce aplikacji oraz w meta-data AndroidManifest)
# author: Sebastian Milczarek
android.meta_data = author=Sebastian Milczarek,copyright=2026 Sebastian Milczarek,com.google.android.gms.ads.APPLICATION_ID=ca-app-pub-7481054652344026~2716191071

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
android.permissions = INTERNET, ACCESS_NETWORK_STATE, WRITE_EXTERNAL_STORAGE, READ_EXTERNAL_STORAGE

# Min / target API (AdMob SDK 25.x wymaga compileSdk 35+)
android.api = 35
android.minapi = 24
android.ndk = 25b
android.archs = arm64-v8a, armeabi-v7a

# AdMob / Google Mobile Ads SDK + Google Play Billing (PRO: no ads)
android.add_src = %(source.dir)s/android/src
android.activity_class_name = pl.mdpuch.shockercalc.ShockerCalcActivity
android.entrypoint = pl.mdpuch.shockercalc.ShockerCalcActivity
android.gradle_dependencies = com.google.android.gms:play-services-ads:25.3.0, com.android.billingclient:billing:9.0.0
android.add_gradle_repositories = "google()", "mavenCentral()"

# Pin python-for-android do znanego dobrego release'u.
# Najnowszy p4a domyślnie buduje Python 3.14, pod którym Kivy 2.3.0 i reportlab
# nie kompilują się (usunięte _PyThreadState_UncheckedGet, Py_UNICODE itp.).
# Tag v2024.01.21 -> Python 3.11.x, Kivy 2.3.0 buduje czysto.
p4a.fork = kivy
p4a.branch = v2024.01.21

# Ikona i splash
icon.filename = %(source.dir)s/assets/icon.png
presplash.filename = %(source.dir)s/assets/presplash.png
android.presplash_color = #1E3C6E

# Logowanie
log_level = 2

[buildozer]

# Zapobiega przypadkowemu uruchomieniu jako root
warn_on_root = 1

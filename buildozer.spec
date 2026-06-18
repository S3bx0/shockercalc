[app]

# Nazwa aplikacji widoczna na ekranie urządzenia
title = Refrigeration Calc

# Nazwa pakietu (musi być unikalna w Google Play)
package.name = refrigerationcalc
package.domain = pl.smilczarek

# Katalogi źródłowe
source.dir = .
source.include_exts = py,png,jpg,jpeg,webp,ttf,json,kv,atlas
source.include_patterns = assets/*,assets/**/*,tpof/**/*
source.exclude_dirs = tests, archive, .venv, .pytest_cache, .mypy_cache, project, dejavu-fonts-ttf-2.37, Zdjęcia

# Wersja aplikacji
version = 1.2.5

# Numeryczny kod wersji (versionCode) dla Google Play — musi rosnąć z każdą publikacją.
# CI (workflow release) nadpisuje tę wartość numerem builda, więc lokalnie wystarczy 1.
android.numeric_version = 1

# Format artefaktu wydania dla Google Play (App Bundle).
android.release_artifact = aab

# Autor / metadane (komentarz; widoczne w stopce aplikacji oraz w meta-data AndroidManifest)
# author: Sebastian Milczarek
android.meta_data = author=Sebastian Milczarek,copyright=2026 Sebastian Milczarek,com.google.android.gms.ads.APPLICATION_ID=ca-app-pub-7481054652344026~2716191071

# Zależności (uwaga: kivymd musi być w wersji kompatybilnej z kivy)
# UWAGA: reportlab/pypdf usunięte z buildu Android — ich C-rozszerzenia nie kompilują się
# pod Python 3.14 wybierany przez najnowszego python-for-android.
# PDF na Androidzie generujemy czysto-pythonowym fpdf2 (+ fonttools, defusedxml).
requirements = python3,kivy==2.3.0,kivymd==1.2.0,pillow,fpdf2,fonttools,defusedxml

# Punkt wejścia: p4a uruchamia main.py z source.dir.
# Plik main.py w korzeniu jest cienkim launcherem -> tpof.mobile.main:main

# Orientacja / duże ekrany
# Buildozer wymaga poprawnej wartosci orientacji. Finalny AndroidManifest jest
# czyszczony w p4a_hooks.py z screenOrientation i ograniczen duzych ekranow.
orientation = portrait
fullscreen = 0

# Uprawnienia Android
android.permissions = INTERNET, ACCESS_NETWORK_STATE, WRITE_EXTERNAL_STORAGE, READ_EXTERNAL_STORAGE

# Min / target API (AdMob SDK 25.x wymaga compileSdk 35+)
android.api = 35
android.minapi = 24
android.ndk = 25b
android.archs = arm64-v8a

# AdMob / Google Mobile Ads SDK + Google Play Billing (PRO: no ads)
android.add_src = %(source.dir)s/android/src
android.activity_class_name = pl.smilczarek.refrigerationcalc.RefrigerationCalcActivity
android.entrypoint = pl.smilczarek.refrigerationcalc.RefrigerationCalcActivity
android.gradle_dependencies = com.google.android.gms:play-services-ads:25.3.0, com.android.billingclient:billing:9.0.0, com.google.android.ump:user-messaging-platform:3.0.0, androidx.core:core:1.15.0, androidx.fragment:fragment:1.8.9
android.add_gradle_repositories = "google()", "mavenCentral()"

# Pin python-for-android do znanego dobrego release'u.
# Najnowszy p4a domyślnie buduje Python 3.14, pod którym Kivy 2.3.0 i reportlab
# nie kompilują się (usunięte _PyThreadState_UncheckedGet, Py_UNICODE itp.).
# Tag v2024.01.21 -> Python 3.11.x, Kivy 2.3.0 buduje czysto.
p4a.fork = kivy
p4a.branch = v2024.01.21

# Hook p4a: usuwa błędne (host-arch) rozszerzenia .so fonttools z bundla,
# by na arm64 nie padało dlopen (bezierTools.so EM_X86_64 vs EM_AARCH64).
p4a.hook = p4a_hooks.py

# Ikona i splash
icon.filename = %(source.dir)s/assets/icon.png
presplash.filename = %(source.dir)s/assets/presplash.png
android.presplash_color = #1E3C6E

# Logowanie
log_level = 2

[buildozer]

# Zapobiega przypadkowemu uruchomieniu jako root
warn_on_root = 1

[app]

# Nazwa aplikacji widoczna na ekranie urządzenia
title = Refrig Calc

# Nazwa pakietu (musi być unikalna w Google Play)
package.name = refrigerationcalc
package.domain = pl.smilczarek

# Katalogi źródłowe
source.dir = .
source.include_exts = py,png,jpg,jpeg,gif,webp,ttf,json,kv,atlas
source.include_patterns =
source.exclude_patterns = assets/brand/**,assets/store/**,assets/fonts/**,assets/watermark.png,assets/icon.png,assets/icon-192.png,assets/icon-48.png,assets/presplash.png,android/**,tpof/desktop/**
source.exclude_dirs = tests, tools, archive, .venv, .pytest_cache, .mypy_cache, .firebase, project, dejavu-fonts-ttf-2.37, Zdjęcia

# Wersja aplikacji
version = 1.4.4

# Numeryczny kod wersji (versionCode) dla Google Play — musi rosnąć z każdą publikacją.
# CI (workflow release) nadpisuje tę wartość numerem builda, więc lokalnie wystarczy 1.
android.numeric_version = 1

# Format artefaktu wydania dla Google Play (App Bundle).
android.release_artifact = aab

# Autor / metadane (komentarz; widoczne w stopce aplikacji oraz w meta-data AndroidManifest)
# author: Sebastian Milczarek
android.meta_data = author=Sebastian Milczarek,copyright=2026 Sebastian Milczarek,com.google.android.gms.ads.APPLICATION_ID=ca-app-pub-7481054652344026~2716191071,firebase_analytics_collection_enabled=false,firebase_crashlytics_collection_enabled=false,google_analytics_default_allow_ad_personalization_signals=false

# Zależności (uwaga: kivymd musi być w wersji kompatybilnej z kivy)
# UWAGA: reportlab/pypdf usunięte z buildu Android — ich C-rozszerzenia nie kompilują się
# pod Pythonem Androidowym wybieranym przez python-for-android.
# PDF na Androidzie generujemy czysto-pythonowym fpdf2 (+ fonttools, defusedxml).
requirements = python3==3.13.14,hostpython3==3.13.14,kivy==2.3.1,kivymd==1.2.0,pillow==11.3.0,fpdf2==2.8.7,fonttools==4.63.0,defusedxml==0.7.1

# Punkt wejścia: p4a uruchamia main.py z source.dir.
# Plik main.py w korzeniu jest cienkim launcherem -> tpof.mobile.main:main

# Orientacja / duże ekrany
# Przekazujemy oba kierunki wraz z ich odwrotnymi wariantami, aby SDL/Kivy nie
# blokowalo orientacji w runtime. Finalny AndroidManifest jest dodatkowo
# czyszczony w p4a_hooks.py z ograniczen duzych ekranow.
orientation = portrait, landscape, portrait-reverse, landscape-reverse
fullscreen = 0

# Uprawnienia Android
android.permissions = INTERNET, ACCESS_NETWORK_STATE, WRITE_EXTERNAL_STORAGE, READ_EXTERNAL_STORAGE

# Min / target API (AdMob SDK 25.x wymaga compileSdk 35+)
android.api = 36
android.minapi = 24
android.ndk = 29
android.ndk_api = 24
android.archs = arm64-v8a
android.extra_cflags = -Dban_ALooper_pollAll=ALooper_pollOnce -Wno-error -Wno-cast-function-type-strict -Wno-cast-function-type
android.extra_ldflags = -Wl,-z,max-page-size=16384

# AdMob / Google Mobile Ads SDK + Google Play Billing (PRO: no ads)
android.add_src = %(source.dir)s/android/src
android.add_resources = %(source.dir)s/android/res
android.activity_class_name = pl.smilczarek.refrigerationcalc.RefrigerationCalcActivity
android.entrypoint = pl.smilczarek.refrigerationcalc.RefrigerationCalcActivity
android.gradle_dependencies = com.google.android.gms:play-services-ads:25.4.0, com.android.billingclient:billing:9.1.0, com.google.android.ump:user-messaging-platform:4.0.0, androidx.core:core:1.18.0, androidx.fragment:fragment:1.8.9, com.google.firebase:firebase-analytics:23.2.0, com.google.firebase:firebase-crashlytics:20.0.6, com.google.firebase:firebase-config:23.1.0
android.add_gradle_repositories = "google()", "mavenCentral()"

# Stabilny, odtwarzalny python-for-android. Ten release dostarcza AGP 8.11.0
# i Gradle 8.14.3 oraz obsluguje API 36, Python 3.13/3.14 i 16 KB pages.
p4a.fork = kivy
p4a.branch = master
p4a.commit = 58d21141f17c889bf8585f5665921d72028f8831

# Hook p4a: usuwa błędne (host-arch) rozszerzenia .so fonttools z bundla,
# by na arm64 nie padało dlopen (bezierTools.so EM_X86_64 vs EM_AARCH64).
p4a.hook = p4a_hooks.py

# Ikona i splash
icon.filename = %(source.dir)s/assets/icon.png
presplash.filename = %(source.dir)s/assets/presplash.png
android.presplash_color = #FFFFFF

# Logowanie
log_level = 2

[buildozer]

# Zapobiega przypadkowemu uruchomieniu jako root
warn_on_root = 1

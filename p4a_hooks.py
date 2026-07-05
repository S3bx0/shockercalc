"""Hooki python-for-android dla buildu Androida.

Problem: ``fonttools`` ma OPCJONALNE rozszerzenia Cython (np.
``fontTools/misc/bezierTools.so``). p4a instaluje fonttools hostowym pipem,
więc te rozszerzenia kompilują się dla architektury HOSTA CI (x86_64), a nie
dla telefonu (arm64). Na urządzeniu ``dlopen`` takiego ``.so`` pada:

    bezierTools.so is for EM_X86_64 (62) instead of EM_AARCH64 (183)

Rozwiązanie: usuwamy wszystkie ``.so`` należące do fonttools z bundla zanim
zostanie spakowany. fonttools działa wtedy w czystym Pythonie (nieco wolniej,
ale w pełni poprawnie) — fpdf2 generuje PDF bez problemu.
"""

import gzip
import io
import json
import os
import re
import shutil
import tarfile

FIREBASE_PACKAGE = "pl.smilczarek.refrigerationcalc"
DEFAULT_FIREBASE_CONFIG = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    ".firebase",
    "google-services.json",
)


def _resolve_firebase_config(config_path=None):
    candidates = [
        config_path,
        os.environ.get("FIREBASE_GOOGLE_SERVICES_JSON"),
        DEFAULT_FIREBASE_CONFIG,
        os.path.join(os.getcwd(), ".firebase", "google-services.json"),
    ]
    for candidate in candidates:
        if candidate and os.path.isfile(candidate):
            return os.path.abspath(candidate)
    return os.path.abspath(
        config_path
        or os.environ.get("FIREBASE_GOOGLE_SERVICES_JSON")
        or DEFAULT_FIREBASE_CONFIG
    )

def _strip_fonttools_native(*roots):
    """Usuwa pliki .so z katalogów fonttools we wskazanych korzeniach."""
    seen = set()
    removed = 0
    for root in roots:
        if not root:
            continue
        root = os.path.abspath(root)
        if root in seen or not os.path.isdir(root):
            continue
        seen.add(root)
        for dirpath, _dirnames, filenames in os.walk(root):
            low = dirpath.replace("\\", "/").lower()
            if "fonttools" not in low:
                continue
            for name in filenames:
                if name.endswith(".so"):
                    target = os.path.join(dirpath, name)
                    try:
                        os.remove(target)
                        removed += 1
                        print("[p4a hook] usunieto fonttools .so:", target)
                    except OSError as exc:  # pragma: no cover - build only
                        print("[p4a hook] nie udalo sie usunac:", target, exc)
    print("[p4a hook] usunieto plikow fonttools .so:", removed)


def _strip_python_bundle_payload(*roots):
    """Usuwa z libpybundle pliki fontTools zbędne na Androidzie.

    Rozszerzenia ``.so`` są kompilowane dla hosta CI, a źródła ``.c`` służą
    wyłącznie do ich budowania. FPDF korzysta na Androidzie z implementacji
    czysto-pythonowej, więc oba typy można usunąć przed podpisaniem paczki.
    """
    processed = set()
    removed_files = 0
    removed_bytes = 0
    for path in _iter_files("libpybundle.so", *roots):
        real_path = os.path.realpath(path)
        if real_path in processed:
            continue
        processed.add(real_path)
        try:
            with open(path, "rb") as fh:
                payload = fh.read()
            if not payload.startswith(b"\x1f\x8b"):
                continue
            raw_tar = gzip.decompress(payload)
            source = tarfile.open(fileobj=io.BytesIO(raw_tar), mode="r:")
        except (OSError, EOFError, tarfile.TarError):
            continue

        output = io.BytesIO()
        changed = False
        with source, tarfile.open(fileobj=output, mode="w") as target:
            for member in source.getmembers():
                normalized = member.name.replace("\\", "/").lower()
                remove = (
                    "/fonttools/" in normalized
                    and normalized.endswith((".c", ".so"))
                )
                if remove and member.isfile():
                    removed_files += 1
                    removed_bytes += member.size
                    changed = True
                    continue
                fileobj = source.extractfile(member) if member.isfile() else None
                target.addfile(member, fileobj)

        if not changed:
            continue
        compressed = gzip.compress(output.getvalue(), compresslevel=9, mtime=0)
        temp_path = path + ".optimized"
        with open(temp_path, "wb") as fh:
            fh.write(compressed)
        os.replace(temp_path, path)
        print(
            "[p4a hook] odchudzono libpybundle:",
            path,
            len(payload),
            "->",
            len(compressed),
        )
    print(
        "[p4a hook] usunieto z libpybundle:",
        removed_files,
        "plikow,",
        removed_bytes,
        "bajtow",
    )


def _candidate_roots(toolchain):
    roots = [os.getcwd()]
    ctx = getattr(toolchain, "ctx", None)
    for obj in (toolchain, ctx):
        for attr in ("dist_dir", "build_dir", "_build_dir"):
            roots.append(getattr(obj, attr, None))
    roots.append(os.path.join(os.getcwd(), ".buildozer"))
    return roots


def _iter_files(filename, *roots):
    seen = set()
    for root in roots:
        if not root:
            continue
        root = os.path.abspath(root)
        if root in seen or not os.path.isdir(root):
            continue
        seen.add(root)
        for dirpath, _dirnames, filenames in os.walk(root):
            if filename in filenames:
                yield os.path.join(dirpath, filename)


def _patch_android_manifest(*roots):
    """Usuwa ograniczenia orientacji/resize z wygenerowanego Manifestu."""
    patched = 0
    for path in _iter_files("AndroidManifest.xml", *roots):
        try:
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
        except OSError:
            continue

        original = text
        text = re.sub(r'\s+android:screenOrientation="[^"]*"', "", text)
        text = re.sub(r'\s+android:(?:max|min)AspectRatio="[^"]*"', "", text)
        text = re.sub(r'android:resizeableActivity="false"', 'android:resizeableActivity="true"', text)

        if "android:resizeableActivity=" not in text:
            text = re.sub(
                r"(<application\b)",
                r'\1 android:resizeableActivity="true"',
                text,
                count=1,
            )

        if text != original:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(text)
            patched += 1
            print("[p4a hook] zaktualizowano AndroidManifest:", path)
    print("[p4a hook] zaktualizowanych Manifestow:", patched)


def _patch_python_activity_orientation(*roots):
    """Usuwa odziedziczona blokade orientacji z launchera p4a.

    Zwykla aplikacja nie korzysta z galezi ``org.kivy.LAUNCH``, ale skaner
    Google Play analizuje bytecode i wykrywa tam ``setRequestedOrientation``.
    Android 16 ignoruje to ograniczenie na duzych ekranach, dlatego usuwamy je
    jeszcze przed kompilacja Javy.
    """
    orientation_block = re.compile(
        r"""
        \s*if\s*\(p\s*!=\s*null\)\s*\{\s*
        if\s*\(p\.landscape\)\s*\{\s*
        setRequestedOrientation\(ActivityInfo\.SCREEN_ORIENTATION_LANDSCAPE\);\s*
        \}\s*else\s*\{\s*
        setRequestedOrientation\(ActivityInfo\.SCREEN_ORIENTATION_PORTRAIT\);\s*
        \}\s*
        \}
        """,
        re.VERBOSE,
    )
    patched = 0
    for path in _iter_files("PythonActivity.java", *roots):
        try:
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
        except OSError:
            continue

        updated, replacements = orientation_block.subn("", text)
        if not replacements:
            continue
        if "ActivityInfo." not in updated:
            updated = re.sub(
                r"^import android\.content\.pm\.ActivityInfo;\s*\n",
                "",
                updated,
                flags=re.MULTILINE,
            )
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(updated)
        patched += 1
        print("[p4a hook] usunieto blokade orientacji:", path)
    print("[p4a hook] zaktualizowanych PythonActivity:", patched)


def _patch_release_gradle_diagnostics(*roots):
    """Dodaje bezpieczne ustawienia release dla ostrzezen Google Play."""
    marker = "Refrigeration Calc release diagnostics"
    snippet = f"""

// {marker} (patched by p4a_hooks.py).
android {{
    buildTypes {{
        release {{
            // Include native symbol table in AAB for Google Play Android vitals.
            ndk {{
                debugSymbolLevel 'SYMBOL_TABLE'
            }}
            // The p4a/Kivy release is not R8-obfuscated in this line.
            minifyEnabled false
            shrinkResources false
        }}
    }}
}}
"""
    patched = 0
    for path in _iter_files("build.gradle", *roots):
        try:
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
        except OSError:
            continue

        if marker in text:
            continue
        if "com.android.application" not in text or "android {" not in text:
            continue

        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text.rstrip() + snippet + "\n")
        patched += 1
        print("[p4a hook] zaktualizowano build.gradle diagnostics:", path)
    print("[p4a hook] zaktualizowanych build.gradle diagnostics:", patched)


def _firebase_config_matches_package(path):
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError, TypeError):
        return False
    for client in data.get("client", []):
        package = (
            client.get("client_info", {})
            .get("android_client_info", {})
            .get("package_name")
        )
        if package == FIREBASE_PACKAGE:
            return True
    return False


def _patch_firebase_gradle(*roots, config_path=None):
    """Konfiguruje pluginy Firebase tylko gdy dostarczono poprawny JSON."""
    config_path = _resolve_firebase_config(config_path)
    if not os.path.isfile(config_path):
        print("[p4a hook] Firebase wylaczony: brak google-services.json")
        return 0
    if not _firebase_config_matches_package(config_path):
        raise RuntimeError(
            "google-services.json nie zawiera pakietu " + FIREBASE_PACKAGE
        )

    marker = "Refrigeration Calc Firebase plugins"
    patched = 0
    for path in _iter_files("build.gradle", *roots):
        try:
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
        except OSError:
            continue
        if "com.android.application" not in text or "android {" not in text:
            continue

        updated = text
        if marker not in updated:
            with_classpath, classpath_count = re.subn(
                r"(?P<agp>\s*classpath\s+['\"]com\.android\.tools\.build:gradle:[^'\"]+['\"])",
                (
                    r"\g<agp>\n"
                    "        // " + marker + "\n"
                    "        classpath 'com.google.gms:google-services:4.5.0'\n"
                    "        classpath 'com.google.firebase:firebase-crashlytics-gradle:3.0.7'"
                ),
                text,
                count=1,
            )
            updated, plugin_count = re.subn(
                r"(apply plugin:\s*['\"]com\.android\.application['\"])",
                (
                    r"\1\n"
                    "apply plugin: 'com.google.gms.google-services'\n"
                    "apply plugin: 'com.google.firebase.crashlytics'"
                ),
                with_classpath,
                count=1,
            )
            if not classpath_count or not plugin_count:
                print(
                    "[p4a hook] pominieto pomocniczy build.gradle Firebase:",
                    path,
                )
                continue

        target_config = os.path.join(os.path.dirname(path), "google-services.json")
        shutil.copyfile(config_path, target_config)
        if updated != text:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(updated)
        patched += 1
        print("[p4a hook] skonfigurowano Firebase w:", path)
    if not patched:
        raise RuntimeError("Nie znaleziono glownego build.gradle aplikacji Firebase")
    print("[p4a hook] skonfigurowanych projektow Firebase:", patched)
    return patched


def _append_env_flag(name, flag):
    current = os.environ.get(name, "")
    if flag not in current:
        os.environ[name] = (current + " " + flag).strip()


def _set_16kb_build_flags():
    """Probuje wymusic 16 KB LOAD alignment dla bibliotek budowanych przez p4a."""
    ld_flag = "-Wl,-z,max-page-size=16384"
    c_flag = "-Dban_ALooper_pollAll=ALooper_pollOnce"
    warn_flags = "-Wno-error -Wno-cast-function-type-strict -Wno-cast-function-type"

    for name in ("LDFLAGS", "APP_LDFLAGS"):
        _append_env_flag(name, ld_flag)
    _append_env_flag("CFLAGS", c_flag)
    _append_env_flag("CFLAGS", warn_flags)
    _append_env_flag("CXXFLAGS", warn_flags)

    print("[p4a hook] LDFLAGS:", os.environ.get("LDFLAGS", ""))
    print("[p4a hook] APP_LDFLAGS:", os.environ.get("APP_LDFLAGS", ""))


def before_apk_build(toolchain):
    _set_16kb_build_flags()


def after_apk_build(toolchain):
    # Bundle _python_bundle jest juz utworzony na tym etapie.
    _strip_fonttools_native(*_candidate_roots(toolchain))


def before_apk_assemble(toolchain):
    # Ostatni moment przed gradle (bezpiecznik).
    roots = _candidate_roots(toolchain)
    _set_16kb_build_flags()
    _patch_android_manifest(*roots)
    _patch_python_activity_orientation(*roots)
    _patch_firebase_gradle(*roots)
    _patch_release_gradle_diagnostics(*roots)
    _strip_fonttools_native(*roots)
    _strip_python_bundle_payload(*roots)

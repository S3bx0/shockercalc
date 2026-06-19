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

import os
import re

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
            with open(path, "r", encoding="utf-8") as fh:
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
            with open(path, "r", encoding="utf-8") as fh:
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
    _patch_release_gradle_diagnostics(*roots)
    _strip_fonttools_native(*roots)

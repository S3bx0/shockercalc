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


def after_apk_build(toolchain):
    # Bundle _python_bundle jest juz utworzony na tym etapie.
    _strip_fonttools_native(*_candidate_roots(toolchain))


def before_apk_assemble(toolchain):
    # Ostatni moment przed gradle (bezpiecznik).
    _strip_fonttools_native(*_candidate_roots(toolchain))

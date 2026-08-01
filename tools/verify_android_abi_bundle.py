"""Verify that an Android APK/AAB contains a complete supported native runtime."""

from __future__ import annotations

import argparse
import re
import zipfile
from collections import defaultdict
from collections.abc import Collection
from pathlib import Path

SUPPORTED_ANDROID_ABIS = frozenset({"arm64-v8a"})
REQUIRED_RUNTIME_LIBRARIES = frozenset(
    {
        "libSDL2.so",
        "libmain.so",
        "libpybundle.so",
        "libpython3.13.so",
    }
)
_NATIVE_LIBRARY_PATH = re.compile(
    r"^(?:[^/]+/)?lib/(?P<abi>[^/]+)/(?P<library>[^/]+\.so)$"
)


def inspect_android_abis(archive_path: Path) -> dict[str, frozenset[str]]:
    """Return native libraries grouped by ABI for an APK or App Bundle."""

    libraries: defaultdict[str, set[str]] = defaultdict(set)
    with zipfile.ZipFile(archive_path) as archive:
        for name in archive.namelist():
            match = _NATIVE_LIBRARY_PATH.fullmatch(name)
            if match:
                libraries[match.group("abi")].add(match.group("library"))
    return {abi: frozenset(names) for abi, names in libraries.items()}


def verify_android_abi_bundle(
    archive_path: Path,
    *,
    supported_abis: Collection[str] = SUPPORTED_ANDROID_ABIS,
    required_libraries: Collection[str] = REQUIRED_RUNTIME_LIBRARIES,
) -> dict[str, frozenset[str]]:
    """Validate advertised ABIs and sentinel runtime libraries.

    An AAR dependency can contribute a single native library for an ABI that
    python-for-android did not build. Google Play then generates an installable
    split for that ABI, but the application crashes because Python/SDL are
    absent. Requiring an exact ABI set prevents that false advertisement.
    """

    packaged = inspect_android_abis(archive_path)
    actual_abis = set(packaged)
    expected_abis = set(supported_abis)
    if actual_abis != expected_abis:
        details = []
        unexpected = actual_abis - expected_abis
        missing = expected_abis - actual_abis
        if unexpected:
            details.append("unsupported ABI: " + ", ".join(sorted(unexpected)))
        if missing:
            details.append("missing ABI: " + ", ".join(sorted(missing)))
        if not details:
            details.append("no native runtime found")
        raise ValueError(f"{archive_path}: " + "; ".join(details))

    required = set(required_libraries)
    for abi in sorted(expected_abis):
        missing_libraries = required - set(packaged[abi])
        if missing_libraries:
            raise ValueError(
                f"{archive_path}: {abi} missing runtime libraries: "
                + ", ".join(sorted(missing_libraries))
            )
    return packaged


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("archive", type=Path, help="APK or AAB to verify")
    args = parser.parse_args()
    packaged = verify_android_abi_bundle(args.archive)
    print(f"Android ABI runtime verified: {args.archive}")
    for abi, libraries in sorted(packaged.items()):
        print(f"  {abi}: {len(libraries)} native libraries")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Verify security-sensitive Python packages embedded in an APK or AAB."""

from __future__ import annotations

import argparse
import io
import re
import tarfile
import zipfile
from pathlib import Path

EXPECTED_PILLOW_VERSION = "12.3.0"
PILLOW_DIST_INFO = re.compile(
    r"(?:^|/)pillow-([^/]+)\.dist-info(?:/|$)", re.IGNORECASE
)
REQUIRED_PILLOW_RUNTIME = (
    "PIL/__init__.pyc",
    "PIL/_imaging.so",
    "PIL/_imagingft.so",
)


def _python_bundle_members(package_path: Path) -> set[str]:
    with zipfile.ZipFile(package_path) as package:
        bundle_name = next(
            (name for name in package.namelist() if name.endswith("libpybundle.so")),
            None,
        )
        if bundle_name is None:
            raise ValueError(f"{package_path}: missing libpybundle.so")
        payload = package.read(bundle_name)

    with tarfile.open(fileobj=io.BytesIO(payload), mode="r:*") as bundle:
        return {
            member.name.removeprefix("./")
            for member in bundle.getmembers()
            if member.isfile()
        }


def verify_python_packages(
    package_path: Path, expected_pillow: str = EXPECTED_PILLOW_VERSION
) -> set[str]:
    """Return embedded Pillow versions or raise for stale/incomplete payloads."""

    members = _python_bundle_members(package_path)
    versions = {
        match.group(1)
        for name in members
        if (match := PILLOW_DIST_INFO.search(name)) is not None
    }
    if versions != {expected_pillow}:
        found = ", ".join(sorted(versions)) or "none"
        raise ValueError(
            f"{package_path}: expected Pillow {expected_pillow}, found {found}"
        )

    missing = [
        marker
        for marker in REQUIRED_PILLOW_RUNTIME
        if not any(name.endswith(marker) for name in members)
    ]
    if missing:
        raise ValueError(
            f"{package_path}: incomplete Pillow runtime: {', '.join(missing)}"
        )
    return versions


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("package", type=Path)
    parser.add_argument("--pillow-version", default=EXPECTED_PILLOW_VERSION)
    args = parser.parse_args()

    versions = verify_python_packages(args.package, args.pillow_version)
    print(f"Python bundle verified: {args.package}")
    print(f"  Pillow: {', '.join(sorted(versions))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

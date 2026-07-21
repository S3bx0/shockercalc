"""Verify that an Android App Bundle contains required offline legal files."""

from __future__ import annotations

import argparse
import io
import tarfile
import zipfile
from pathlib import Path

REQUIRED_LEGAL_FILES = {
    "LICENSE",
    "EULA",
    "AI_USAGE_POLICY",
    "THIRD_PARTY_NOTICES",
    "legal/GPL-3.0-only",
    "legal/LGPL-3.0-only",
}
CONTACT_EMAIL = "milczarek.sebastian1988@gmail.com"
CONTACT_FILES = {
    "LICENSE",
    "EULA",
    "AI_USAGE_POLICY",
    "THIRD_PARTY_NOTICES",
}


def _normalized_tar_members(archive: tarfile.TarFile) -> dict[str, tarfile.TarInfo]:
    return {member.name.removeprefix("./"): member for member in archive.getmembers()}


def verify_legal_bundle(aab_path: Path) -> set[str]:
    """Return packaged legal paths or raise when the bundle is incomplete."""

    with zipfile.ZipFile(aab_path) as bundle:
        private_name = next(
            (
                name
                for name in bundle.namelist()
                if name.endswith("assets/private.tar")
            ),
            None,
        )
        if private_name is None:
            raise ValueError(f"{aab_path}: missing assets/private.tar")
        private_tar = bundle.read(private_name)

    # Buildozer keeps the historical ``private.tar`` name even when the
    # payload is gzip-compressed, so let tarfile detect the actual format.
    with tarfile.open(fileobj=io.BytesIO(private_tar), mode="r:*") as archive:
        members = _normalized_tar_members(archive)
        missing = REQUIRED_LEGAL_FILES.difference(members)
        if missing:
            raise ValueError(
                f"{aab_path}: missing legal files: {', '.join(sorted(missing))}"
            )

        packaged = set(REQUIRED_LEGAL_FILES)
        contents: dict[str, str] = {}
        for name in REQUIRED_LEGAL_FILES:
            extracted = archive.extractfile(members[name])
            if extracted is None:
                raise ValueError(f"{aab_path}: cannot read {name}")
            contents[name] = extracted.read().decode("utf-8")

    checks = {
        "LICENSE": "LicenseRef-RefrigerationCalc-Proprietary-1.0",
        "EULA": "End-User License Agreement",
        "AI_USAGE_POLICY": "TDM-Reservation: 1",
        "THIRD_PARTY_NOTICES": "fpdf2 2.8.7",
        "legal/GPL-3.0-only": "GNU GENERAL PUBLIC LICENSE",
        "legal/LGPL-3.0-only": "GNU LESSER GENERAL PUBLIC LICENSE",
    }
    for name, marker in checks.items():
        if marker not in contents[name]:
            raise ValueError(f"{aab_path}: {name} does not contain {marker!r}")
    for name in CONTACT_FILES:
        if CONTACT_EMAIL not in contents[name]:
            raise ValueError(
                f"{aab_path}: {name} does not contain contact {CONTACT_EMAIL!r}"
            )
    return packaged


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("aab", type=Path)
    args = parser.parse_args()
    packaged = verify_legal_bundle(args.aab)
    print(f"Legal bundle verified: {args.aab}")
    for name in sorted(packaged):
        print(f"  {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

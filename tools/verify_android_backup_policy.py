"""Verify that the final Android manifest explicitly disables app backup."""

from __future__ import annotations

import argparse
import xml.etree.ElementTree as ET
from pathlib import Path

ANDROID_NS = "{http://schemas.android.com/apk/res/android}"


class AndroidBackupPolicyError(RuntimeError):
    """Raised when the final manifest permits or may permit app backup."""


def verify_backup_policy_manifest(path: Path) -> None:
    try:
        root = ET.fromstring(path.read_text(encoding="utf-8"))
    except (OSError, ET.ParseError) as exc:
        raise AndroidBackupPolicyError(f"{path}: invalid manifest XML: {exc}") from exc

    application = root.find("application")
    if application is None:
        raise AndroidBackupPolicyError(f"{path}: missing application element")

    allow_backup = application.get(ANDROID_NS + "allowBackup")
    if allow_backup != "false":
        value = "missing" if allow_backup is None else repr(allow_backup)
        raise AndroidBackupPolicyError(
            f"{path}: android:allowBackup must be false, got {value}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, help="Final AndroidManifest.xml")
    args = parser.parse_args()
    try:
        verify_backup_policy_manifest(args.manifest)
    except AndroidBackupPolicyError as exc:
        parser.error(str(exc))
    print(f"Android app backup is explicitly disabled: {args.manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

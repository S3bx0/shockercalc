"""Verify the final Android manifest against the approved permission allowlist."""

from __future__ import annotations

import argparse
import xml.etree.ElementTree as ET
from pathlib import Path

ANDROID_NS = "{http://schemas.android.com/apk/res/android}"
REQUIRED_PERMISSIONS = frozenset(
    {
        "android.permission.INTERNET",
        "android.permission.ACCESS_NETWORK_STATE",
        "com.android.vending.BILLING",
    }
)
ALLOWED_PERMISSIONS = REQUIRED_PERMISSIONS | frozenset(
    {
        "com.google.android.gms.permission.AD_ID",
        "android.permission.ACCESS_ADSERVICES_AD_ID",
        "android.permission.ACCESS_ADSERVICES_ATTRIBUTION",
        "android.permission.ACCESS_ADSERVICES_TOPICS",
        "android.permission.WAKE_LOCK",
        "com.google.android.finsky.permission.BIND_GET_INSTALL_REFERRER_SERVICE",
        "android.permission.FOREGROUND_SERVICE",
        "pl.smilczarek.refrigerationcalc.DYNAMIC_RECEIVER_NOT_EXPORTED_PERMISSION",
    }
)


class AndroidPermissionError(RuntimeError):
    """Raised when a merged manifest requests an unapproved permission."""


def manifest_permissions(text: str, source: str = "AndroidManifest.xml") -> set[str]:
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        raise AndroidPermissionError(f"{source}: invalid manifest XML: {exc}") from exc

    permissions: set[str] = set()
    for tag in ("uses-permission", "uses-permission-sdk-23"):
        for node in root.findall(tag):
            name = node.get(ANDROID_NS + "name", "")
            if name:
                permissions.add(name)
    return permissions


def verify_permission_state(permissions: set[str], source: str) -> set[str]:
    unexpected = sorted(
        permission
        for permission in permissions
        if permission not in ALLOWED_PERMISSIONS
    )
    if unexpected:
        raise AndroidPermissionError(
            f"{source}: unapproved Android permissions: {', '.join(unexpected)}"
        )
    missing = sorted(REQUIRED_PERMISSIONS - permissions)
    if missing:
        raise AndroidPermissionError(
            f"{source}: required Android permissions missing: {', '.join(missing)}"
        )
    return permissions


def verify_permission_manifest(path: Path) -> set[str]:
    text = path.read_text(encoding="utf-8")
    permissions = manifest_permissions(text, str(path))
    return verify_permission_state(permissions, str(path))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, help="Merged AndroidManifest.xml")
    args = parser.parse_args()
    try:
        permissions = verify_permission_manifest(args.manifest)
    except (OSError, AndroidPermissionError) as exc:
        parser.error(str(exc))
    print(f"Android permission allowlist verified: {args.manifest}")
    for permission in sorted(permissions):
        print(f"  {permission}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

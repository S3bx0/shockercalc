"""Verify that the final Android manifest explicitly blocks cleartext traffic."""

from __future__ import annotations

import argparse
import xml.etree.ElementTree as ET
from pathlib import Path

ANDROID_NS = "{http://schemas.android.com/apk/res/android}"


class AndroidNetworkSecurityError(RuntimeError):
    """Raised when the final manifest permits or may permit cleartext traffic."""


def verify_network_security_manifest(path: Path) -> None:
    try:
        root = ET.fromstring(path.read_text(encoding="utf-8"))
    except (OSError, ET.ParseError) as exc:
        raise AndroidNetworkSecurityError(f"{path}: invalid manifest XML: {exc}") from exc

    application = root.find("application")
    if application is None:
        raise AndroidNetworkSecurityError(f"{path}: missing application element")

    cleartext = application.get(ANDROID_NS + "usesCleartextTraffic")
    if cleartext != "false":
        value = "missing" if cleartext is None else repr(cleartext)
        raise AndroidNetworkSecurityError(
            f"{path}: android:usesCleartextTraffic must be false, got {value}"
        )

    network_config = application.get(ANDROID_NS + "networkSecurityConfig")
    if network_config is not None:
        raise AndroidNetworkSecurityError(
            f"{path}: unreviewed android:networkSecurityConfig: {network_config}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, help="Merged AndroidManifest.xml")
    args = parser.parse_args()
    try:
        verify_network_security_manifest(args.manifest)
    except AndroidNetworkSecurityError as exc:
        parser.error(str(exc))
    print(f"Android cleartext traffic is explicitly disabled: {args.manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

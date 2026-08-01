"""Verify that an Android package cannot auto-start Firebase before consent."""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

FIREBASE_INIT_PROVIDER = "com.google.firebase.provider.FirebaseInitProvider"
REQUIRED_FALSE_METADATA = (
    "firebase_data_collection_default_enabled",
    "firebase_analytics_collection_enabled",
    "firebase_crashlytics_collection_enabled",
    "google_analytics_adid_collection_enabled",
    "google_analytics_default_allow_ad_personalization_signals",
)
ANDROID_NS = "{http://schemas.android.com/apk/res/android}"


class FirebaseManifestError(RuntimeError):
    """Raised when an Android manifest violates the Firebase opt-in policy."""


def _metadata_from_xmltree(text: str) -> tuple[set[str], set[str]]:
    providers: set[str] = set()
    disabled: set[str] = set()
    current_element = ""
    current_name = ""
    for raw_line in text.splitlines():
        line = raw_line.strip()
        element = re.match(r"E:\s+([\w.-]+)", line)
        if element:
            current_element = element.group(1)
            current_name = ""
            continue
        name = re.search(r":name(?:\([^)]*\))?=\"([^\"]+)\"", line)
        if name:
            current_name = name.group(1)
            if current_element == "provider":
                providers.add(current_name)
            continue
        value = re.search(r":value(?:\([^)]*\))?=(false|true)\b", line)
        if current_element == "meta-data" and current_name and value:
            if value.group(1) == "false":
                disabled.add(current_name)
    return providers, disabled


def _metadata_from_xml(text: str) -> tuple[set[str], set[str]]:
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        raise FirebaseManifestError(f"Invalid Android manifest XML: {exc}") from exc
    application = root.find("application")
    if application is None:
        raise FirebaseManifestError("Android manifest has no application element")
    providers = {
        node.get(ANDROID_NS + "name", "") for node in application.findall("provider")
    }
    disabled = {
        node.get(ANDROID_NS + "name", "")
        for node in application.findall("meta-data")
        if node.get(ANDROID_NS + "value", "").lower() == "false"
    }
    return providers, disabled


def verify_manifest_state(
    providers: set[str], disabled_metadata: set[str], source: str
) -> None:
    if FIREBASE_INIT_PROVIDER in providers:
        raise FirebaseManifestError(
            f"{source}: FirebaseInitProvider is present and can initialize Firebase "
            "before consent"
        )
    missing = sorted(set(REQUIRED_FALSE_METADATA) - disabled_metadata)
    if missing:
        raise FirebaseManifestError(
            f"{source}: required false Firebase metadata missing: {', '.join(missing)}"
        )


def verify_xmltree(text: str, source: str = "aapt2 manifest") -> None:
    providers, disabled = _metadata_from_xmltree(text)
    verify_manifest_state(providers, disabled, source)


def verify_xml_manifest(path: Path) -> None:
    providers, disabled = _metadata_from_xml(path.read_text(encoding="utf-8"))
    verify_manifest_state(providers, disabled, str(path))


def _version_key(path: Path) -> tuple[int, ...]:
    return tuple(int(part) for part in re.findall(r"\d+", path.parent.name))


def find_aapt2(explicit: str | None = None) -> str:
    if explicit:
        candidate = Path(explicit)
        if candidate.is_file():
            return str(candidate)
        raise FirebaseManifestError(f"aapt2 not found: {candidate}")
    found = shutil.which("aapt2")
    if found:
        return found
    executable = "aapt2.exe" if os.name == "nt" else "aapt2"
    candidates: list[Path] = []
    sdk_roots: set[Path] = set()
    for variable in ("ANDROID_HOME", "ANDROID_SDK_ROOT"):
        sdk_root_value = os.environ.get(variable)
        if sdk_root_value:
            sdk_roots.add(Path(sdk_root_value))
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        sdk_roots.add(Path(local_app_data) / "Android" / "Sdk")
    for sdk_root_path in sdk_roots:
        candidates.extend(sdk_root_path.glob(f"build-tools/*/{executable}"))
    if candidates:
        return str(max(candidates, key=_version_key))
    raise FirebaseManifestError("aapt2 was not found in PATH or Android SDK")


def verify_apk(path: Path, aapt2: str | None = None) -> None:
    command = [
        find_aapt2(aapt2),
        "dump",
        "xmltree",
        "--file",
        "AndroidManifest.xml",
        str(path),
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode:
        raise FirebaseManifestError(
            f"aapt2 could not inspect {path}: {result.stderr.strip()}"
        )
    verify_xmltree(result.stdout, str(path))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact", type=Path, help="APK or merged AndroidManifest.xml")
    parser.add_argument("--aapt2", help="Explicit path to aapt2")
    args = parser.parse_args()
    if not args.artifact.is_file():
        parser.error(f"file does not exist: {args.artifact}")
    try:
        if args.artifact.suffix.lower() == ".apk":
            verify_apk(args.artifact, args.aapt2)
        elif args.artifact.suffix.lower() == ".xml":
            verify_xml_manifest(args.artifact)
        else:
            raise FirebaseManifestError("expected an APK or AndroidManifest.xml")
    except (OSError, FirebaseManifestError) as exc:
        parser.error(str(exc))
    print(f"Firebase opt-in manifest verified: {args.artifact}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

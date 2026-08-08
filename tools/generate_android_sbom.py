"""Generate a deterministic CycloneDX SBOM from a signed Android App Bundle."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import tarfile
import uuid
import xml.etree.ElementTree as ET
import zipfile
from collections.abc import Iterable
from pathlib import Path
from urllib.parse import quote

ANDROID_NS = "{http://schemas.android.com/apk/res/android}"
CYCLONEDX_SCHEMA = "https://cyclonedx.org/schema/bom-1.6.schema.json"
_DIST_INFO = re.compile(r"^(?P<name>.+)-(?P<version>\d[^/]*)\.dist-info$")
_PINNED_REQUIREMENT = re.compile(
    r"^(?P<name>[A-Za-z0-9_.-]+)==(?P<version>[^\s;]+)$"
)
_GRADLE_DEPENDENCY = re.compile(
    r"(?:\+---|\\---)\s+"
    r"(?P<group>[A-Za-z0-9_.-]+):(?P<name>[A-Za-z0-9_.-]+):"
    r"(?P<requested>[^\s]+)(?:\s+->\s+(?P<resolved>[^\s]+))?"
)
_NATIVE_LIBRARY = re.compile(
    r"^(?:[^/]+/)?lib/(?P<abi>[^/]+)/(?P<name>[^/]+\.so)$"
)


class AndroidSbomError(RuntimeError):
    """Raised when the bundle cannot produce an exact, auditable SBOM."""


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_python_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _purl_part(value: str) -> str:
    return quote(value, safe=".-_~")


def _properties(**values: str) -> list[dict[str, str]]:
    return [
        {"name": f"pl.smilczarek.refrigerationcalc:{name}", "value": value}
        for name, value in sorted(values.items())
    ]


def parse_pinned_requirements(path: Path) -> dict[str, str]:
    """Read an exact Python requirements allowlist used by the Android build."""

    requirements: dict[str, str] = {}
    for number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        match = _PINNED_REQUIREMENT.fullmatch(line)
        if match is None:
            raise AndroidSbomError(
                f"{path}:{number}: Android SBOM requires an exact name==version pin"
            )
        name = _canonical_python_name(match.group("name"))
        version = match.group("version")
        previous = requirements.setdefault(name, version)
        if previous != version:
            raise AndroidSbomError(
                f"{path}:{number}: conflicting versions for {name}: {previous}, {version}"
            )
    if not requirements:
        raise AndroidSbomError(f"{path}: no pinned Android Python requirements")
    return requirements


def _python_bundle_payload(archive: zipfile.ZipFile) -> tuple[str, bytes]:
    names = sorted(name for name in archive.namelist() if name.endswith("libpybundle.so"))
    if len(names) != 1:
        raise AndroidSbomError(
            f"expected exactly one libpybundle.so in AAB, found {len(names)}"
        )
    return names[0], archive.read(names[0])


def python_components(
    archive: zipfile.ZipFile, expected: dict[str, str]
) -> list[dict[str, object]]:
    """Inventory the Python distributions actually embedded in libpybundle.so."""

    bundle_path, payload = _python_bundle_payload(archive)
    distributions: dict[tuple[str, str], set[str]] = {}
    try:
        with tarfile.open(fileobj=io.BytesIO(payload), mode="r:*") as bundle:
            for member in bundle.getmembers():
                marker = ".dist-info/"
                if marker not in member.name:
                    continue
                directory = member.name.split(marker, 1)[0] + ".dist-info"
                match = _DIST_INFO.fullmatch(Path(directory).name)
                if match is None:
                    continue
                name = _canonical_python_name(match.group("name"))
                version = match.group("version")
                distributions.setdefault((name, version), set()).add(directory)
    except tarfile.TarError as exc:
        raise AndroidSbomError(f"{bundle_path}: invalid Python bundle: {exc}") from exc

    if not distributions:
        raise AndroidSbomError(f"{bundle_path}: no embedded Python distributions found")

    found = set(distributions)
    missing = sorted((name, version) for name, version in expected.items() if (name, version) not in found)
    if missing:
        details = ", ".join(f"{name}=={version}" for name, version in missing)
        raise AndroidSbomError(f"AAB is missing pinned Python distributions: {details}")

    components: list[dict[str, object]] = []
    for (name, version), paths in sorted(distributions.items()):
        purl = f"pkg:pypi/{_purl_part(name)}@{_purl_part(version)}"
        components.append(
            {
                "type": "library",
                "bom-ref": purl,
                "name": name,
                "version": version,
                "purl": purl,
                "properties": _properties(
                    ecosystem="python",
                    embedded_paths=";".join(sorted(paths)),
                    source=bundle_path,
                ),
            }
        )
    return components


def parse_gradle_dependencies(path: Path) -> list[dict[str, object]]:
    """Parse all resolved Maven modules from Gradle's runtime dependency report."""

    modules: set[tuple[str, str, str]] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        match = _GRADLE_DEPENDENCY.search(line)
        if match is None:
            continue
        version = match.group("resolved") or match.group("requested")
        if version == "FAILED":
            raise AndroidSbomError(f"{path}: unresolved Gradle dependency: {line.strip()}")
        if version.count(":") >= 2:
            version = version.rsplit(":", 1)[-1]
        modules.add((match.group("group"), match.group("name"), version))

    if not modules:
        raise AndroidSbomError(f"{path}: no resolved Maven dependencies found")

    components: list[dict[str, object]] = []
    for group, name, version in sorted(modules):
        purl = (
            f"pkg:maven/{_purl_part(group)}/{_purl_part(name)}"
            f"@{_purl_part(version)}"
        )
        components.append(
            {
                "type": "library",
                "bom-ref": purl,
                "group": group,
                "name": name,
                "version": version,
                "purl": purl,
                "properties": _properties(ecosystem="maven", configuration="releaseRuntimeClasspath"),
            }
        )
    return components


def native_components(archive: zipfile.ZipFile) -> list[dict[str, object]]:
    """Hash every native library shipped in the AAB, grouped by archive path."""

    components: list[dict[str, object]] = []
    for path in sorted(archive.namelist()):
        match = _NATIVE_LIBRARY.fullmatch(path)
        if match is None:
            continue
        digest = _sha256_bytes(archive.read(path))
        bom_ref = f"file:{path}?sha256={digest}"
        components.append(
            {
                "type": "file",
                "bom-ref": bom_ref,
                "name": match.group("name"),
                "hashes": [{"alg": "SHA-256", "content": digest}],
                "properties": _properties(abi=match.group("abi"), archive_path=path),
            }
        )
    if not components:
        raise AndroidSbomError("AAB contains no native Android libraries")
    return components


def parse_android_manifest(path: Path) -> tuple[str, str, str]:
    """Return the package ID, version name and version code dumped from the AAB."""

    try:
        root = ET.fromstring(path.read_text(encoding="utf-8"))
    except (OSError, ET.ParseError) as exc:
        raise AndroidSbomError(f"{path}: invalid Android manifest XML: {exc}") from exc
    package_id = root.get("package", "").strip()
    version_name = root.get(ANDROID_NS + "versionName", "").strip()
    version_code = root.get(ANDROID_NS + "versionCode", "").strip()
    if not package_id or not version_name or not version_code:
        raise AndroidSbomError(
            f"{path}: package, android:versionName and android:versionCode are required"
        )
    return package_id, version_name, version_code


def _component_refs(components: Iterable[dict[str, object]]) -> list[str]:
    return sorted(str(component["bom-ref"]) for component in components)


def generate_android_sbom(
    aab_path: Path,
    *,
    manifest_path: Path,
    python_requirements_path: Path,
    gradle_report_path: Path,
) -> dict[str, object]:
    """Build a deterministic CycloneDX 1.6 document for an exact signed AAB."""

    package_id, version_name, version_code = parse_android_manifest(manifest_path)
    aab_digest = _sha256_file(aab_path)
    expected_python = parse_pinned_requirements(python_requirements_path)
    try:
        with zipfile.ZipFile(aab_path) as archive:
            components = python_components(archive, expected_python)
            components.extend(native_components(archive))
    except (OSError, zipfile.BadZipFile) as exc:
        raise AndroidSbomError(f"{aab_path}: invalid AAB: {exc}") from exc
    components.extend(parse_gradle_dependencies(gradle_report_path))
    components.sort(key=lambda component: str(component["bom-ref"]))

    app_purl = (
        "pkg:generic/pl.smilczarek/refrigeration-calc"
        f"@{_purl_part(version_name)}?arch=arm64-v8a"
    )
    serial_seed = f"{package_id}:{version_name}:{version_code}:{aab_digest}"
    serial = uuid.uuid5(uuid.NAMESPACE_URL, serial_seed)
    return {
        "$schema": CYCLONEDX_SCHEMA,
        "bomFormat": "CycloneDX",
        "specVersion": "1.6",
        "serialNumber": f"urn:uuid:{serial}",
        "version": 1,
        "metadata": {
            "component": {
                "type": "application",
                "bom-ref": app_purl,
                "group": "pl.smilczarek",
                "name": "Refrigeration Calc",
                "version": version_name,
                "purl": app_purl,
                "hashes": [{"alg": "SHA-256", "content": aab_digest}],
                "properties": _properties(
                    android_package=package_id,
                    android_version_code=version_code,
                    artifact_name=aab_path.name,
                    target_abi="arm64-v8a",
                ),
            }
        },
        "components": components,
        "dependencies": [{"ref": app_purl, "dependsOn": _component_refs(components)}],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("aab", type=Path, help="Signed Android App Bundle")
    parser.add_argument("--manifest", type=Path, required=True, help="bundletool manifest dump")
    parser.add_argument(
        "--python-requirements",
        type=Path,
        required=True,
        help="exact Android Python requirements",
    )
    parser.add_argument(
        "--gradle-report",
        type=Path,
        required=True,
        help="Gradle releaseRuntimeClasspath dependency report",
    )
    parser.add_argument("--output", type=Path, required=True, help="CycloneDX JSON output")
    args = parser.parse_args()

    try:
        document = generate_android_sbom(
            args.aab,
            manifest_path=args.manifest,
            python_requirements_path=args.python_requirements,
            gradle_report_path=args.gradle_report,
        )
    except AndroidSbomError as exc:
        parser.error(str(exc))
    args.output.write_text(
        json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    components = document["components"]
    if not isinstance(components, list):
        raise AndroidSbomError("generated SBOM components must be a list")
    print(f"CycloneDX SBOM generated: {args.output}")
    print(f"  components: {len(components)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

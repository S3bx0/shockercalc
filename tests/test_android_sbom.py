import gzip
import io
import json
import tarfile
import zipfile
from pathlib import Path

import pytest

from tools.generate_android_sbom import (
    AndroidSbomError,
    generate_android_sbom,
    parse_gradle_dependencies,
    parse_pinned_requirements,
)


def _write_python_bundle(distributions: list[str]) -> bytes:
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w") as archive:
        for distribution in distributions:
            data = f"Name: {distribution}\n".encode()
            info = tarfile.TarInfo(
                f"_python_bundle/site-packages/{distribution}.dist-info/METADATA"
            )
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
    return gzip.compress(raw.getvalue(), mtime=0)


def _write_aab(path: Path, distributions: list[str]) -> None:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "base/lib/arm64-v8a/libpybundle.so",
            _write_python_bundle(distributions),
        )
        archive.writestr("base/lib/arm64-v8a/libpython3.13.so", b"python-runtime")


def _write_inputs(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    aab = tmp_path / "refrigerationcalc-1.5.13.aab"
    _write_aab(aab, ["Kivy-2.3.1", "pillow-12.3.0", "requests-2.34.2"])
    manifest = tmp_path / "AndroidManifest.xml"
    manifest.write_text(
        """<manifest xmlns:android="http://schemas.android.com/apk/res/android"
        package="pl.smilczarek.refrigerationcalc"
        android:versionName="1.5.13" android:versionCode="123" />""",
        encoding="utf-8",
    )
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("kivy==2.3.1\nPillow==12.3.0\n", encoding="utf-8")
    gradle = tmp_path / "gradle.txt"
    gradle.write_text(
        """releaseRuntimeClasspath - Runtime classpath of '/release'.
+--- com.google.firebase:firebase-analytics:23.1.0 -> 23.2.0
|    +--- com.google.android.gms:play-services-measurement-api:23.0.0
|    \\--- androidx.annotation:annotation:1.9.1 (*)
\\--- com.android.billingclient:billing:9.1.0
     \\--- project :ignored
""",
        encoding="utf-8",
    )
    return aab, manifest, requirements, gradle


def test_android_sbom_inventories_exact_bundle_and_resolved_dependencies(tmp_path):
    aab, manifest, requirements, gradle = _write_inputs(tmp_path)

    document = generate_android_sbom(
        aab,
        manifest_path=manifest,
        python_requirements_path=requirements,
        gradle_report_path=gradle,
    )

    assert document["bomFormat"] == "CycloneDX"
    assert document["specVersion"] == "1.6"
    assert str(document["serialNumber"]).startswith("urn:uuid:")
    metadata = document["metadata"]["component"]
    assert metadata["version"] == "1.5.13"
    assert metadata["hashes"][0]["alg"] == "SHA-256"

    components = {component["bom-ref"]: component for component in document["components"]}
    assert "pkg:pypi/kivy@2.3.1" in components
    assert "pkg:pypi/pillow@12.3.0" in components
    assert "pkg:pypi/requests@2.34.2" in components
    assert "pkg:maven/com.google.firebase/firebase-analytics@23.2.0" in components
    assert (
        "pkg:maven/com.google.android.gms/play-services-measurement-api@23.0.0"
        in components
    )
    native = [component for component in components.values() if component["type"] == "file"]
    assert {component["name"] for component in native} == {
        "libpybundle.so",
        "libpython3.13.so",
    }
    assert all(component["hashes"][0]["alg"] == "SHA-256" for component in native)
    assert document["dependencies"][0]["dependsOn"] == sorted(components)


def test_android_sbom_is_deterministic_for_the_same_signed_aab(tmp_path):
    aab, manifest, requirements, gradle = _write_inputs(tmp_path)

    first = generate_android_sbom(
        aab,
        manifest_path=manifest,
        python_requirements_path=requirements,
        gradle_report_path=gradle,
    )
    second = generate_android_sbom(
        aab,
        manifest_path=manifest,
        python_requirements_path=requirements,
        gradle_report_path=gradle,
    )

    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)


def test_android_sbom_rejects_pinned_package_missing_from_bundle(tmp_path):
    aab, manifest, requirements, gradle = _write_inputs(tmp_path)
    requirements.write_text("kivy==2.3.1\ncertifi==2026.6.17\n", encoding="utf-8")

    with pytest.raises(AndroidSbomError, match="certifi==2026.6.17"):
        generate_android_sbom(
            aab,
            manifest_path=manifest,
            python_requirements_path=requirements,
            gradle_report_path=gradle,
        )


def test_android_sbom_requires_exact_python_pins(tmp_path):
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("Pillow>=12.3\n", encoding="utf-8")

    with pytest.raises(AndroidSbomError, match="name==version"):
        parse_pinned_requirements(requirements)


def test_gradle_sbom_parser_rejects_empty_or_unresolved_reports(tmp_path):
    empty = tmp_path / "empty.txt"
    empty.write_text("No dependencies\n", encoding="utf-8")
    with pytest.raises(AndroidSbomError, match="no resolved Maven"):
        parse_gradle_dependencies(empty)

    failed = tmp_path / "failed.txt"
    failed.write_text("\\--- example:broken:1.0 -> FAILED\n", encoding="utf-8")
    with pytest.raises(AndroidSbomError, match="unresolved Gradle"):
        parse_gradle_dependencies(failed)

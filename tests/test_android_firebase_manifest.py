from pathlib import Path

import pytest

from tools.verify_android_firebase_manifest import (
    FIREBASE_INIT_PROVIDER,
    REQUIRED_FALSE_METADATA,
    FirebaseManifestError,
    verify_xml_manifest,
    verify_xmltree,
)


def _xmltree(*, provider: bool = False, missing: str | None = None) -> str:
    lines = ["E: manifest", "  E: application"]
    for name in REQUIRED_FALSE_METADATA:
        if name == missing:
            continue
        lines.extend(
            [
                "    E: meta-data",
                f'      A: android:name(0x01010003)="{name}"',
                "      A: android:value(0x01010024)=false",
            ]
        )
    if provider:
        lines.extend(
            [
                "    E: provider",
                f'      A: android:name(0x01010003)="{FIREBASE_INIT_PROVIDER}"',
            ]
        )
    return "\n".join(lines)


def test_final_apk_manifest_dump_passes_without_auto_init_provider():
    verify_xmltree(_xmltree(), "test.apk")


def test_final_apk_manifest_dump_rejects_firebase_init_provider():
    with pytest.raises(FirebaseManifestError, match="FirebaseInitProvider"):
        verify_xmltree(_xmltree(provider=True), "test.apk")


def test_final_apk_manifest_dump_requires_all_defensive_flags():
    with pytest.raises(FirebaseManifestError, match="firebase_analytics"):
        verify_xmltree(
            _xmltree(missing="firebase_analytics_collection_enabled"),
            "test.apk",
        )


def test_merged_xml_manifest_is_supported(tmp_path: Path):
    metadata = "\n".join(
        f'        <meta-data android:name="{name}" android:value="false" />'
        for name in REQUIRED_FALSE_METADATA
    )
    manifest = tmp_path / "AndroidManifest.xml"
    manifest.write_text(
        f"""<manifest xmlns:android="http://schemas.android.com/apk/res/android">
    <application>
{metadata}
    </application>
</manifest>
""",
        encoding="utf-8",
    )

    verify_xml_manifest(manifest)

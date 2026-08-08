from pathlib import Path

import pytest

from tools.verify_android_backup_policy import (
    AndroidBackupPolicyError,
    verify_backup_policy_manifest,
)


def _manifest(application_attributes: str) -> str:
    return f"""<manifest xmlns:android="http://schemas.android.com/apk/res/android">
    <application {application_attributes} />
</manifest>
"""


def test_accepts_explicit_backup_block(tmp_path: Path):
    manifest = tmp_path / "AndroidManifest.xml"
    manifest.write_text(_manifest('android:allowBackup="false"'), encoding="utf-8")

    verify_backup_policy_manifest(manifest)


@pytest.mark.parametrize(
    "attributes",
    [
        "",
        'android:allowBackup="true"',
        'android:allowBackup="False"',
    ],
)
def test_rejects_missing_or_noncanonical_backup_block(
    tmp_path: Path, attributes: str
):
    manifest = tmp_path / "AndroidManifest.xml"
    manifest.write_text(_manifest(attributes), encoding="utf-8")

    with pytest.raises(AndroidBackupPolicyError, match="allowBackup"):
        verify_backup_policy_manifest(manifest)


def test_rejects_manifest_without_application(tmp_path: Path):
    manifest = tmp_path / "AndroidManifest.xml"
    manifest.write_text("<manifest />", encoding="utf-8")

    with pytest.raises(AndroidBackupPolicyError, match="missing application"):
        verify_backup_policy_manifest(manifest)


def test_rejects_invalid_xml(tmp_path: Path):
    manifest = tmp_path / "AndroidManifest.xml"
    manifest.write_text("<manifest>", encoding="utf-8")

    with pytest.raises(AndroidBackupPolicyError, match="invalid manifest XML"):
        verify_backup_policy_manifest(manifest)

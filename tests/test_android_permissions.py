from pathlib import Path

import pytest

from tools.verify_android_permissions import (
    ALLOWED_PERMISSIONS,
    AndroidPermissionError,
    verify_permission_manifest,
)


def _manifest(permissions: set[str]) -> str:
    nodes = "\n".join(
        f'    <uses-permission android:name="{permission}" />'
        for permission in sorted(permissions)
    )
    return f"""<manifest xmlns:android="http://schemas.android.com/apk/res/android">
{nodes}
    <application />
</manifest>
"""


def test_accepts_current_final_permission_set(tmp_path: Path):
    permissions = set(ALLOWED_PERMISSIONS)
    manifest = tmp_path / "AndroidManifest.xml"
    manifest.write_text(_manifest(permissions), encoding="utf-8")

    assert verify_permission_manifest(manifest) == permissions


@pytest.mark.parametrize(
    "permission",
    [
        "android.permission.CAMERA",
        "android.permission.RECORD_AUDIO",
        "android.permission.ACCESS_FINE_LOCATION",
        "android.permission.READ_CONTACTS",
        "android.permission.READ_MEDIA_IMAGES",
    ],
)
def test_rejects_unapproved_sensitive_permission(tmp_path: Path, permission: str):
    manifest = tmp_path / "AndroidManifest.xml"
    manifest.write_text(
        _manifest(set(ALLOWED_PERMISSIONS) | {permission}), encoding="utf-8"
    )

    with pytest.raises(AndroidPermissionError, match=permission):
        verify_permission_manifest(manifest)


def test_rejects_generated_permission_for_a_different_package(tmp_path: Path):
    permission = "example.injected.DYNAMIC_RECEIVER_NOT_EXPORTED_PERMISSION"
    manifest = tmp_path / "AndroidManifest.xml"
    manifest.write_text(
        _manifest(set(ALLOWED_PERMISSIONS) | {permission}), encoding="utf-8"
    )

    with pytest.raises(AndroidPermissionError, match=permission):
        verify_permission_manifest(manifest)


def test_requires_core_network_and_billing_permissions(tmp_path: Path):
    manifest = tmp_path / "AndroidManifest.xml"
    manifest.write_text(
        _manifest(set(ALLOWED_PERMISSIONS) - {"com.android.vending.BILLING"}),
        encoding="utf-8",
    )

    with pytest.raises(AndroidPermissionError, match="BILLING"):
        verify_permission_manifest(manifest)

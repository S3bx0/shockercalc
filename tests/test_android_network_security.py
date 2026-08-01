from pathlib import Path

import pytest

from tools.verify_android_network_security import (
    AndroidNetworkSecurityError,
    verify_network_security_manifest,
)


def _manifest(application_attributes: str) -> str:
    return f"""<manifest xmlns:android="http://schemas.android.com/apk/res/android">
    <application {application_attributes} />
</manifest>
"""


def test_accepts_explicit_cleartext_block(tmp_path: Path):
    manifest = tmp_path / "AndroidManifest.xml"
    manifest.write_text(
        _manifest('android:usesCleartextTraffic="false"'), encoding="utf-8"
    )

    verify_network_security_manifest(manifest)


@pytest.mark.parametrize(
    "attributes",
    [
        "",
        'android:usesCleartextTraffic="true"',
        'android:usesCleartextTraffic="False"',
    ],
)
def test_rejects_missing_or_noncanonical_cleartext_block(
    tmp_path: Path, attributes: str
):
    manifest = tmp_path / "AndroidManifest.xml"
    manifest.write_text(_manifest(attributes), encoding="utf-8")

    with pytest.raises(AndroidNetworkSecurityError, match="usesCleartextTraffic"):
        verify_network_security_manifest(manifest)


def test_rejects_unreviewed_network_security_config(tmp_path: Path):
    manifest = tmp_path / "AndroidManifest.xml"
    manifest.write_text(
        _manifest(
            'android:usesCleartextTraffic="false" '
            'android:networkSecurityConfig="@xml/network_security_config"'
        ),
        encoding="utf-8",
    )

    with pytest.raises(AndroidNetworkSecurityError, match="networkSecurityConfig"):
        verify_network_security_manifest(manifest)

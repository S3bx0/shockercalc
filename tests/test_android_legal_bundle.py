from __future__ import annotations

import io
import tarfile
import zipfile

import pytest

from tools.verify_android_legal_bundle import (
    CONTACT_EMAIL,
    CONTACT_FILES,
    REQUIRED_LEGAL_FILES,
    verify_legal_bundle,
)


def _write_aab(
    path,
    *,
    omitted=frozenset(),
    compressed=True,
    contact_email=CONTACT_EMAIL,
):
    markers = {
        "LICENSE": "LicenseRef-RefrigerationCalc-Proprietary-1.0",
        "EULA": "End-User License Agreement",
        "AI_USAGE_POLICY": "TDM-Reservation: 1",
        "THIRD_PARTY_NOTICES": "fpdf2 2.8.7",
        "legal/GPL-3.0-only": "GNU GENERAL PUBLIC LICENSE",
        "legal/LGPL-3.0-only": "GNU LESSER GENERAL PUBLIC LICENSE",
    }
    private = io.BytesIO()
    mode = "w:gz" if compressed else "w"
    with tarfile.open(fileobj=private, mode=mode) as archive:
        for name, marker in markers.items():
            if name in omitted:
                continue
            if name in CONTACT_FILES:
                marker = f"{marker}\n{contact_email}"
            payload = marker.encode("utf-8")
            member = tarfile.TarInfo(name)
            member.size = len(payload)
            archive.addfile(member, io.BytesIO(payload))
    with zipfile.ZipFile(path, mode="w") as bundle:
        bundle.writestr("base/assets/private.tar", private.getvalue())


def test_android_legal_bundle_accepts_buildozer_gzip_private_tar(tmp_path):
    aab = tmp_path / "app.aab"
    _write_aab(aab)

    assert verify_legal_bundle(aab) == REQUIRED_LEGAL_FILES


def test_android_legal_bundle_accepts_uncompressed_private_tar(tmp_path):
    aab = tmp_path / "app.aab"
    _write_aab(aab, compressed=False)

    assert verify_legal_bundle(aab) == REQUIRED_LEGAL_FILES


def test_android_legal_bundle_reports_missing_notice(tmp_path):
    aab = tmp_path / "app.aab"
    _write_aab(aab, omitted={"EULA"})

    with pytest.raises(ValueError, match="missing legal files: EULA"):
        verify_legal_bundle(aab)


def test_android_legal_bundle_rejects_outdated_contact(tmp_path):
    aab = tmp_path / "app.aab"
    _write_aab(aab, contact_email="outdated@example.invalid")

    with pytest.raises(ValueError, match="does not contain contact"):
        verify_legal_bundle(aab)

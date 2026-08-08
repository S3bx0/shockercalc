import gzip
import io
import tarfile
import zipfile
from pathlib import Path

import pytest

from tools.verify_android_python_packages import verify_python_packages


def _package(tmp_path: Path, members: dict[str, bytes]) -> Path:
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w") as bundle:
        for name, content in members.items():
            info = tarfile.TarInfo(name)
            info.size = len(content)
            bundle.addfile(info, io.BytesIO(content))

    package = tmp_path / "app.aab"
    with zipfile.ZipFile(package, "w") as archive:
        archive.writestr(
            "base/lib/arm64-v8a/libpybundle.so",
            gzip.compress(raw.getvalue(), mtime=0),
        )
    return package


def _pillow_members(version: str = "12.3.0") -> dict[str, bytes]:
    root = "_python_bundle/site-packages"
    return {
        f"{root}/pillow-{version}.dist-info/METADATA": b"metadata",
        f"{root}/PIL/__init__.pyc": b"python",
        f"{root}/PIL/_imaging.so": b"native",
        f"{root}/PIL/_imagingft.so": b"native-font",
    }


def test_accepts_expected_pillow_runtime(tmp_path):
    package = _package(tmp_path, _pillow_members())

    assert verify_python_packages(package) == {"12.3.0"}


def test_rejects_stale_pillow_version(tmp_path):
    package = _package(tmp_path, _pillow_members("11.3.0"))

    with pytest.raises(ValueError, match=r"expected Pillow 12\.3\.0, found 11\.3\.0"):
        verify_python_packages(package)


def test_rejects_incomplete_pillow_runtime(tmp_path):
    members = _pillow_members()
    del members["_python_bundle/site-packages/PIL/_imagingft.so"]
    package = _package(tmp_path, members)

    with pytest.raises(ValueError, match="incomplete Pillow runtime"):
        verify_python_packages(package)

import zipfile
from pathlib import Path

import pytest

from tools.verify_android_abi_bundle import (
    REQUIRED_RUNTIME_LIBRARIES,
    inspect_android_abis,
    verify_android_abi_bundle,
)


def _write_archive(
    path: Path,
    libraries: dict[str, set[str]],
    *,
    bundle: bool = True,
) -> None:
    prefix = "base/" if bundle else ""
    with zipfile.ZipFile(path, "w") as archive:
        for abi, names in libraries.items():
            for name in names:
                archive.writestr(f"{prefix}lib/{abi}/{name}", b"native")


@pytest.mark.parametrize("bundle", [True, False])
def test_abi_verifier_accepts_complete_arm64_runtime(tmp_path, bundle):
    archive = tmp_path / ("app.aab" if bundle else "app.apk")
    _write_archive(
        archive,
        {"arm64-v8a": set(REQUIRED_RUNTIME_LIBRARIES) | {"libssl.so"}},
        bundle=bundle,
    )

    packaged = verify_android_abi_bundle(archive)

    assert inspect_android_abis(archive) == packaged
    assert REQUIRED_RUNTIME_LIBRARIES <= packaged["arm64-v8a"]


def test_abi_verifier_rejects_dependency_only_unsupported_abi(tmp_path):
    archive = tmp_path / "app.aab"
    _write_archive(
        archive,
        {
            "arm64-v8a": set(REQUIRED_RUNTIME_LIBRARIES),
            "x86_64": {"libdatastore_shared_counter.so"},
        },
    )

    with pytest.raises(ValueError, match=r"unsupported ABI: x86_64"):
        verify_android_abi_bundle(archive)


def test_abi_verifier_rejects_incomplete_supported_runtime(tmp_path):
    archive = tmp_path / "app.aab"
    libraries = set(REQUIRED_RUNTIME_LIBRARIES) - {"libpybundle.so"}
    _write_archive(archive, {"arm64-v8a": libraries})

    with pytest.raises(ValueError, match=r"arm64-v8a missing.*libpybundle\.so"):
        verify_android_abi_bundle(archive)


def test_abi_verifier_rejects_archive_without_native_runtime(tmp_path):
    archive = tmp_path / "app.aab"
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr("base/manifest/AndroidManifest.xml", b"manifest")

    with pytest.raises(ValueError, match=r"missing ABI: arm64-v8a"):
        verify_android_abi_bundle(archive)

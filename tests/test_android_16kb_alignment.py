import struct
import zipfile
from pathlib import Path

import pytest

from tools.verify_android_16kb_alignment import (
    AndroidAlignmentError,
    verify_android_16kb_alignment,
    write_alignment_report,
)


def _elf64(load_alignment: int) -> bytes:
    data = bytearray(64 + 56)
    data[:4] = b"\x7fELF"
    data[4] = 2
    data[5] = 1
    struct.pack_into("<Q", data, 32, 64)
    struct.pack_into("<H", data, 54, 56)
    struct.pack_into("<H", data, 56, 1)
    struct.pack_into("<IIQQQQQQ", data, 64, 1, 5, 0, 0, 0, 0, 0, load_alignment)
    return bytes(data)


def _archive(tmp_path: Path, alignment: int) -> Path:
    archive = tmp_path / "app.aab"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("base/lib/arm64-v8a/libmain.so", _elf64(alignment))
    return archive


def test_accepts_16kb_native_load_segments(tmp_path: Path):
    archive = _archive(tmp_path, 0x4000)

    inspected = verify_android_16kb_alignment(archive)

    assert inspected == {"base/lib/arm64-v8a/libmain.so": (0x4000,)}


def test_accepts_larger_native_load_alignment(tmp_path: Path):
    verify_android_16kb_alignment(_archive(tmp_path, 0x10000))


def test_rejects_4kb_native_load_segments(tmp_path: Path):
    with pytest.raises(AndroidAlignmentError, match="below 16 KB"):
        verify_android_16kb_alignment(_archive(tmp_path, 0x1000))


def test_rejects_archive_without_native_libraries(tmp_path: Path):
    archive = tmp_path / "empty.aab"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("base/manifest/AndroidManifest.xml", "manifest")

    with pytest.raises(AndroidAlignmentError, match="no native libraries"):
        verify_android_16kb_alignment(archive)


def test_allows_known_python_bundle_payload(tmp_path: Path):
    archive = _archive(tmp_path, 0x4000)
    with zipfile.ZipFile(archive, "a") as bundle:
        bundle.writestr("base/lib/arm64-v8a/libpybundle.so", b"\x1f\x8bpayload")

    inspected = verify_android_16kb_alignment(archive)

    assert inspected["base/lib/arm64-v8a/libpybundle.so"] == ()


def test_rejects_unexpected_non_elf_so_payload(tmp_path: Path):
    archive = _archive(tmp_path, 0x4000)
    with zipfile.ZipFile(archive, "a") as bundle:
        bundle.writestr("base/lib/arm64-v8a/libunexpected.so", b"not-elf")

    with pytest.raises(AndroidAlignmentError, match="not a valid ELF"):
        verify_android_16kb_alignment(archive)


def test_writes_repeatable_alignment_report(tmp_path: Path):
    archive = _archive(tmp_path, 0x4000)
    inspected = verify_android_16kb_alignment(archive)
    report = tmp_path / "report.txt"

    write_alignment_report(archive, inspected, report)

    text = report.read_text(encoding="utf-8")
    assert "base/lib/arm64-v8a/libmain.so: 0x4000" in text
    assert "ELF native libraries inspected: 1" in text
    assert "Known non-ELF .so payloads skipped: 0" in text

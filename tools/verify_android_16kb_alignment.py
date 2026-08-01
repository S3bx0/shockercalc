"""Verify that every packaged Android native library supports 16 KB pages."""

from __future__ import annotations

import argparse
import struct
import zipfile
from pathlib import Path

REQUIRED_PAGE_ALIGNMENT = 16 * 1024
PT_LOAD = 1
KNOWN_NON_ELF_SO_PAYLOADS = frozenset({"libpybundle.so"})


class AndroidAlignmentError(RuntimeError):
    """Raised when a packaged native library is not compatible with 16 KB pages."""


def _load_segment_alignments(data: bytes, source: str) -> tuple[int, ...]:
    if len(data) < 16 or data[:4] != b"\x7fELF":
        raise AndroidAlignmentError(f"{source}: native library is not a valid ELF file")

    elf_class = data[4]
    byte_order = data[5]
    if byte_order not in (1, 2):
        raise AndroidAlignmentError(f"{source}: unsupported ELF byte order {byte_order}")
    prefix = "<" if byte_order == 1 else ">"

    if elf_class == 2:
        header_size = 64
        program_header = prefix + "IIQQQQQQ"
        program_offset_position = 32
        entry_size_position = 54
        entry_count_position = 56
        offset_format = prefix + "Q"
    elif elf_class == 1:
        header_size = 52
        program_header = prefix + "IIIIIIII"
        program_offset_position = 28
        entry_size_position = 42
        entry_count_position = 44
        offset_format = prefix + "I"
    else:
        raise AndroidAlignmentError(f"{source}: unsupported ELF class {elf_class}")

    if len(data) < header_size:
        raise AndroidAlignmentError(f"{source}: truncated ELF header")
    program_offset = struct.unpack_from(offset_format, data, program_offset_position)[0]
    entry_size = struct.unpack_from(prefix + "H", data, entry_size_position)[0]
    entry_count = struct.unpack_from(prefix + "H", data, entry_count_position)[0]
    minimum_entry_size = struct.calcsize(program_header)
    if entry_size < minimum_entry_size:
        raise AndroidAlignmentError(
            f"{source}: invalid program-header size {entry_size}"
        )

    alignments: list[int] = []
    for index in range(entry_count):
        offset = program_offset + index * entry_size
        if offset + minimum_entry_size > len(data):
            raise AndroidAlignmentError(f"{source}: truncated program-header table")
        header = struct.unpack_from(program_header, data, offset)
        if header[0] == PT_LOAD:
            alignments.append(header[-1])
    if not alignments:
        raise AndroidAlignmentError(f"{source}: ELF file has no loadable segments")
    return tuple(alignments)


def inspect_android_16kb_alignment(archive_path: Path) -> dict[str, tuple[int, ...]]:
    """Return PT_LOAD alignments for every packaged ``.so`` file."""

    inspected: dict[str, tuple[int, ...]] = {}
    with zipfile.ZipFile(archive_path) as archive:
        for name in sorted(entry for entry in archive.namelist() if entry.endswith(".so")):
            data = archive.read(name)
            if data[:4] != b"\x7fELF" and Path(name).name in KNOWN_NON_ELF_SO_PAYLOADS:
                inspected[name] = ()
                continue
            inspected[name] = _load_segment_alignments(data, name)
    if not inspected:
        raise AndroidAlignmentError(f"{archive_path}: no native libraries found")
    return inspected


def verify_android_16kb_alignment(
    archive_path: Path,
    *,
    required_alignment: int = REQUIRED_PAGE_ALIGNMENT,
) -> dict[str, tuple[int, ...]]:
    """Reject an APK/AAB containing a PT_LOAD segment below 16 KB alignment."""

    inspected = inspect_android_16kb_alignment(archive_path)
    incompatible = {
        name: tuple(alignment for alignment in alignments if alignment < required_alignment)
        for name, alignments in inspected.items()
        if alignments and any(alignment < required_alignment for alignment in alignments)
    }
    if incompatible:
        details = "; ".join(
            f"{name}: {', '.join(hex(value) for value in values)}"
            for name, values in incompatible.items()
        )
        raise AndroidAlignmentError(
            f"{archive_path}: native PT_LOAD alignment below "
            f"{required_alignment // 1024} KB: {details}"
        )
    return inspected


def write_alignment_report(
    archive_path: Path,
    inspected: dict[str, tuple[int, ...]],
    output_path: Path,
) -> None:
    lines = [
        "16 KB native library alignment report",
        "=====================================",
        f"Archive: {archive_path}",
        "",
    ]
    for name, alignments in inspected.items():
        if alignments:
            lines.append(f"{name}: {' '.join(hex(value) for value in alignments)}")
        else:
            lines.append(f"{name}: known packaged non-ELF payload")
    elf_count = sum(bool(alignments) for alignments in inspected.values())
    lines.extend(
        [
            "",
            f"ELF native libraries inspected: {elf_count}",
            f"Known non-ELF .so payloads skipped: {len(inspected) - elf_count}",
        ]
    )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path, help="APK or AAB to verify")
    parser.add_argument("--report", type=Path, help="Optional text report path")
    args = parser.parse_args()
    try:
        inspected = verify_android_16kb_alignment(args.archive)
    except (OSError, zipfile.BadZipFile, AndroidAlignmentError) as exc:
        parser.error(str(exc))
    if args.report:
        write_alignment_report(args.archive, inspected, args.report)
    print(f"Android 16 KB alignment verified: {args.archive}")
    print(f"  ELF native libraries: {sum(bool(value) for value in inspected.values())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

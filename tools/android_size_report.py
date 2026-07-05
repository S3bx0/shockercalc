"""Generuje powtarzalny raport rozmiaru APK/AAB i bundla Pythona."""

from __future__ import annotations

import argparse
import gzip
import io
import tarfile
import zipfile
from collections import defaultdict
from pathlib import Path

MIB = 1024 * 1024


def _fmt(size: int) -> str:
    return f"{size / MIB:8.2f} MiB"


def _entry_group(name: str) -> str:
    parts = Path(name).parts
    if name.startswith("base/") and len(parts) >= 2:
        return "/".join(parts[:2])
    return parts[0] if parts else "(root)"


def _tar_members(gzip_data: bytes):
    raw = gzip.decompress(gzip_data)
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:") as archive:
        members = [member for member in archive.getmembers() if member.isfile()]
    return raw, members


def _private_group(name: str) -> str:
    parts = Path(name).parts
    return "/".join(parts[:2]) if len(parts) >= 2 else name


def _python_group(name: str) -> str:
    parts = Path(name).parts
    if "site-packages" in parts:
        index = parts.index("site-packages")
        if len(parts) > index + 1:
            return parts[index + 1]
    if len(parts) >= 3:
        return "/".join(parts[:3])
    return name


def build_report(package: Path) -> str:
    lines = [
        "Android package size report",
        "===========================",
        f"Package: {package.name}",
        f"File size: {_fmt(package.stat().st_size)}",
        "",
    ]
    with zipfile.ZipFile(package) as archive:
        grouped = defaultdict(lambda: [0, 0])
        for info in archive.infolist():
            group = _entry_group(info.filename)
            grouped[group][0] += info.compress_size
            grouped[group][1] += info.file_size

        lines.append("ZIP groups (compressed / raw)")
        for group, (compressed, raw) in sorted(
            grouped.items(), key=lambda item: item[1][0], reverse=True
        ):
            lines.append(f"{_fmt(compressed)} / {_fmt(raw)}  {group}")

        private_name = next(
            (name for name in archive.namelist() if name.endswith("assets/private.tar")),
            None,
        )
        if private_name:
            raw, members = _tar_members(archive.read(private_name))
            private_groups = defaultdict(int)
            for member in members:
                private_groups[_private_group(member.name)] += member.size
            lines.extend(
                [
                    "",
                    f"private.tar: {_fmt(len(archive.read(private_name)))} gzip / {_fmt(len(raw))} extracted",
                ]
            )
            for group, size in sorted(
                private_groups.items(), key=lambda item: item[1], reverse=True
            )[:25]:
                lines.append(f"{_fmt(size)}  {group}")

        pybundle_name = next(
            (name for name in archive.namelist() if name.endswith("libpybundle.so")),
            None,
        )
        if pybundle_name:
            raw, members = _tar_members(archive.read(pybundle_name))
            python_groups = defaultdict(int)
            for member in members:
                python_groups[_python_group(member.name)] += member.size
            lines.extend(
                [
                    "",
                    f"Python bundle: {_fmt(len(archive.read(pybundle_name)))} gzip / {_fmt(len(raw))} extracted",
                ]
            )
            for group, size in sorted(
                python_groups.items(), key=lambda item: item[1], reverse=True
            )[:25]:
                lines.append(f"{_fmt(size)}  {group}")

    lines.extend(
        [
            "",
            "Installed size is larger than this archive because Android extracts native",
            "libraries and app data and may create ART-optimized DEX files.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("package", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    report = build_report(args.package)
    if args.output:
        args.output.write_text(report, encoding="utf-8")
    print(report, end="")


if __name__ == "__main__":
    main()

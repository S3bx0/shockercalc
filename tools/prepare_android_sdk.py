"""Keep Buildozer 1.6.0's SDK bootstrap usable with empty or partial caches.

Buildozer skips its SDK download if android-sdk already exists, even when it
contains only licenses. Do not create that directory on a cache miss. Preserve
an incomplete restored SDK under a unique sibling name instead of deleting it.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from uuid import uuid4


def prepare_sdk(platform_dir: Path) -> Path | None:
    platform = platform_dir.resolve()
    sdk = platform / "android-sdk"
    if sdk.is_symlink() or sdk.resolve() != sdk:
        raise ValueError("Refusing to move a redirected Android SDK path")
    if not sdk.exists():
        return None
    if not sdk.is_dir():
        raise ValueError("Android SDK path is not a directory")
    if (sdk / "tools" / "bin" / "sdkmanager").is_file():
        return None
    backup = platform / f"android-sdk-incomplete-{uuid4().hex}"
    sdk.rename(backup)
    return backup


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--platform-dir", required=True, type=Path)
    backup = prepare_sdk(parser.parse_args().platform_dir)
    if backup is not None:
        print(f"Preserved incomplete SDK at {backup}; Buildozer will reinstall it.")
    else:
        print("SDK ready or absent; bootstrap remains owned by Buildozer.")


if __name__ == "__main__":
    main()

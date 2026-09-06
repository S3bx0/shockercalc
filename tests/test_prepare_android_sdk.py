from pathlib import Path

import pytest

from tools.prepare_android_sdk import prepare_sdk


def test_cold_cache_does_not_create_sdk_directory(tmp_path):
    platform = tmp_path / "platform"
    assert prepare_sdk(platform) is None
    assert not platform.exists()


def test_complete_sdk_is_reused_unchanged(tmp_path):
    sdk = tmp_path / "android-sdk"
    manager = sdk / "tools/bin/sdkmanager"
    manager.parent.mkdir(parents=True)
    manager.write_bytes(b"sdkmanager")
    assert prepare_sdk(tmp_path) is None
    assert manager.read_bytes() == b"sdkmanager"
    assert list(tmp_path.iterdir()) == [sdk]


def test_license_only_sdk_is_preserved_and_bootstrap_is_unblocked(tmp_path):
    sdk = tmp_path / "android-sdk"
    license_file = sdk / "licenses/android-sdk-license"
    license_file.parent.mkdir(parents=True)
    license_file.write_bytes(b"accepted-license")
    old_backup = tmp_path / "android-sdk-incomplete-old"
    old_backup.mkdir()
    other = tmp_path / "android-ndk-r29"
    other.mkdir()

    backup = prepare_sdk(tmp_path)

    assert backup is not None and backup.parent == tmp_path
    assert (backup / "licenses/android-sdk-license").read_bytes() == b"accepted-license"
    assert not sdk.exists()  # Buildozer's actual skip/download condition.
    assert old_backup.is_dir() and other.is_dir()
    assert prepare_sdk(tmp_path) is None  # Idempotent; no new placeholder.


def test_sdk_file_is_rejected_without_moving_it(tmp_path):
    sdk = tmp_path / "android-sdk"
    sdk.write_bytes(b"not-a-directory")
    with pytest.raises(ValueError, match="not a directory"):
        prepare_sdk(tmp_path)
    assert sdk.read_bytes() == b"not-a-directory"


def test_redirected_sdk_is_rejected(tmp_path, monkeypatch):
    sdk = tmp_path / "android-sdk"
    original = Path.is_symlink
    monkeypatch.setattr(Path, "is_symlink", lambda path: path == sdk or original(path))
    with pytest.raises(ValueError, match="redirected"):
        prepare_sdk(tmp_path)


def test_both_android_workflows_delegate_bootstrap_before_build():
    root = Path(__file__).resolve().parents[1]
    assert "android.accept_sdk_license = True" in (root / "buildozer.spec").read_text()
    for name in ("android.yml", "android-release.yml"):
        workflow = (root / ".github/workflows" / name).read_text(encoding="utf-8")
        assert "python tools/prepare_android_sdk.py" in workflow
        assert "android-sdk/licenses" not in workflow
        assert workflow.index("python tools/prepare_android_sdk.py") < workflow.index(
            "| buildozer android"
        )

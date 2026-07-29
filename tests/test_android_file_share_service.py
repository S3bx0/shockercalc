from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JAVA_DIR = ROOT / "android" / "src" / "pl" / "smilczarek" / "refrigerationcalc"
ACTIVITY = JAVA_DIR / "RefrigerationCalcActivity.java"
SERVICE = JAVA_DIR / "FileShareService.java"


def _compact(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").split())


def test_activity_keeps_thin_pyjnius_file_share_delegate():
    activity = _compact(ACTIVITY)

    assert "private FileShareService fileShareService;" in activity
    assert "fileShareService = new FileShareService(this);" in activity
    assert "fileShare().shareFile(path, mimeType, subject, text);" in activity


def test_activity_no_longer_owns_file_share_implementation():
    activity = ACTIVITY.read_text(encoding="utf-8")

    assert "import android.content.Intent" not in activity
    assert "import android.provider.MediaStore" not in activity
    assert "import java.io.File" not in activity
    assert "Intent.ACTION_SEND" not in activity
    assert "exportToDownloads" not in activity
    assert "StrictMode.setVmPolicy" not in activity
    assert len(activity.splitlines()) < 360


def test_file_share_service_preserves_media_store_export_contract():
    service = _compact(SERVICE)

    assert "final class FileShareService" in service
    assert "activity.runOnUiThread(" in service
    assert "if (Build.VERSION.SDK_INT >= 29)" in service
    assert "MediaStore.Downloads.DISPLAY_NAME" in service
    assert "MediaStore.Downloads.MIME_TYPE" in service
    assert "MediaStore.Downloads.RELATIVE_PATH" in service
    assert "Environment.DIRECTORY_DOWNLOADS" in service
    assert "MediaStore.Downloads.IS_PENDING, 1" in service
    assert "resolver.openOutputStream(item)" in service
    assert "new FileInputStream(file)" in service
    assert "MediaStore.Downloads.IS_PENDING, 0" in service
    assert "resolver.update(item, values, null, null)" in service


def test_file_share_service_preserves_sharesheet_and_fallback_contract():
    service = _compact(SERVICE)

    assert 'Log.w(TAG, "shareFile: plik nie istnieje " + path)' in service
    assert "StrictMode.setVmPolicy(" in service
    assert "uri = Uri.fromFile(file);" in service
    assert "new Intent(Intent.ACTION_SEND)" in service
    assert '"application/octet-stream"' in service
    assert "Intent.EXTRA_STREAM" in service
    assert "Intent.EXTRA_SUBJECT" in service
    assert "Intent.EXTRA_TEXT" in service
    assert "Intent.FLAG_GRANT_READ_URI_PERMISSION" in service
    assert "activity.startActivity(Intent.createChooser(intent, subject))" in service

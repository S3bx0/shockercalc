from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JAVA_DIR = ROOT / "android" / "src" / "pl" / "smilczarek" / "refrigerationcalc"
ACTIVITY = JAVA_DIR / "RefrigerationCalcActivity.java"
SERVICE = JAVA_DIR / "FeedbackService.java"


def _compact(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").split())


def test_activity_keeps_thin_feedback_delegate():
    activity = _compact(ACTIVITY)

    assert "private FeedbackService feedbackService;" in activity
    assert "feedbackService = new FeedbackService(this);" in activity
    assert "feedback().openEmail(recipient, subject, body);" in activity


def test_feedback_service_opens_user_controlled_email_draft():
    service = _compact(SERVICE)

    assert "final class FeedbackService" in service
    assert "activity.runOnUiThread(" in service
    assert "new Intent(Intent.ACTION_SENDTO)" in service
    assert '"mailto:" + Uri.encode(safeRecipient)' in service
    assert '"?subject=" + Uri.encode(safeSubject)' in service
    assert '"&body=" + Uri.encode(safeBody)' in service
    assert "activity.startActivity(intent)" in service


def test_feedback_service_has_sharesheet_fallback_without_auto_send():
    service = _compact(SERVICE)

    assert "catch (ActivityNotFoundException noEmailApp)" in service
    assert "new Intent(Intent.ACTION_SEND)" in service
    assert 'fallback.setType("message/rfc822")' in service
    assert "Intent.EXTRA_EMAIL" in service
    assert "Intent.EXTRA_SUBJECT" in service
    assert "Intent.EXTRA_TEXT" in service
    assert "Intent.createChooser(fallback, subject)" in service
    assert "sendBroadcast" not in service
    assert "SmsManager" not in service

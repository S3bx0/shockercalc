from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JAVA_DIR = ROOT / "android" / "src" / "pl" / "smilczarek" / "refrigerationcalc"
ACTIVITY = JAVA_DIR / "RefrigerationCalcActivity.java"
SERVICE = JAVA_DIR / "PrivacyConsentService.java"


def _compact(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").split())


def test_activity_keeps_thin_pyjnius_privacy_delegates():
    activity = _compact(ACTIVITY)

    assert "private PrivacyConsentService privacyConsentService;" in activity
    assert "privacyConsent().requestConsent();" in activity
    assert "return privacyConsent().isPrivacyOptionsRequired();" in activity
    assert "privacyConsent().showPrivacyOptionsForm();" in activity
    assert "this::startMobileAdsSdk" in activity


def test_activity_no_longer_owns_ump_implementation():
    activity = ACTIVITY.read_text(encoding="utf-8")

    assert "import com.google.android.ump" not in activity
    assert "ConsentInformation consentInformation" not in activity
    assert "requestConsentThenInitAds" not in activity
    assert "maybeInitializeAdsAfterConsent" not in activity
    assert len(activity.splitlines()) < 1100


def test_privacy_service_preserves_consent_request_contract():
    service = SERVICE.read_text(encoding="utf-8")

    assert "final class PrivacyConsentService" in service
    assert "ConsentDebugSettings.DebugGeography.DEBUG_GEOGRAPHY_EEA" in service
    assert "requestConsentInfoUpdate(" in service
    assert "loadAndShowConsentFormIfRequired(" in service
    assert "consentInformation.canRequestAds()" in service
    assert "adsInitializer.run();" in service
    assert 'Log.w(TAG, "Consent form error: "' in service
    assert 'Log.w(TAG, "Consent info update failed: "' in service


def test_privacy_service_preserves_options_form_contract():
    service = SERVICE.read_text(encoding="utf-8")

    assert "ConsentInformation.PrivacyOptionsRequirementStatus.REQUIRED" in service
    assert "activity.runOnUiThread(" in service
    assert "UserMessagingPlatform.showPrivacyOptionsForm(" in service
    assert 'Log.w(TAG, "Privacy options error: "' in service

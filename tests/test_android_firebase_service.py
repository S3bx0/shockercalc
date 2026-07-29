from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JAVA_DIR = ROOT / "android" / "src" / "pl" / "smilczarek" / "refrigerationcalc"
ACTIVITY = JAVA_DIR / "RefrigerationCalcActivity.java"
SERVICE = JAVA_DIR / "FirebaseTelemetryService.java"


def _compact(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").split())


def test_activity_keeps_thin_pyjnius_telemetry_delegates():
    activity = _compact(ACTIVITY)

    assert "private FirebaseTelemetryService firebaseTelemetryService;" in activity
    assert "telemetry().initialize();" in activity
    assert "return telemetry().isAvailable();" in activity
    assert "return telemetry().hasPreference();" in activity
    assert "return telemetry().isEnabled();" in activity
    assert "telemetry().setEnabled(enabled);" in activity
    assert "return telemetry().getRemoteConfigBoolean(key, fallback);" in activity
    assert "return telemetry().getRemoteConfigLong(key, fallback);" in activity
    assert "telemetry().logAnalyticsEvent(eventName, parametersJson);" in activity
    assert (
        "telemetry().recordPythonException(context, type, message, stackTrace);"
        in activity
    )


def test_activity_no_longer_owns_firebase_sdk_implementation():
    activity = ACTIVITY.read_text(encoding="utf-8")

    assert "import com.google.firebase" not in activity
    assert "FirebaseAnalytics firebaseAnalytics" not in activity
    assert "FirebaseCrashlytics firebaseCrashlytics" not in activity
    assert "FirebaseRemoteConfig firebaseRemoteConfig" not in activity
    assert "initializeFirebaseTelemetry" not in activity
    assert len(activity.splitlines()) < 1180


def test_firebase_service_preserves_opt_in_and_remote_config_contract():
    service = SERVICE.read_text(encoding="utf-8")

    assert "final class FirebaseTelemetryService" in service
    assert '"firebase_telemetry_preference_set"' in service
    assert '"firebase_telemetry_enabled"' in service
    assert "getBoolean(PREF_TELEMETRY_ENABLED, false)" in service
    assert "setAnalyticsCollectionEnabled(enabled)" in service
    assert "setCrashlyticsCollectionEnabled(enabled)" in service
    assert 'defaults.put("show_beta_features", false)' in service
    assert 'defaults.put("custom_products_limit", 250L)' in service
    assert "setMinimumFetchIntervalInSeconds(debugBuild ? 0 : 43200)" in service
    assert 'setCustomKey("app_runtime", "kivy_python")' in service
    assert 'setCustomKey("android_api", Build.VERSION.SDK_INT)' in service


def test_firebase_service_owns_analytics_and_crash_reporting():
    service = SERVICE.read_text(encoding="utf-8")

    assert "void logAnalyticsEvent(String eventName, String parametersJson)" in service
    assert "new JSONObject(" in service
    assert "firebaseAnalytics.logEvent(eventName, parameters)" in service
    assert "void recordPythonException(String context, String type," in service
    assert 'setCustomKey("python_context", safeContext)' in service
    assert "firebaseCrashlytics.recordException(" in service

package pl.smilczarek.refrigerationcalc;

import android.content.Context;
import android.content.SharedPreferences;
import android.content.pm.ApplicationInfo;
import android.os.Build;
import android.os.Bundle;
import android.util.Log;

import com.google.firebase.FirebaseApp;
import com.google.firebase.analytics.FirebaseAnalytics;
import com.google.firebase.crashlytics.FirebaseCrashlytics;
import com.google.firebase.remoteconfig.FirebaseRemoteConfig;
import com.google.firebase.remoteconfig.FirebaseRemoteConfigSettings;

import org.json.JSONObject;

import java.util.HashMap;
import java.util.Iterator;
import java.util.Map;

/**
 * Owns optional Firebase telemetry and Remote Config integration.
 *
 * <p>The Android activity keeps the public methods used by PyJNIus, while this
 * class contains all SDK state and implementation details. Collection remains
 * opt-in and disabled until the user explicitly makes a choice.</p>
 */
final class FirebaseTelemetryService {
    private static final String TAG = "RefrigerationCalc";
    private static final String PREF_TELEMETRY_SET =
            "firebase_telemetry_preference_set";
    private static final String PREF_TELEMETRY_ENABLED =
            "firebase_telemetry_enabled";

    private final Context context;
    private final SharedPreferences preferences;
    private final boolean debugBuild;

    private FirebaseAnalytics firebaseAnalytics;
    private FirebaseCrashlytics firebaseCrashlytics;
    private FirebaseRemoteConfig firebaseRemoteConfig;
    private boolean available;

    FirebaseTelemetryService(Context context, SharedPreferences preferences) {
        this.context = context;
        this.preferences = preferences;
        this.debugBuild = (context.getApplicationInfo().flags
                & ApplicationInfo.FLAG_DEBUGGABLE) != 0;
    }

    /** Firebase stays optional when a developer build has no configuration. */
    void initialize() {
        try {
            FirebaseApp app;
            if (FirebaseApp.getApps(context).isEmpty()) {
                app = FirebaseApp.initializeApp(context);
            } else {
                app = FirebaseApp.getInstance();
            }
            if (app == null) {
                Log.i(TAG, "Firebase configuration not present; telemetry disabled.");
                return;
            }
            firebaseAnalytics = FirebaseAnalytics.getInstance(context);
            firebaseCrashlytics = FirebaseCrashlytics.getInstance();
            firebaseRemoteConfig = FirebaseRemoteConfig.getInstance();
            available = true;
            applyCollectionPreference(isEnabled());
            if (isEnabled()) {
                applyDiagnosticKeys();
                configureAndFetchRemoteConfig();
            }
        } catch (Exception exc) {
            available = false;
            Log.w(TAG, "Firebase initialization unavailable", exc);
        }
    }

    boolean isAvailable() {
        return available;
    }

    boolean hasPreference() {
        return preferences.contains(PREF_TELEMETRY_SET);
    }

    boolean isEnabled() {
        return preferences.getBoolean(PREF_TELEMETRY_ENABLED, false);
    }

    void setEnabled(boolean enabled) {
        preferences.edit()
                .putBoolean(PREF_TELEMETRY_SET, true)
                .putBoolean(PREF_TELEMETRY_ENABLED, enabled)
                .apply();
        applyCollectionPreference(enabled);
        if (enabled && firebaseCrashlytics != null) {
            applyDiagnosticKeys();
            configureAndFetchRemoteConfig();
        }
    }

    private void applyCollectionPreference(boolean enabled) {
        if (!available) {
            return;
        }
        try {
            firebaseAnalytics.setAnalyticsCollectionEnabled(enabled);
            firebaseCrashlytics.setCrashlyticsCollectionEnabled(enabled);
        } catch (Exception exc) {
            Log.w(TAG, "Unable to apply Firebase telemetry preference", exc);
        }
    }

    private void applyDiagnosticKeys() {
        firebaseCrashlytics.setCustomKey("app_runtime", "kivy_python");
        firebaseCrashlytics.setCustomKey("android_api", Build.VERSION.SDK_INT);
    }

    private void configureAndFetchRemoteConfig() {
        if (!available || !isEnabled() || firebaseRemoteConfig == null) {
            return;
        }
        FirebaseRemoteConfigSettings settings =
                new FirebaseRemoteConfigSettings.Builder()
                        .setMinimumFetchIntervalInSeconds(debugBuild ? 0 : 43200)
                        .build();
        firebaseRemoteConfig.setConfigSettingsAsync(settings);
        Map<String, Object> defaults = new HashMap<>();
        defaults.put("show_beta_features", false);
        defaults.put("custom_products_limit", 250L);
        firebaseRemoteConfig.setDefaultsAsync(defaults);
        firebaseRemoteConfig.fetchAndActivate()
                .addOnFailureListener(exception ->
                        Log.w(TAG, "Remote Config fetch failed", exception));
    }

    boolean getRemoteConfigBoolean(String key, boolean fallback) {
        if (!available || !isEnabled() || firebaseRemoteConfig == null || key == null) {
            return fallback;
        }
        try {
            return firebaseRemoteConfig.getBoolean(key);
        } catch (Exception exc) {
            return fallback;
        }
    }

    long getRemoteConfigLong(String key, long fallback) {
        if (!available || !isEnabled() || firebaseRemoteConfig == null || key == null) {
            return fallback;
        }
        try {
            return firebaseRemoteConfig.getLong(key);
        } catch (Exception exc) {
            return fallback;
        }
    }

    /** Logs only coarse, allow-listed values supplied by the Python UI. */
    void logAnalyticsEvent(String eventName, String parametersJson) {
        if (!available || !isEnabled() || firebaseAnalytics == null || eventName == null) {
            return;
        }
        Bundle parameters = new Bundle();
        try {
            JSONObject source = new JSONObject(
                    parametersJson == null ? "{}" : parametersJson);
            Iterator<String> keys = source.keys();
            while (keys.hasNext()) {
                String key = keys.next();
                Object value = source.opt(key);
                if (value instanceof Boolean) {
                    parameters.putLong(key, ((Boolean) value) ? 1L : 0L);
                } else if (value instanceof Integer || value instanceof Long) {
                    parameters.putLong(key, ((Number) value).longValue());
                } else if (value instanceof Number) {
                    parameters.putDouble(key, ((Number) value).doubleValue());
                } else if (value != null && value != JSONObject.NULL) {
                    parameters.putString(key, String.valueOf(value));
                }
            }
        } catch (Exception exc) {
            Log.w(TAG, "Invalid analytics parameters", exc);
        }
        firebaseAnalytics.logEvent(eventName, parameters);
    }

    /** Converts a Python traceback into a searchable non-fatal Crashlytics event. */
    void recordPythonException(String context, String type,
                               String message, String stackTrace) {
        if (!available || !isEnabled() || firebaseCrashlytics == null) {
            return;
        }
        String safeContext = context == null ? "python" : context;
        String safeType = type == null ? "Exception" : type;
        firebaseCrashlytics.setCustomKey("python_context", safeContext);
        firebaseCrashlytics.setCustomKey("python_exception_type", safeType);
        if (stackTrace != null && !stackTrace.isEmpty()) {
            firebaseCrashlytics.log(stackTrace);
        }
        firebaseCrashlytics.recordException(
                new RuntimeException(
                        "Python " + safeType + " [" + safeContext + "]: "
                                + (message == null ? "" : message)));
    }
}

import json
from pathlib import Path

import p4a_hooks


ROOT = Path(__file__).resolve().parents[1]
ACTIVITY = ROOT / "android/src/pl/smilczarek/refrigerationcalc/RefrigerationCalcActivity.java"


def test_activity_uses_modern_edge_to_edge_api():
    source = ACTIVITY.read_text(encoding="utf-8")

    assert "WindowCompat.enableEdgeToEdge(getWindow())" in source
    assert "setStatusBarColor" not in source
    assert "setNavigationBarColor" not in source
    assert "WindowCompat.setDecorFitsSystemWindows" not in source


def test_firebase_collection_is_opt_in_and_python_errors_are_reported():
    source = ACTIVITY.read_text(encoding="utf-8")

    assert "setAnalyticsCollectionEnabled(enabled)" in source
    assert "setCrashlyticsCollectionEnabled(enabled)" in source
    assert 'getBoolean(PREF_TELEMETRY_ENABLED, false)' in source
    assert "recordPythonException" in source
    assert "custom_products_limit" in source


def test_build_config_supports_rotation_and_current_android_libraries():
    spec = (ROOT / "buildozer.spec").read_text(encoding="utf-8")

    assert "orientation = portrait, landscape, portrait-reverse, landscape-reverse" in spec
    assert "com.google.android.gms:play-services-ads:25.4.0" in spec
    assert "com.android.billingclient:billing:9.1.0" in spec
    assert "com.google.android.ump:user-messaging-platform:4.0.0" in spec
    assert "androidx.core:core:1.18.0" in spec
    assert "com.google.firebase:firebase-analytics:23.2.0" in spec
    assert "com.google.firebase:firebase-crashlytics:20.0.6" in spec
    assert "com.google.firebase:firebase-config:23.1.0" in spec
    assert "firebase_analytics_collection_enabled=false" in spec
    assert "firebase_crashlytics_collection_enabled=false" in spec
    assert "p4a.branch = master" in spec
    assert "p4a.commit = 58d21141f17c889bf8585f5665921d72028f8831" in spec


def test_workflows_pin_reproducible_build_tools():
    for name in ("android.yml", "android-release.yml"):
        workflow = (ROOT / ".github/workflows" / name).read_text(encoding="utf-8")
        assert "buildozer==1.6.0" in workflow
        assert "legacy-cgi==2.6.4" in workflow
        assert "git+https://github.com/kivy/buildozer" not in workflow
        assert "actions/checkout@v4" not in workflow
        assert "actions/cache@v4" not in workflow
        assert "actions/upload-artifact@v4" not in workflow
        assert "FIREBASE_GOOGLE_SERVICES_JSON_BASE64" in workflow
        assert "FIREBASE_GOOGLE_SERVICES_JSON=$GITHUB_WORKSPACE" in workflow

    debug_workflow = (ROOT / ".github/workflows/android.yml").read_text(
        encoding="utf-8"
    )
    assert "firebase-tools@15.22.0" in debug_workflow
    assert "distribute_to_firebase" in debug_workflow


def test_p4a_hook_configures_firebase_only_with_matching_config(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    gradle = project / "build.gradle"
    gradle.write_text(
        """buildscript {
    dependencies {
        classpath 'com.android.tools.build:gradle:8.11.0'
    }
}
apply plugin: 'com.android.application'
android {}
""",
        encoding="utf-8",
    )
    config = tmp_path / "google-services.json"
    config.write_text(
        json.dumps(
            {
                "client": [
                    {
                        "client_info": {
                            "android_client_info": {
                                "package_name": "pl.smilczarek.refrigerationcalc"
                            }
                        }
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    assert p4a_hooks._patch_firebase_gradle(project, config_path=config) == 1
    patched = gradle.read_text(encoding="utf-8")

    assert "com.google.gms:google-services:4.5.0" in patched
    assert "com.google.firebase:firebase-crashlytics-gradle:3.0.7" in patched
    assert "apply plugin: 'com.google.gms.google-services'" in patched
    assert "apply plugin: 'com.google.firebase.crashlytics'" in patched
    assert (project / "google-services.json").exists()


def test_p4a_hook_removes_runtime_orientation_lock(tmp_path):
    source_dir = tmp_path / "src/main/java/org/kivy/android"
    source_dir.mkdir(parents=True)
    activity = source_dir / "PythonActivity.java"
    activity.write_text(
        """import android.content.pm.ActivityInfo;

class PythonActivity {
    void load(Project p) {
        if (p != null) {
            if (p.landscape) {
                setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_LANDSCAPE);
            } else {
                setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_PORTRAIT);
            }
        }
    }
}
""",
        encoding="utf-8",
    )

    p4a_hooks._patch_python_activity_orientation(tmp_path)
    patched = activity.read_text(encoding="utf-8")

    assert "setRequestedOrientation" not in patched
    assert "ActivityInfo" not in patched

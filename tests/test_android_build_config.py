import json
from pathlib import Path

import p4a_hooks


ROOT = Path(__file__).resolve().parents[1]
ACTIVITY = ROOT / "android/src/pl/smilczarek/refrigerationcalc/RefrigerationCalcActivity.java"
SPLASH_VIEW = ROOT / "android/src/pl/smilczarek/refrigerationcalc/RefrigerationSplashView.java"


def test_activity_uses_modern_edge_to_edge_api():
    source = ACTIVITY.read_text(encoding="utf-8")

    assert "Build.VERSION.SDK_INT >= 35" in source
    assert "applyPlatformEdgeToEdgeInsets()" in source
    assert "WindowInsets.Type.systemBars()" in source
    assert "WindowInsets.Type.displayCutout()" in source
    assert "import androidx.core.view.WindowCompat;" not in source
    assert "WindowCompat.enableEdgeToEdge(getWindow())" not in source
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


def test_native_splash_is_lightweight_and_started_by_activity():
    activity = ACTIVITY.read_text(encoding="utf-8")
    splash = SPLASH_VIEW.read_text(encoding="utf-8")

    assert "showAnimatedIntro();" in activity
    assert "removeAnimatedIntro();" in activity
    assert "ANIMATION_DURATION_MS = 4600L" in splash
    assert "drawSnowflake" in splash
    assert "drawRadialSnowflakes" in splash
    assert "drawOrbitComets" in splash
    assert "POLYGON_SIDES = 8" in splash
    assert "RADIAL_PARTICLE_COUNT = 22" in splash
    assert "RADIAL_SPEEDS" in splash
    assert "ORBIT_SPEEDS = {1.93f, 2.21f, 2.49f}" in splash
    assert "255f * reveal" in splash
    assert "ValueAnimator.areAnimatorsEnabled()" in splash
    assert "com.airbnb.lottie" not in splash


def test_launcher_uses_current_icon_as_static_presplash():
    spec = (ROOT / "buildozer.spec").read_text(encoding="utf-8")

    assert "icon.filename = %(source.dir)s/assets/icon.png" in spec
    assert "presplash.filename = %(source.dir)s/assets/presplash.png" in spec
    assert "android.presplash_color = #FFFFFF" in spec
    assert "source.exclude_patterns = assets/brand/**,assets/store/play-icon-512.png" in spec
    assert "source.exclude_dirs = tests, tools," in spec


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


def test_p4a_hook_skips_auxiliary_gradle_templates(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    main_gradle = project / "build.gradle"
    main_gradle.write_text(
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
    auxiliary = project / "src" / "sample" / "build.gradle"
    auxiliary.parent.mkdir(parents=True)
    auxiliary.write_text(
        """apply plugin: 'com.android.application'
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
    assert "com.google.gms.google-services" in main_gradle.read_text(encoding="utf-8")
    assert "com.google.gms.google-services" not in auxiliary.read_text(encoding="utf-8")


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

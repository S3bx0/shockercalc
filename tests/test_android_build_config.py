import gzip
import io
import json
import tarfile
from pathlib import Path

from PIL import Image, ImageChops, ImageStat

import p4a_hooks

ROOT = Path(__file__).resolve().parents[1]
ACTIVITY = ROOT / "android/src/pl/smilczarek/refrigerationcalc/RefrigerationCalcActivity.java"
SPLASH_VIEW = ROOT / "android/src/pl/smilczarek/refrigerationcalc/RefrigerationSplashView.java"


def test_release_version_is_consistent():
    spec = (ROOT / "buildozer.spec").read_text(encoding="utf-8")
    package_init = (ROOT / "tpof/__init__.py").read_text(encoding="utf-8")
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert "version = 1.5.10" in spec
    assert '__version__ = "1.5.10"' in package_init
    assert 'version = "1.5.10"' in pyproject


def test_activity_uses_modern_edge_to_edge_api():
    source = ACTIVITY.read_text(encoding="utf-8")

    assert "Build.VERSION.SDK_INT >= 30" in source
    assert "enablePlatformEdgeToEdge()" in source
    assert "applyPlatformEdgeToEdgeInsets()" in source
    assert "getWindow().setDecorFitsSystemWindows(false)" in source
    assert "LAYOUT_IN_DISPLAY_CUTOUT_MODE_ALWAYS" in source
    assert "LAYOUT_IN_DISPLAY_CUTOUT_MODE_SHORT_EDGES" not in source
    assert "WindowInsets.Type.systemBars()" in source
    assert "WindowInsets.Type.displayCutout()" in source
    assert "WindowInsets.Type.ime()" in source
    assert "APPEARANCE_LIGHT_STATUS_BARS" in source
    assert "APPEARANCE_LIGHT_NAVIGATION_BARS" in source
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


def test_labor_tab_uses_dedicated_admob_units():
    activity = ACTIVITY.read_text(encoding="utf-8")
    mobile_main = (ROOT / "tpof/mobile/main.py").read_text(encoding="utf-8")

    assert "ca-app-pub-7481054652344026/8198860699" in activity
    assert "ca-app-pub-7481054652344026/7623346864" in activity
    assert 'if ("labor".equals(activeAdTab))' in activity
    assert "normalizeAdTab(final String tab)" in activity
    assert 'if ("labor".equals(tab))' in activity
    assert 'self._set_active_ad_tab(name)' in mobile_main
    assert '"labor": self.bottom_labor_tab' in mobile_main


def test_native_splash_is_lightweight_and_started_by_activity():
    activity = ACTIVITY.read_text(encoding="utf-8")
    splash = SPLASH_VIEW.read_text(encoding="utf-8")

    assert "showAnimatedIntro();" in activity
    assert "removeAnimatedIntro();" in activity
    assert "ANIMATION_DURATION_MS = 4900L" in splash
    assert '\"refrigeration_intro\", \"raw\"' in splash
    assert "AnimatedImageDrawable" in splash
    assert "Movie.decodeStream" in splash
    assert "ScaleType.FIT_CENTER" in splash
    assert "setBackgroundColor(Color.WHITE)" in splash
    assert "splashOverlay.setBackgroundColor(Color.WHITE)" in activity
    assert "getWindow().setBackgroundDrawableResource(android.R.color.white)" in activity
    assert "ValueAnimator.areAnimatorsEnabled()" in splash
    assert "com.airbnb.lottie" not in splash
    assert "drawPolygon" not in splash

    intro = ROOT / "android/res/raw/refrigeration_intro.gif"
    assert intro.exists()
    assert intro.read_bytes()[:6] in (b"GIF87a", b"GIF89a")


def test_closed_test_build_expires_and_only_links_to_google_play():
    source = ACTIVITY.read_text(encoding="utf-8")

    assert "TEST_BUILD_EXPIRES_AT_EPOCH_MS = 1784152800000L" in source
    assert "if (isClosedTestBuildExpired())" in source
    assert "showExpiredBuildGate();" in source
    assert "market://details?id=" in source
    assert "https://play.google.com/store/apps/details?id=" in source
    assert "Ta wersja testowa działała do 15 lipca 2026" in source
    assert "public void onBackPressed()" in source


def test_intro_final_frame_matches_approved_emblem():
    intro_path = ROOT / "android/res/raw/refrigeration_intro.gif"
    reference_path = ROOT / "assets/brand/approved-emblem-reference.png"

    with Image.open(intro_path) as animation, Image.open(reference_path) as reference:
        animation.seek(animation.n_frames - 1)
        frame = animation.convert("RGB")
        resized_reference = reference.convert("RGB").resize(
            frame.size, Image.Resampling.LANCZOS
        )
        difference = ImageStat.Stat(ImageChops.difference(frame, resized_reference))

    assert max(difference.mean) < 3.0


def test_launcher_uses_current_icon_as_static_presplash():
    spec = (ROOT / "buildozer.spec").read_text(encoding="utf-8")

    assert "title = Refrig Calc" in spec
    assert "icon.filename = %(source.dir)s/assets/icon.png" in spec
    assert "presplash.filename = %(source.dir)s/assets/presplash.png" in spec
    assert "android.presplash_color = #FFFFFF" in spec
    assert "android.add_resources = %(source.dir)s/android/res" in spec
    assert "source.include_exts = py,png,jpg,jpeg,gif,webp" in spec
    assert "source.include_patterns =\n" in spec
    assert "assets/watermark.png" in spec
    assert "assets/fonts/**" in spec
    assert "assets/icon.png" in spec
    assert "assets/presplash.png" in spec
    assert "android/**" in spec
    assert "tpof/desktop/**" in spec
    assert "source.exclude_dirs = tests, tools," in spec


def test_product_images_are_mobile_sized_and_bounded():
    image_dir = ROOT / "assets" / "images"
    images = sorted(image_dir.glob("*.webp"))

    assert len(images) >= 200
    assert sum(path.stat().st_size for path in images) < 9 * 1024 * 1024
    for path in images:
        with Image.open(path) as image:
            assert image.width <= 512, path.name
            assert image.height <= 512, path.name


def test_build_config_supports_rotation_and_current_android_libraries():
    spec = (ROOT / "buildozer.spec").read_text(encoding="utf-8")
    mobile_main = (ROOT / "tpof/mobile/main.py").read_text(encoding="utf-8")

    assert "orientation = portrait, landscape, portrait-reverse, landscape-reverse" in spec
    assert "android.permissions = INTERNET, ACCESS_NETWORK_STATE" in spec
    assert "WRITE_EXTERNAL_STORAGE" not in spec
    assert "READ_EXTERNAL_STORAGE" not in spec
    assert "/sdcard/Download" not in mobile_main
    assert "/storage/emulated/0/Download" not in mobile_main
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
        assert "tools/android_size_report.py" in workflow

    debug_workflow = (ROOT / ".github/workflows/android.yml").read_text(
        encoding="utf-8"
    )
    assert "firebase-tools@15.22.0" in debug_workflow
    assert "distribute_to_firebase" in debug_workflow


def test_lint_workflow_runs_full_mypy_baseline():
    workflow = (ROOT / ".github/workflows/lint.yml").read_text(encoding="utf-8")

    assert "mypy==2.1.0" in workflow
    assert "python -m mypy\n" in workflow
    assert "python -m mypy ." in workflow


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


def test_p4a_hook_strips_only_fonttools_build_payload(tmp_path):
    bundle = tmp_path / "libpybundle.so"
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w") as archive:
        for name, data in {
            "_python_bundle/site-packages/fontTools/misc/bezierTools.c": b"c" * 100,
            "_python_bundle/site-packages/fontTools/misc/bezierTools.so": b"so" * 100,
            "_python_bundle/site-packages/fontTools/misc/bezierTools.pyc": b"pyc",
            "_python_bundle/site-packages/fpdf/fpdf.pyc": b"fpdf",
        }.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
    bundle.write_bytes(gzip.compress(raw.getvalue(), mtime=0))

    p4a_hooks._strip_python_bundle_payload(tmp_path)

    unpacked = gzip.decompress(bundle.read_bytes())
    with tarfile.open(fileobj=io.BytesIO(unpacked), mode="r:") as archive:
        names = set(archive.getnames())
    assert not any(name.endswith(".c") for name in names)
    assert not any(name.endswith(".so") for name in names)
    assert any(name.endswith("bezierTools.pyc") for name in names)
    assert any(name.endswith("fpdf.pyc") for name in names)

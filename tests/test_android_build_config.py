import gzip
import io
import json
import tarfile
from pathlib import Path

from PIL import Image, ImageChops, ImageStat

import p4a_hooks

ROOT = Path(__file__).resolve().parents[1]
ACTIVITY = ROOT / "android/src/pl/smilczarek/refrigerationcalc/RefrigerationCalcActivity.java"
FIREBASE_SERVICE = (
    ROOT / "android/src/pl/smilczarek/refrigerationcalc/FirebaseTelemetryService.java"
)
ADVERTISING_SERVICE = (
    ROOT / "android/src/pl/smilczarek/refrigerationcalc/AdvertisingService.java"
)
SPLASH_VIEW = ROOT / "android/src/pl/smilczarek/refrigerationcalc/RefrigerationSplashView.java"


def test_release_version_is_consistent():
    spec = (ROOT / "buildozer.spec").read_text(encoding="utf-8")
    package_init = (ROOT / "tpof/__init__.py").read_text(encoding="utf-8")
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert "version = 1.5.13" in spec
    assert '__version__ = "1.5.13"' in package_init
    assert 'version = "1.5.13"' in pyproject


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
    assert "APPEARANCE_LIGHT_STATUS_BARS" in source
    assert "APPEARANCE_LIGHT_NAVIGATION_BARS" in source
    assert "import androidx.core.view.WindowCompat;" not in source
    assert "WindowCompat.enableEdgeToEdge(getWindow())" not in source
    assert "setStatusBarColor" not in source
    assert "setNavigationBarColor" not in source
    assert "WindowCompat.setDecorFitsSystemWindows" not in source


def test_activity_leaves_ime_positioning_to_kivy():
    source = ACTIVITY.read_text(encoding="utf-8")

    assert "WindowInsets.Type.ime()" not in source
    assert "initialBottom + bars.bottom" in source
    assert "Math.max(bars.bottom, ime.bottom)" not in source


def test_firebase_collection_is_opt_in_and_python_errors_are_reported():
    activity = ACTIVITY.read_text(encoding="utf-8")
    service = FIREBASE_SERVICE.read_text(encoding="utf-8")

    assert "setAnalyticsCollectionEnabled(enabled)" in service
    assert "setCrashlyticsCollectionEnabled(enabled)" in service
    assert 'getBoolean(PREF_TELEMETRY_ENABLED, false)' in service
    assert "recordPythonException" in activity
    assert "custom_products_limit" in service


def test_labor_tab_uses_dedicated_admob_units():
    advertising = ADVERTISING_SERVICE.read_text(encoding="utf-8")
    mobile_app = (ROOT / "tpof/mobile/app.py").read_text(encoding="utf-8")

    assert "ca-app-pub-7481054652344026/8198860699" in advertising
    assert "ca-app-pub-7481054652344026/7623346864" in advertising
    assert 'if ("labor".equals(activeAdTab))' in advertising
    assert "normalizeAdTab(final String tab)" in advertising
    assert 'if ("labor".equals(tab))' in advertising
    assert "self._android.set_active_ad_tab(name)" in mobile_app
    assert '"labor": self.bottom_labor_tab' in mobile_app


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


def test_release_has_no_time_limited_test_build_gate():
    source = ACTIVITY.read_text(encoding="utf-8")

    assert "TEST_BUILD_EXPIRES_AT_EPOCH_MS" not in source
    assert "isClosedTestBuildExpired" not in source
    assert "showExpiredBuildGate" not in source
    assert "expiredBuildOverlay" not in source
    assert "Test version expired" not in source


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
    assert "atlas,0-only" in spec
    assert (
        "source.include_patterns = "
        "LICENSE,EULA,AI_USAGE_POLICY,THIRD_PARTY_NOTICES,legal/*"
    ) in spec
    assert "assets/watermark.png" in spec
    assert "assets/fonts/**" in spec
    assert "assets/icon.png" in spec
    assert "assets/presplash.png" in spec
    assert "android/**" in spec
    assert "tpof/desktop/**" in spec
    assert "source.exclude_dirs = tests, tools," in spec
    assert "p4a-recipes" in spec


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
    mobile_app = (ROOT / "tpof/mobile/app.py").read_text(encoding="utf-8")

    assert "orientation = portrait, landscape, portrait-reverse, landscape-reverse" in spec
    assert "android.permissions = INTERNET, ACCESS_NETWORK_STATE" in spec
    assert "android.allow_backup = False" in spec
    assert "WRITE_EXTERNAL_STORAGE" not in spec
    assert "READ_EXTERNAL_STORAGE" not in spec
    assert "/sdcard/Download" not in mobile_app
    assert "/storage/emulated/0/Download" not in mobile_app
    assert "com.google.android.gms:play-services-ads:25.4.0" in spec
    assert "com.android.billingclient:billing:9.1.0" in spec
    assert "com.google.android.ump:user-messaging-platform:4.0.0" in spec
    assert "androidx.core:core:1.18.0" in spec
    assert "com.google.firebase:firebase-analytics:23.2.0" in spec
    assert "com.google.firebase:firebase-crashlytics:20.0.6" in spec
    assert "com.google.firebase:firebase-config:23.1.0" in spec
    assert "com.google.firebase:firebase-installations:19.1.2" in spec
    assert "firebase_data_collection_default_enabled=false" in spec
    assert "firebase_analytics_collection_enabled=false" in spec
    assert "firebase_crashlytics_collection_enabled=false" in spec
    assert "google_analytics_adid_collection_enabled=false" in spec
    assert "p4a.branch = master" in spec
    assert "p4a.commit = 58d21141f17c889bf8585f5665921d72028f8831" in spec
    assert "p4a.local_recipes = ./p4a-recipes" in spec
    assert "pillow==12.3.0" in spec.lower()


def test_local_pillow_recipe_is_pinned_and_cross_compile_safe():
    recipe = (ROOT / "p4a-recipes/pillow/__init__.py").read_text(encoding="utf-8")
    patch = (ROOT / "p4a-recipes/pillow/setup.py.patch").read_text(
        encoding="utf-8"
    )

    assert 'version = "12.3.0"' in recipe
    assert (
        'sha256sum = "3b8182a766685eaa002637e28b4ec8d6b18819a0c71f579bf0dbaa5830297cce"'
        in recipe
    )
    assert 'depends = ["png", "jpeg", "freetype"]' in recipe
    assert 'hostpython_prerequisites = ["setuptools>=77"]' in recipe
    assert 'extra_build_args = ["--config-setting", "platform-guessing=disable"]' in recipe
    assert 'env["PKG_CONFIG"] = "p4a-pkg-config-disabled"' in recipe
    assert 'root = tuple(root_prefix.split(":"))' in patch
    assert 'os.path.join(sys.prefix, "lib")' in patch


def test_workflows_pin_reproducible_build_tools():
    freetype_mirror = (
        "https://downloads.sourceforge.net/project/freetype/freetype2/"
        "{version}/freetype-{version}.tar.gz"
        "#sha256=174d9e53402e1bf9ec7277e22ec199ba3e55a6be2c0740cb18c0ee9850fc8c34"
    )

    for name in ("android.yml", "android-release.yml"):
        workflow = (ROOT / ".github/workflows" / name).read_text(encoding="utf-8")
        assert "buildozer==1.6.0" in workflow
        assert "legacy-cgi==2.6.4" in workflow
        assert f'URL_freetype: "{freetype_mirror}"' in workflow
        assert "git+https://github.com/kivy/buildozer" not in workflow
        assert "actions/checkout@v4" not in workflow
        assert "actions/cache@v4" not in workflow
        assert "uses: actions/cache/restore@27d5ce7f" in workflow
        assert "uses: actions/cache@27d5ce7f" not in workflow
        assert "actions/upload-artifact@v4" not in workflow
        assert "FIREBASE_GOOGLE_SERVICES_JSON_BASE64" in workflow
        assert "FIREBASE_GOOGLE_SERVICES_JSON=$GITHUB_WORKSPACE" in workflow
        assert "tools/android_size_report.py" in workflow
        assert "Cache Buildozer build dir" not in workflow
        assert "Report runner storage after cache restore" in workflow
        assert "Verify packaged Python dependencies" in workflow
        assert "tools/verify_android_python_packages.py" in workflow
        assert "Verify Android backup policy" in workflow
        assert "tools/verify_android_backup_policy.py" in workflow
        assert "*/dists/*/src/main/AndroidManifest.xml" not in workflow
        assert "UPLOAD_EXTRA_ARTIFACTS" in workflow
        assert "Verify final Android permission allowlist" in workflow
        assert "tools/verify_android_permissions.py" in workflow
        assert "Verify Android network security policy" in workflow
        assert "tools/verify_android_network_security.py" in workflow
        assert "Verify Firebase opt-in manifest" in workflow
        assert "tools/verify_android_firebase_manifest.py" in workflow

    debug_workflow = (ROOT / ".github/workflows/android.yml").read_text(
        encoding="utf-8"
    )
    assert "firebase-tools@15.22.0" in debug_workflow
    assert "distribute_to_firebase" in debug_workflow


def test_release_workflow_verifies_offline_legal_bundle():
    workflow = (ROOT / ".github/workflows/android-release.yml").read_text(
        encoding="utf-8"
    )

    assert "Verify packaged legal notices" in workflow
    assert "tools/verify_android_legal_bundle.py" in workflow


def test_release_workflow_has_blocking_aab_integrity_gates():
    workflow = (ROOT / ".github/workflows/android-release.yml").read_text(
        encoding="utf-8"
    )

    assert "Verify AAB signature" in workflow
    assert "jarsigner -verify -verbose -certs" in workflow
    assert 'grep -Fq "jar verified."' in workflow
    assert "Validate AAB with bundletool" in workflow
    assert "bundletool-all-1.18.3.jar" in workflow
    assert "a099cfa1543f55593bc2ed16a70a7c67fe54b1747bb7301f37fdfd6d91028e29" in workflow
    assert 'validate --bundle="$AAB_PATH"' in workflow
    assert "dump manifest" in workflow
    assert 'final-AndroidManifest.xml' in workflow
    assert "Verify native libraries 16 KB alignment" in workflow
    assert "tools/verify_android_16kb_alignment.py" in workflow
    alignment_step = workflow.split(
        "- name: Verify native libraries 16 KB alignment", maxsplit=1
    )[1].split("- name:", maxsplit=1)[0]
    assert "if: always()" not in alignment_step
    assert "::warning::" not in alignment_step

    for step_name in (
        "Upload package size report",
        "Upload sanitized buildozer log (on failure)",
        "Upload 16 KB alignment report",
        "Upload Play Console diagnostic files",
    ):
        step = workflow.split(f"- name: {step_name}", maxsplit=1)[1].split(
            "- name:", maxsplit=1
        )[0]
        assert "env.UPLOAD_EXTRA_ARTIFACTS == 'true'" in step

    aab_upload = workflow.split("- name: Upload AAB artifact", maxsplit=1)[1]
    assert "if: always()" in aab_upload


def test_lint_workflow_runs_full_mypy_baseline():
    workflow = (ROOT / ".github/workflows/lint.yml").read_text(encoding="utf-8")

    requirements = (ROOT / "requirements-dev.txt").read_text(encoding="utf-8")

    assert "mypy==2.3.0" in requirements
    assert "-r requirements.txt -r requirements-dev.txt" in workflow
    assert "python -m pytest" in workflow
    assert "--cov-fail-under=50" in (
        ROOT / "pyproject.toml"
    ).read_text(encoding="utf-8")
    assert "python -m mypy\n" in workflow
    assert "python -m mypy ." in workflow


def test_lint_workflow_audits_dependencies_and_secrets():
    workflow = (ROOT / ".github/workflows/lint.yml").read_text(encoding="utf-8")

    assert "pip-audit==2.10.1" in workflow
    assert "python -m pip_audit" in workflow
    assert "requirements-android-audit.txt" in workflow
    assert '"2026-08-31"' not in workflow
    assert "--ignore-vuln" not in workflow
    assert "gitleaks_8.30.1_linux_x64.tar.gz" in workflow
    assert "551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb" in workflow
    assert "sha256sum --check --strict" in workflow
    assert "./gitleaks git . --redact --no-banner" in workflow
    assert "fetch-depth: 0" in workflow


def test_android_audit_manifest_matches_embedded_security_sensitive_pins():
    manifest = (ROOT / "requirements-android-audit.txt").read_text(encoding="utf-8")
    spec = (ROOT / "buildozer.spec").read_text(encoding="utf-8")

    for requirement in (
        "kivy==2.3.1",
        "kivymd==1.2.0",
        "Pillow==12.3.0",
        "fpdf2==2.8.7",
        "fonttools==4.63.0",
        "defusedxml==0.7.1",
        "certifi==2026.6.17",
    ):
        assert requirement in manifest
        assert requirement.lower() in spec.lower()


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


def test_p4a_hook_filters_packaged_native_dependencies_to_arm64(tmp_path):
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

    assert p4a_hooks._patch_android_abi_filters(project) == 1
    assert p4a_hooks._patch_android_abi_filters(project) == 0
    patched = gradle.read_text(encoding="utf-8")

    assert patched.count("Refrigeration Calc supported ABIs") == 1
    assert "abiFilters.clear()" in patched
    assert "abiFilters 'arm64-v8a'" in patched


def test_p4a_hook_removes_automatic_sdk_providers_from_main_manifest(tmp_path):
    manifest = tmp_path / "project/src/main/AndroidManifest.xml"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        """<manifest xmlns:android="http://schemas.android.com/apk/res/android">
    <application android:label="Refrigeration Calc">
    </application>
</manifest>
""",
        encoding="utf-8",
    )

    assert p4a_hooks._patch_firebase_init_provider(tmp_path) == 1
    assert p4a_hooks._patch_firebase_init_provider(tmp_path) == 0
    patched = manifest.read_text(encoding="utf-8")

    assert patched.count("Refrigeration Calc remove auto-init provider:") == 2
    assert 'xmlns:tools="http://schemas.android.com/tools"' in patched
    assert "com.google.firebase.provider.FirebaseInitProvider" in patched
    assert "com.google.android.gms.ads.MobileAdsInitProvider" in patched
    assert patched.count('tools:node="remove"') == 2


def test_p4a_hook_explicitly_blocks_cleartext_traffic(tmp_path):
    manifest = tmp_path / "project/src/main/AndroidManifest.xml"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        """<manifest xmlns:android="http://schemas.android.com/apk/res/android">
    <application android:usesCleartextTraffic="true" />
</manifest>
""",
        encoding="utf-8",
    )

    assert p4a_hooks._patch_cleartext_policy(tmp_path) == 1
    assert p4a_hooks._patch_cleartext_policy(tmp_path) == 0
    patched = manifest.read_text(encoding="utf-8")

    assert patched.count('android:usesCleartextTraffic="false"') == 1
    assert 'android:usesCleartextTraffic="true"' not in patched


def test_p4a_hook_adds_missing_cleartext_policy(tmp_path):
    manifest = tmp_path / "project/src/main/AndroidManifest.xml"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        """<manifest xmlns:android="http://schemas.android.com/apk/res/android">
    <application android:label="Refrigeration Calc" />
</manifest>
""",
        encoding="utf-8",
    )

    assert p4a_hooks._patch_cleartext_policy(tmp_path) == 1
    assert p4a_hooks._patch_cleartext_policy(tmp_path) == 0

    assert 'android:usesCleartextTraffic="false"' in manifest.read_text(
        encoding="utf-8"
    )


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

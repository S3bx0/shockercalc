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


def test_build_config_supports_rotation_and_current_android_libraries():
    spec = (ROOT / "buildozer.spec").read_text(encoding="utf-8")

    assert "orientation = portrait, landscape, portrait-reverse, landscape-reverse" in spec
    assert "com.google.android.gms:play-services-ads:25.4.0" in spec
    assert "com.android.billingclient:billing:9.1.0" in spec
    assert "com.google.android.ump:user-messaging-platform:4.0.0" in spec
    assert "androidx.core:core:1.18.0" in spec
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

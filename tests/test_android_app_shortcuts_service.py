from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JAVA_DIR = ROOT / "android/src/pl/smilczarek/refrigerationcalc"
ACTIVITY = JAVA_DIR / "RefrigerationCalcActivity.java"
SERVICE = JAVA_DIR / "AppShortcutsService.java"


def test_activity_delegates_shortcut_lifecycle_to_separate_service():
    activity = ACTIVITY.read_text(encoding="utf-8")

    assert "private AppShortcutsService appShortcutsService;" in activity
    assert "appShortcuts().initialize(getIntent());" in activity
    assert "protected void onNewIntent(Intent intent)" in activity
    assert "appShortcuts().onNewIntent(intent);" in activity
    assert "public String consumePendingShortcutTab()" in activity
    assert "return appShortcuts().consumePendingTargetTab();" in activity
    assert "ShortcutManager" not in activity
    assert "ShortcutInfo" not in activity


def test_shortcut_service_registers_three_localized_tab_destinations():
    service = SERVICE.read_text(encoding="utf-8")

    assert "final class AppShortcutsService" in service
    assert "Build.VERSION.SDK_INT >= Build.VERSION_CODES.N_MR1" in service
    assert "manager.setDynamicShortcuts(" in service
    assert "manager.getMaxShortcutCountPerActivity()" in service
    assert 'TAB_FREEZING = "freezing"' in service
    assert 'TAB_VALVES = "valves"' in service
    assert 'TAB_LABOR = "labor"' in service
    assert '"Chłodnicze"' in service
    assert '"Zawory"' in service
    assert '"Robocizna"' in service
    assert "Intent.FLAG_ACTIVITY_CLEAR_TOP" in service
    assert "Intent.FLAG_ACTIVITY_SINGLE_TOP" in service


def test_shortcut_service_validates_and_consumes_pending_target_once():
    service = SERVICE.read_text(encoding="utf-8")

    assert "isSupportedTab(target)" in service
    assert "synchronized String consumePendingTargetTab()" in service
    assert 'pendingTargetTab = "";' in service
    assert 'manager.reportShortcutUsed("open_" + tab);' in service

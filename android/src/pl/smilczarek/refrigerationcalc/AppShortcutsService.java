package pl.smilczarek.refrigerationcalc;

import android.annotation.TargetApi;
import android.app.Activity;
import android.content.Intent;
import android.content.pm.ShortcutInfo;
import android.content.pm.ShortcutManager;
import android.net.Uri;
import android.os.Build;
import android.os.UserManager;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

/** Rejestruje skróty launchera i przekazuje wybraną kartę do warstwy Python. */
final class AppShortcutsService {
    static final String EXTRA_TARGET_TAB =
            "pl.smilczarek.refrigerationcalc.extra.TARGET_TAB";

    private static final String TAB_FREEZING = "freezing";
    private static final String TAB_VALVES = "valves";
    private static final String TAB_LABOR = "labor";

    private final Activity activity;
    private String pendingTargetTab = "";

    AppShortcutsService(Activity activity) {
        this.activity = activity;
    }

    void initialize(Intent launchIntent) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N_MR1) {
            try {
                Api25Impl.registerDynamicShortcuts(activity);
            } catch (RuntimeException ignored) {
                // Skróty są opcjonalne i nie mogą zablokować startu aplikacji.
            }
        }
        captureIntent(launchIntent);
    }

    void onNewIntent(Intent intent) {
        captureIntent(intent);
    }

    synchronized String consumePendingTargetTab() {
        String target = pendingTargetTab;
        pendingTargetTab = "";
        return target;
    }

    private synchronized void captureIntent(Intent intent) {
        if (intent == null) {
            return;
        }
        String target = intent.getStringExtra(EXTRA_TARGET_TAB);
        if (!isSupportedTab(target)) {
            Uri data = intent.getData();
            target = data == null ? null : data.getLastPathSegment();
        }
        if (!isSupportedTab(target)) {
            return;
        }
        pendingTargetTab = target;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N_MR1) {
            Api25Impl.reportShortcutUsed(activity, target);
        }
    }

    private static boolean isSupportedTab(String tab) {
        return TAB_FREEZING.equals(tab)
                || TAB_VALVES.equals(tab)
                || TAB_LABOR.equals(tab);
    }

    /** Trzyma odwołania do klas dodanych w API 25 poza ścieżką ładowania API 24. */
    @TargetApi(Build.VERSION_CODES.N_MR1)
    private static final class Api25Impl {
        private Api25Impl() {
        }

        static void registerDynamicShortcuts(Activity activity) {
            ShortcutManager manager = activity.getSystemService(ShortcutManager.class);
            UserManager userManager = activity.getSystemService(UserManager.class);
            if (manager == null || userManager == null || !userManager.isUserUnlocked()) {
                return;
            }

            boolean polish = "pl".equals(Locale.getDefault().getLanguage());
            List<ShortcutInfo> shortcuts = new ArrayList<>();
            shortcuts.add(buildShortcut(
                    activity,
                    "open_freezing",
                    TAB_FREEZING,
                    polish ? "Chłodnicze" : "Cooling",
                    polish ? "Otwórz obliczenia chłodnicze" : "Open cooling calculations",
                    0));
            shortcuts.add(buildShortcut(
                    activity,
                    "open_valves",
                    TAB_VALVES,
                    polish ? "Zawory" : "Valves",
                    polish ? "Otwórz dobór zaworów" : "Open valve selection",
                    1));
            shortcuts.add(buildShortcut(
                    activity,
                    "open_labor",
                    TAB_LABOR,
                    polish ? "Robocizna" : "Labor",
                    polish ? "Otwórz kalkulator robocizny" : "Open labor calculator",
                    2));

            int limit = Math.min(
                    shortcuts.size(),
                    manager.getMaxShortcutCountPerActivity());
            if (limit > 0) {
                manager.setDynamicShortcuts(
                        new ArrayList<>(shortcuts.subList(0, limit)));
            }
        }

        private static ShortcutInfo buildShortcut(Activity activity, String id,
                                                  String tab, String shortLabel,
                                                  String longLabel, int rank) {
            Intent intent = new Intent(activity, RefrigerationCalcActivity.class);
            intent.setAction(Intent.ACTION_VIEW);
            intent.setData(Uri.parse("refrigerationcalc://open/" + tab));
            intent.putExtra(EXTRA_TARGET_TAB, tab);
            intent.addFlags(
                    Intent.FLAG_ACTIVITY_CLEAR_TOP | Intent.FLAG_ACTIVITY_SINGLE_TOP);
            return new ShortcutInfo.Builder(activity, id)
                    .setShortLabel(shortLabel)
                    .setLongLabel(longLabel)
                    .setRank(rank)
                    .setIntent(intent)
                    .build();
        }

        static void reportShortcutUsed(Activity activity, String tab) {
            ShortcutManager manager = activity.getSystemService(ShortcutManager.class);
            UserManager userManager = activity.getSystemService(UserManager.class);
            if (manager == null || userManager == null || !userManager.isUserUnlocked()) {
                return;
            }
            try {
                manager.reportShortcutUsed("open_" + tab);
            } catch (RuntimeException ignored) {
                // Niektóre launchery nie implementują pełnego API skrótów.
            }
        }
    }
}

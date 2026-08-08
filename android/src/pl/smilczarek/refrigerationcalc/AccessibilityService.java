package pl.smilczarek.refrigerationcalc;

import android.app.Activity;
import android.content.Context;
import android.os.Build;
import android.view.View;
import android.view.accessibility.AccessibilityManager;

/** Bridges the single Kivy surface to Android accessibility services. */
final class AccessibilityService {
    private final Activity activity;

    AccessibilityService(Activity activity) {
        this.activity = activity;
    }

    void configureRoot(final String description) {
        final String safeDescription = description == null ? "" : description.trim();
        activity.runOnUiThread(() -> {
            final View root = accessibilityRoot();
            if (root == null) {
                return;
            }
            root.setImportantForAccessibility(View.IMPORTANT_FOR_ACCESSIBILITY_YES);
            root.setFocusable(true);
            root.setContentDescription(safeDescription);
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.KITKAT) {
                root.setAccessibilityLiveRegion(View.ACCESSIBILITY_LIVE_REGION_POLITE);
            }
        });
    }

    void announce(final String message) {
        final String safeMessage = message == null ? "" : message.trim();
        if (safeMessage.isEmpty()) {
            return;
        }
        activity.runOnUiThread(() -> {
            final AccessibilityManager manager = (AccessibilityManager) activity
                    .getSystemService(Context.ACCESSIBILITY_SERVICE);
            final View root = accessibilityRoot();
            if (root == null || manager == null || !manager.isEnabled()) {
                return;
            }
            root.announceForAccessibility(safeMessage);
        });
    }

    private View accessibilityRoot() {
        View root = activity.findViewById(android.R.id.content);
        if (root == null) {
            root = activity.getWindow().getDecorView();
        }
        return root;
    }
}

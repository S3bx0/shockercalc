package pl.smilczarek.refrigerationcalc;

import android.content.pm.ApplicationInfo;
import android.graphics.Color;
import android.graphics.Insets;
import android.os.Build;
import android.os.Bundle;
import android.view.View;
import android.view.ViewGroup;
import android.view.ViewParent;
import android.view.WindowInsets;
import android.view.WindowInsetsController;
import android.view.WindowManager;
import android.widget.FrameLayout;

import org.kivy.android.PythonActivity;

public class RefrigerationCalcActivity extends PythonActivity {
    private static final String PREFS_NAME = "shockercalc_billing";

    private BillingService billingService;
    private FirebaseTelemetryService firebaseTelemetryService;
    private PrivacyConsentService privacyConsentService;
    private AdvertisingService advertisingService;
    private FileShareService fileShareService;
    private FrameLayout splashOverlay;
    private RefrigerationSplashView splashView;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        getWindow().setBackgroundDrawableResource(android.R.color.white);
        super.onCreate(savedInstanceState);
        configureEdgeToEdge();
        showAnimatedIntro();
        telemetry().initialize();
        billing().initialize();
        initializeAds();
    }

    private void showAnimatedIntro() {
        final View decor = getWindow().getDecorView();
        if (!(decor instanceof ViewGroup)) {
            return;
        }

        splashOverlay = new FrameLayout(this);
        splashOverlay.setBackgroundColor(Color.WHITE);
        splashOverlay.setClickable(true);
        splashOverlay.setFocusable(true);
        splashOverlay.setImportantForAccessibility(
                View.IMPORTANT_FOR_ACCESSIBILITY_NO_HIDE_DESCENDANTS);
        splashView = new RefrigerationSplashView(this);
        splashOverlay.addView(
                splashView,
                new FrameLayout.LayoutParams(
                        ViewGroup.LayoutParams.MATCH_PARENT,
                        ViewGroup.LayoutParams.MATCH_PARENT));
        ((ViewGroup) decor).addView(
                splashOverlay,
                new ViewGroup.LayoutParams(
                        ViewGroup.LayoutParams.MATCH_PARENT,
                        ViewGroup.LayoutParams.MATCH_PARENT));
        splashOverlay.bringToFront();
        final RefrigerationSplashView introView = splashView;
        splashOverlay.post(() -> {
            if (splashView == introView) {
                introView.start(this::fadeOutAnimatedIntro);
            }
        });
    }

    private void fadeOutAnimatedIntro() {
        final FrameLayout overlay = splashOverlay;
        if (overlay == null) {
            return;
        }
        overlay.animate()
                .alpha(0f)
                .setDuration(240L)
                .withEndAction(this::removeAnimatedIntro)
                .start();
    }

    private void removeAnimatedIntro() {
        if (splashView != null) {
            splashView.stop();
            splashView = null;
        }
        if (splashOverlay != null) {
            ViewParent parent = splashOverlay.getParent();
            if (parent instanceof ViewGroup) {
                ((ViewGroup) parent).removeView(splashOverlay);
            }
            splashOverlay = null;
        }
    }

    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }

    private FirebaseTelemetryService telemetry() {
        if (firebaseTelemetryService == null) {
            firebaseTelemetryService = new FirebaseTelemetryService(
                    this,
                    getSharedPreferences(PREFS_NAME, MODE_PRIVATE));
        }
        return firebaseTelemetryService;
    }

    private PrivacyConsentService privacyConsent() {
        if (privacyConsentService == null) {
            privacyConsentService = new PrivacyConsentService(
                    this,
                    isDebugBuild(),
                    () -> advertising().startMobileAdsSdk());
        }
        return privacyConsentService;
    }

    private AdvertisingService advertising() {
        if (advertisingService == null) {
            advertisingService = new AdvertisingService(
                    this,
                    getSharedPreferences(PREFS_NAME, MODE_PRIVATE),
                    isDebugBuild(),
                    this::isProNoAdsActive);
        }
        return advertisingService;
    }

    private BillingService billing() {
        if (billingService == null) {
            billingService = new BillingService(
                    this,
                    getSharedPreferences(PREFS_NAME, MODE_PRIVATE),
                    () -> {
                        advertising().updateForProStatus();
                    });
        }
        return billingService;
    }

    private FileShareService fileShare() {
        if (fileShareService == null) {
            fileShareService = new FileShareService(this);
        }
        return fileShareService;
    }

    public boolean isFirebaseTelemetryAvailable() {
        return telemetry().isAvailable();
    }

    public boolean hasTelemetryPreference() {
        return telemetry().hasPreference();
    }

    public boolean isTelemetryEnabled() {
        return telemetry().isEnabled();
    }

    public void setTelemetryEnabled(boolean enabled) {
        telemetry().setEnabled(enabled);
    }

    public boolean getRemoteConfigBoolean(String key, boolean fallback) {
        return telemetry().getRemoteConfigBoolean(key, fallback);
    }

    public long getRemoteConfigLong(String key, long fallback) {
        return telemetry().getRemoteConfigLong(key, fallback);
    }

    public void logAnalyticsEvent(String eventName, String parametersJson) {
        telemetry().logAnalyticsEvent(eventName, parametersJson);
    }

    public void recordPythonException(String context, String type,
                                      String message, String stackTrace) {
        telemetry().recordPythonException(context, type, message, stackTrace);
    }

    /** Jawnie wlacza edge-to-edge na platformach, ktore maja natywne API okna. */
    private void configureEdgeToEdge() {
        if (Build.VERSION.SDK_INT >= 30) {
            enablePlatformEdgeToEdge();
            applyPlatformEdgeToEdgeInsets();
        }
    }

    /**
     * Uzywamy bezposrednio aktualnego API platformy. AndroidX EdgeToEdge nadal
     * zawiera SHORT_EDGES dla starszych wersji systemu, co Play Console zglasza
     * jako wycofany parametr nawet wtedy, gdy Android 15 go nie wykonuje.
     */
    @android.annotation.TargetApi(30)
    private void enablePlatformEdgeToEdge() {
        getWindow().setDecorFitsSystemWindows(false);
        WindowInsetsController controller = getWindow().getInsetsController();
        if (controller != null) {
            // Tło pasków systemowych jest jasne po stronie systemu, więc ikony
            // muszą być ciemne również w trybie edge-to-edge Androida 15+.
            controller.setSystemBarsAppearance(
                    WindowInsetsController.APPEARANCE_LIGHT_STATUS_BARS
                            | WindowInsetsController.APPEARANCE_LIGHT_NAVIGATION_BARS,
                    WindowInsetsController.APPEARANCE_LIGHT_STATUS_BARS
                            | WindowInsetsController.APPEARANCE_LIGHT_NAVIGATION_BARS);
        }
        WindowManager.LayoutParams attributes = getWindow().getAttributes();
        if (attributes.layoutInDisplayCutoutMode
                != WindowManager.LayoutParams.LAYOUT_IN_DISPLAY_CUTOUT_MODE_ALWAYS) {
            attributes.layoutInDisplayCutoutMode =
                    WindowManager.LayoutParams.LAYOUT_IN_DISPLAY_CUTOUT_MODE_ALWAYS;
            getWindow().setAttributes(attributes);
        }
    }

    @android.annotation.TargetApi(30)
    private void applyPlatformEdgeToEdgeInsets() {
        View root = findViewById(android.R.id.content);
        if (root == null) {
            root = getWindow().getDecorView();
        }
        final int initialLeft = root.getPaddingLeft();
        final int initialTop = root.getPaddingTop();
        final int initialRight = root.getPaddingRight();
        final int initialBottom = root.getPaddingBottom();

        root.setOnApplyWindowInsetsListener(
                (view, windowInsets) -> {
                    Insets bars = windowInsets.getInsets(
                            WindowInsets.Type.systemBars()
                                    | WindowInsets.Type.displayCutout()
                    );
                    Insets ime = windowInsets.getInsets(WindowInsets.Type.ime());
                    int bottomInset = Math.max(bars.bottom, ime.bottom);
                    view.setPadding(
                            initialLeft + bars.left,
                            initialTop + bars.top,
                            initialRight + bars.right,
                            initialBottom + bottomInset
                    );
                    return windowInsets;
                }
        );
        root.requestApplyInsets();
    }

    private void initializeAds() {
        if (isProNoAdsActive()) {
            return;
        }
        privacyConsent().requestConsent();
    }

    /** True, gdy dostępny jest formularz opcji prywatności (zmiana zgody). */
    public boolean isPrivacyOptionsRequired() {
        return privacyConsent().isPrivacyOptionsRequired();
    }

    /** Ponownie otwiera formularz zgody (wywoływane z menu Prywatność). */
    public void showPrivacyOptionsForm() {
        privacyConsent().showPrivacyOptionsForm();
    }

    public void setActiveAdTab(final String tab) {
        advertising().setActiveAdTab(tab);
    }

    public boolean isRewardedAdReady() {
        return advertising().isRewardedAdReady();
    }

    public void showRewardedAd() {
        advertising().showRewardedAd();
    }

    public int consumePendingRewardTokens() {
        return advertising().consumePendingRewardTokens();
    }

    public void shareFile(final String path, final String mimeType,
                          final String subject, final String text) {
        fileShare().shareFile(path, mimeType, subject, text);
    }

    private boolean isDebugBuild() {
        return (getApplicationInfo().flags & ApplicationInfo.FLAG_DEBUGGABLE) != 0;
    }

    public int getBannerHeightDp() {
        return advertising().getBannerHeightDp();
    }

    public boolean isProNoAdsActive() {
        return billing().isProNoAdsActive();
    }

    public String getProFormattedPrice() {
        return billing().getProFormattedPrice();
    }

    public void launchProPurchase() {
        billing().launchProPurchase();
    }

    /** Czy moduł doboru zaworów został kupiony (jednorazowy produkt INAPP). */
    public boolean isModuleValvesOwned() {
        return billing().isModuleValvesOwned();
    }

    /** Uruchamia zakup modułu zaworów (jednorazowy produkt ``module_valves``). */
    public void launchModulePurchase() {
        billing().launchModulePurchase();
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (advertisingService != null) {
            advertisingService.onResume();
        }
        billing().onResume();
    }

    @Override
    protected void onPause() {
        if (advertisingService != null) {
            advertisingService.onPause();
        }
        super.onPause();
    }

    @Override
    protected void onDestroy() {
        removeAnimatedIntro();
        if (advertisingService != null) {
            advertisingService.onDestroy();
        }
        if (billingService != null) {
            billingService.onDestroy();
        }
        super.onDestroy();
    }
}

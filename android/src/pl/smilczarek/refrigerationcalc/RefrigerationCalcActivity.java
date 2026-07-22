package pl.smilczarek.refrigerationcalc;

import android.content.Intent;
import android.content.ContentResolver;
import android.content.ContentValues;
import android.content.SharedPreferences;
import android.content.pm.ApplicationInfo;
import android.graphics.Color;
import android.graphics.Insets;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Environment;
import android.os.StrictMode;
import android.provider.MediaStore;
import android.util.DisplayMetrics;
import android.util.Log;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.view.ViewParent;
import android.view.WindowInsets;
import android.view.WindowInsetsController;
import android.view.WindowManager;
import android.widget.FrameLayout;

import com.android.billingclient.api.AcknowledgePurchaseParams;
import com.android.billingclient.api.AcknowledgePurchaseResponseListener;
import com.android.billingclient.api.BillingClient;
import com.android.billingclient.api.BillingClientStateListener;
import com.android.billingclient.api.BillingFlowParams;
import com.android.billingclient.api.BillingResult;
import com.android.billingclient.api.PendingPurchasesParams;
import com.android.billingclient.api.ProductDetails;
import com.android.billingclient.api.ProductDetailsResponseListener;
import com.android.billingclient.api.Purchase;
import com.android.billingclient.api.PurchasesResponseListener;
import com.android.billingclient.api.PurchasesUpdatedListener;
import com.android.billingclient.api.QueryProductDetailsParams;
import com.android.billingclient.api.QueryProductDetailsResult;
import com.android.billingclient.api.QueryPurchasesParams;
import com.google.android.gms.ads.AdRequest;
import com.google.android.gms.ads.AdSize;
import com.google.android.gms.ads.AdView;
import com.google.android.gms.ads.FullScreenContentCallback;
import com.google.android.gms.ads.LoadAdError;
import com.google.android.gms.ads.MobileAds;
import com.google.android.gms.ads.OnUserEarnedRewardListener;
import com.google.android.gms.ads.initialization.InitializationStatus;
import com.google.android.gms.ads.initialization.OnInitializationCompleteListener;
import com.google.android.gms.ads.rewarded.RewardItem;
import com.google.android.gms.ads.rewarded.RewardedAd;
import com.google.android.gms.ads.rewarded.RewardedAdLoadCallback;
import org.kivy.android.PythonActivity;

import java.io.File;
import java.io.FileInputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.util.Collections;
import java.util.List;

public class RefrigerationCalcActivity extends PythonActivity implements PurchasesUpdatedListener {
    private static final String TAG = "RefrigerationCalc";
    private static final String LIVE_BANNER_AD_UNIT_ID =
            "ca-app-pub-7481054652344026/5599859341";
    private static final String LIVE_BANNER_VALVES_AD_UNIT_ID =
            "ca-app-pub-7481054652344026/6303778370";
    private static final String LIVE_BANNER_LABOR_AD_UNIT_ID =
            "ca-app-pub-7481054652344026/8198860699";
    private static final String TEST_BANNER_AD_UNIT_ID =
            "ca-app-pub-3940256099942544/9214589741";
    private static final String LIVE_REWARDED_AD_UNIT_ID =
            "ca-app-pub-7481054652344026/1548239161";
    private static final String LIVE_REWARDED_VALVES_AD_UNIT_ID =
            "ca-app-pub-7481054652344026/1060900411";
    private static final String LIVE_REWARDED_LABOR_AD_UNIT_ID =
            "ca-app-pub-7481054652344026/7623346864";
    private static final String TEST_REWARDED_AD_UNIT_ID =
            "ca-app-pub-3940256099942544/5224354917";
    private static final String LEGACY_PRO_PRODUCT_ID = "pro_no_ads";
    private static final String PRO_SUBSCRIPTION_ID = "refrigeration_pro";
    private static final String PRO_BASE_PLAN_ID = "monthly-499";
    private static final String MODULE_VALVES_PRODUCT_ID = "module_valves";
    private static final String PREFS_NAME = "shockercalc_billing";
    private static final String PREF_PRO_NO_ADS = "pro_no_ads";
    private static final String PREF_PRO_SUBSCRIPTION = "refrigeration_pro";
    private static final String PREF_MODULE_VALVES = "module_valves";
    private static final String PREF_PENDING_REWARD_TOKENS = "pending_reward_tokens";

    private AdView bannerAdView;
    private FrameLayout bannerContainer;
    private RewardedAd rewardedAd;
    private boolean rewardedLoading;
    private boolean adsInitialized;
    // Aktywna zakładka UI ("freezing" / "valves") — wybiera jednostkę reklamową.
    private volatile String activeAdTab = "freezing";
    private BillingClient billingClient;
    private ProductDetails proSubscriptionDetails;
    private ProductDetails moduleValvesProductDetails;
    private boolean billingConnecting;
    private boolean pendingProPurchaseLaunch;
    private boolean pendingModuleValvesLaunch;
    private FirebaseTelemetryService firebaseTelemetryService;
    private PrivacyConsentService privacyConsentService;
    private FrameLayout splashOverlay;
    private RefrigerationSplashView splashView;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        getWindow().setBackgroundDrawableResource(android.R.color.white);
        super.onCreate(savedInstanceState);
        configureEdgeToEdge();
        showAnimatedIntro();
        telemetry().initialize();
        initializeBilling();
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
                    this::startMobileAdsSdk);
        }
        return privacyConsentService;
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

    private void startMobileAdsSdk() {
        if (adsInitialized || isProNoAdsActive()) {
            return;
        }
        new Thread(new Runnable() {
            @Override
            public void run() {
                MobileAds.initialize(
                        RefrigerationCalcActivity.this,
                        new OnInitializationCompleteListener() {
                            @Override
                            public void onInitializationComplete(
                                    InitializationStatus initializationStatus) {
                                runOnUiThread(new Runnable() {
                                    @Override
                                    public void run() {
                                        adsInitialized = true;
                                        attachBanner();
                                        loadRewardedAd();
                                    }
                                });
                            }
                        });
            }
        }).start();
    }

    private void attachBanner() {
        if (isProNoAdsActive() || bannerAdView != null) {
            return;
        }

        ViewGroup root = findViewById(android.R.id.content);
        if (root == null) {
            Log.w(TAG, "Cannot attach banner: root content view is null.");
            return;
        }

        bannerContainer = new FrameLayout(this);
        FrameLayout.LayoutParams containerParams = new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT
        );
        containerParams.gravity = Gravity.BOTTOM | Gravity.CENTER_HORIZONTAL;

        bannerAdView = new AdView(this);
        bannerAdView.setAdUnitId(getBannerAdUnitId());
        bannerAdView.setAdSize(getAdSize());

        bannerContainer.addView(bannerAdView);
        root.addView(bannerContainer, containerParams);

        bannerAdView.loadAd(new AdRequest.Builder().build());
        Log.i(TAG, "AdMob banner requested. Debug test ads: " + isDebugBuild());
    }

    private void hideBanner() {
        if (bannerAdView != null) {
            bannerAdView.destroy();
            bannerAdView = null;
        }
        if (bannerContainer != null) {
            ViewGroup parent = (ViewGroup) bannerContainer.getParent();
            if (parent != null) {
                parent.removeView(bannerContainer);
            }
            bannerContainer = null;
        }
    }

    private String getBannerAdUnitId() {
        if (isDebugBuild()) {
            return TEST_BANNER_AD_UNIT_ID;
        }
        if ("valves".equals(activeAdTab)) {
            return LIVE_BANNER_VALVES_AD_UNIT_ID;
        }
        if ("labor".equals(activeAdTab)) {
            return LIVE_BANNER_LABOR_AD_UNIT_ID;
        }
        return LIVE_BANNER_AD_UNIT_ID;
    }

    private String getRewardedAdUnitId() {
        if (isDebugBuild()) {
            return TEST_REWARDED_AD_UNIT_ID;
        }
        if ("valves".equals(activeAdTab)) {
            return LIVE_REWARDED_VALVES_AD_UNIT_ID;
        }
        if ("labor".equals(activeAdTab)) {
            return LIVE_REWARDED_LABOR_AD_UNIT_ID;
        }
        return LIVE_REWARDED_AD_UNIT_ID;
    }

    private String normalizeAdTab(final String tab) {
        if ("valves".equals(tab)) {
            return "valves";
        }
        if ("labor".equals(tab)) {
            return "labor";
        }
        return "freezing";
    }

    /**
     * Ustawia aktywną zakładkę UI ("freezing" / "valves" / "labor") z warstwy Pythona.
     * Gdy zakładka się zmienia, przeładowuje baner oraz reklamę rewarded na
     * jednostkę przypisaną do danej zakładki. Wywoływane przy przełączaniu
     * dolnej nawigacji — reklamy są inicjowane akcją użytkownika, więc nie
     * narusza zasad AdMob (brak auto-odświeżania programowego).
     */
    public void setActiveAdTab(final String tab) {
        final String normalized = normalizeAdTab(tab);
        if (normalized.equals(activeAdTab)) {
            return;
        }
        activeAdTab = normalized;
        if (isProNoAdsActive()) {
            return;
        }
        runOnUiThread(new Runnable() {
            @Override
            public void run() {
                // Przeładuj baner na jednostkę aktywnej zakładki.
                if (bannerAdView != null || bannerContainer != null) {
                    hideBanner();
                    attachBanner();
                }
                // Przeładuj rewarded na jednostkę aktywnej zakładki.
                if (rewardedAd != null) {
                    rewardedAd = null;
                }
                loadRewardedAd();
            }
        });
    }

    /** Preloads a rewarded ad so it is ready to show on demand. */
    private void loadRewardedAd() {
        if (isProNoAdsActive() || rewardedAd != null || rewardedLoading) {
            return;
        }
        rewardedLoading = true;
        RewardedAd.load(
                this,
                getRewardedAdUnitId(),
                new AdRequest.Builder().build(),
                new RewardedAdLoadCallback() {
                    @Override
                    public void onAdLoaded(RewardedAd ad) {
                        rewardedLoading = false;
                        rewardedAd = ad;
                        Log.i(TAG, "Rewarded ad loaded. Debug test ads: " + isDebugBuild());
                    }

                    @Override
                    public void onAdFailedToLoad(LoadAdError error) {
                        rewardedLoading = false;
                        rewardedAd = null;
                        Log.w(TAG, "Rewarded ad failed to load: " + error.getMessage());
                    }
                });
    }

    /** Returns true when a rewarded ad is loaded and ready to show. */
    public boolean isRewardedAdReady() {
        return rewardedAd != null;
    }

    /**
     * Shows the preloaded rewarded ad. On a completed view the user earns one
     * reward token, persisted to SharedPreferences for the Python layer to
     * consume via {@link #consumePendingRewardTokens()}. Daily caps / cooldowns
     * are enforced on the Python entitlements side before this is called.
     */
    public void showRewardedAd() {
        runOnUiThread(new Runnable() {
            @Override
            public void run() {
                if (rewardedAd == null) {
                    Log.w(TAG, "Rewarded ad requested but not ready.");
                    loadRewardedAd();
                    return;
                }
                final RewardedAd ad = rewardedAd;
                rewardedAd = null;
                ad.setFullScreenContentCallback(new FullScreenContentCallback() {
                    @Override
                    public void onAdDismissedFullScreenContent() {
                        loadRewardedAd();
                    }

                    @Override
                    public void onAdFailedToShowFullScreenContent(
                            com.google.android.gms.ads.AdError adError) {
                        Log.w(TAG, "Rewarded ad failed to show: " + adError.getMessage());
                        loadRewardedAd();
                    }
                });
                ad.show(RefrigerationCalcActivity.this, new OnUserEarnedRewardListener() {
                    @Override
                    public void onUserEarnedReward(RewardItem rewardItem) {
                        grantRewardToken();
                    }
                });
            }
        });
    }

    /** Atomically increments the pending reward-token counter in prefs. */
    private void grantRewardToken() {
        SharedPreferences prefs = getSharedPreferences(PREFS_NAME, MODE_PRIVATE);
        int pending = prefs.getInt(PREF_PENDING_REWARD_TOKENS, 0) + 1;
        prefs.edit().putInt(PREF_PENDING_REWARD_TOKENS, pending).apply();
        Log.i(TAG, "Reward token granted. Pending: " + pending);
    }

    /**
     * Returns the number of reward tokens earned since the last call and resets
     * the pending counter to zero. Called from Python to credit entitlements.
     */
    public int consumePendingRewardTokens() {
        SharedPreferences prefs = getSharedPreferences(PREFS_NAME, MODE_PRIVATE);
        int pending = prefs.getInt(PREF_PENDING_REWARD_TOKENS, 0);
        if (pending > 0) {
            prefs.edit().putInt(PREF_PENDING_REWARD_TOKENS, 0).apply();
        }
        return pending;
    }

    public void shareFile(final String path, final String mimeType,
                          final String subject, final String text) {
        runOnUiThread(new Runnable() {
            @Override
            public void run() {
                try {
                    File file = new File(path);
                    if (!file.exists()) {
                        Log.w(TAG, "shareFile: plik nie istnieje " + path);
                        return;
                    }

                    Uri uri = null;
                    // Android 10+ (API 29): kopiujemy plik do publicznego MediaStore
                    // (Pobrane) i udostępniamy content:// URI — Gmail/Outlook moga go
                    // odczytac (prywatny katalog aplikacji jest dla nich niewidoczny).
                    if (Build.VERSION.SDK_INT >= 29) {
                        uri = exportToDownloads(file, mimeType);
                    }
                    if (uri == null) {
                        // Fallback dla starszych Androidow: file:// + StrictMode.
                        StrictMode.setVmPolicy(new StrictMode.VmPolicy.Builder().build());
                        uri = Uri.fromFile(file);
                    }

                    Intent intent = new Intent(Intent.ACTION_SEND);
                    intent.setType(mimeType != null ? mimeType : "application/octet-stream");
                    intent.putExtra(Intent.EXTRA_STREAM, uri);
                    if (subject != null) {
                        intent.putExtra(Intent.EXTRA_SUBJECT, subject);
                    }
                    if (text != null) {
                        intent.putExtra(Intent.EXTRA_TEXT, text);
                    }
                    intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
                    startActivity(Intent.createChooser(intent, subject));
                } catch (Exception e) {
                    Log.e(TAG, "shareFile nie powiod\u0142o si\u0119", e);
                }
            }
        });
    }

    /**
     * Kopiuje plik do publicznego katalogu Pobrane przez MediaStore i zwraca
     * jego content:// URI (czytelny dla innych aplikacji). API 29+.
     */
    private Uri exportToDownloads(File file, String mimeType) {
        try {
            ContentResolver resolver = getContentResolver();
            ContentValues values = new ContentValues();
            values.put(MediaStore.Downloads.DISPLAY_NAME, file.getName());
            values.put(MediaStore.Downloads.MIME_TYPE,
                    mimeType != null ? mimeType : "application/pdf");
            values.put(MediaStore.Downloads.RELATIVE_PATH, Environment.DIRECTORY_DOWNLOADS);
            values.put(MediaStore.Downloads.IS_PENDING, 1);

            Uri item = resolver.insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, values);
            if (item == null) {
                return null;
            }
            OutputStream os = null;
            InputStream is = null;
            try {
                os = resolver.openOutputStream(item);
                is = new FileInputStream(file);
                byte[] buf = new byte[8192];
                int n;
                while ((n = is.read(buf)) > 0) {
                    os.write(buf, 0, n);
                }
            } finally {
                if (is != null) { try { is.close(); } catch (Exception ignored) {} }
                if (os != null) { try { os.close(); } catch (Exception ignored) {} }
            }
            values.clear();
            values.put(MediaStore.Downloads.IS_PENDING, 0);
            resolver.update(item, values, null, null);
            return item;
        } catch (Exception e) {
            Log.e(TAG, "exportToDownloads nie powiod\u0142o si\u0119", e);
            return null;
        }
    }

    private boolean isDebugBuild() {
        return (getApplicationInfo().flags & ApplicationInfo.FLAG_DEBUGGABLE) != 0;
    }

    private AdSize getAdSize() {
        DisplayMetrics metrics = getResources().getDisplayMetrics();
        int adWidth = (int) (metrics.widthPixels / metrics.density);
        if (adWidth <= 0) {
            adWidth = 360;
        }
        return AdSize.getCurrentOrientationAnchoredAdaptiveBannerAdSize(this, adWidth);
    }

    public int getBannerHeightDp() {
        if (bannerAdView == null || bannerAdView.getAdSize() == null) {
            return 0;
        }
        return bannerAdView.getAdSize().getHeight();
    }

    public boolean isProNoAdsActive() {
        SharedPreferences prefs = getSharedPreferences(PREFS_NAME, MODE_PRIVATE);
        return prefs.getBoolean(PREF_PRO_NO_ADS, false)
                || prefs.getBoolean(PREF_PRO_SUBSCRIPTION, false);
    }

    public void launchProPurchase() {
        runOnUiThread(new Runnable() {
            @Override
            public void run() {
                if (isProNoAdsActive()) {
                    hideBanner();
                    return;
                }
                if (billingClient == null) {
                    initializeBilling();
                }
                if (billingClient == null || !billingClient.isReady()) {
                    pendingProPurchaseLaunch = true;
                    startBillingConnection();
                    return;
                }
                if (proSubscriptionDetails == null) {
                    pendingProPurchaseLaunch = true;
                    queryProProductDetails();
                    return;
                }
                String offerToken = getSubscriptionOfferToken(proSubscriptionDetails);
                if (offerToken == null) {
                    Log.w(TAG, "PRO subscription offer token is unavailable.");
                    pendingProPurchaseLaunch = false;
                    queryProProductDetails();
                    return;
                }
                BillingFlowParams.ProductDetailsParams productParams =
                        BillingFlowParams.ProductDetailsParams.newBuilder()
                                .setProductDetails(proSubscriptionDetails)
                                .setOfferToken(offerToken)
                                .build();
                BillingFlowParams flowParams = BillingFlowParams.newBuilder()
                        .setProductDetailsParamsList(Collections.singletonList(productParams))
                        .build();
                BillingResult result = billingClient.launchBillingFlow(
                        RefrigerationCalcActivity.this,
                        flowParams
                );
                if (result.getResponseCode() == BillingClient.BillingResponseCode.ITEM_ALREADY_OWNED) {
                    queryOwnedPurchases();
                } else if (result.getResponseCode() != BillingClient.BillingResponseCode.OK) {
                    Log.w(TAG, "PRO subscription launch failed: " + result.getDebugMessage());
                }
            }
        });
    }

    /** Czy moduł doboru zaworów został kupiony (jednorazowy produkt INAPP). */
    public boolean isModuleValvesOwned() {
        return getSharedPreferences(PREFS_NAME, MODE_PRIVATE)
                .getBoolean(PREF_MODULE_VALVES, false);
    }

    /** Uruchamia zakup modułu zaworów (jednorazowy produkt ``module_valves``). */
    public void launchModulePurchase() {
        runOnUiThread(new Runnable() {
            @Override
            public void run() {
                if (isModuleValvesOwned()) {
                    return;
                }
                if (billingClient == null) {
                    initializeBilling();
                }
                if (billingClient == null || !billingClient.isReady()) {
                    pendingModuleValvesLaunch = true;
                    startBillingConnection();
                    return;
                }
                if (moduleValvesProductDetails == null) {
                    pendingModuleValvesLaunch = true;
                    queryModuleValvesProductDetails();
                    return;
                }
                BillingFlowParams.ProductDetailsParams productParams =
                        BillingFlowParams.ProductDetailsParams.newBuilder()
                                .setProductDetails(moduleValvesProductDetails)
                                .build();
                BillingFlowParams flowParams = BillingFlowParams.newBuilder()
                        .setProductDetailsParamsList(Collections.singletonList(productParams))
                        .build();
                BillingResult result = billingClient.launchBillingFlow(
                        RefrigerationCalcActivity.this,
                        flowParams
                );
                if (result.getResponseCode() == BillingClient.BillingResponseCode.ITEM_ALREADY_OWNED) {
                    queryOwnedPurchases();
                } else if (result.getResponseCode() != BillingClient.BillingResponseCode.OK) {
                    Log.w(TAG, "Module valves purchase launch failed: " + result.getDebugMessage());
                }
            }
        });
    }

    private void initializeBilling() {
        if (billingClient != null) {
            return;
        }
        billingClient = BillingClient.newBuilder(this)
                .setListener(this)
                .enableAutoServiceReconnection()
                .enablePendingPurchases(
                        PendingPurchasesParams.newBuilder()
                                .enableOneTimeProducts()
                                .build()
                )
                .build();
        startBillingConnection();
    }

    private void startBillingConnection() {
        if (billingClient == null || billingConnecting) {
            return;
        }
        if (billingClient.isReady()) {
            queryProProductDetails();
            queryModuleValvesProductDetails();
            queryOwnedPurchases();
            return;
        }

        billingConnecting = true;
        billingClient.startConnection(new BillingClientStateListener() {
            @Override
            public void onBillingSetupFinished(BillingResult billingResult) {
                billingConnecting = false;
                if (billingResult.getResponseCode() == BillingClient.BillingResponseCode.OK) {
                    queryProProductDetails();
                    queryModuleValvesProductDetails();
                    queryOwnedPurchases();
                } else {
                    Log.w(TAG, "Billing setup failed: " + billingResult.getDebugMessage());
                }
            }

            @Override
            public void onBillingServiceDisconnected() {
                billingConnecting = false;
            }
        });
    }

    private String getSubscriptionOfferToken(ProductDetails productDetails) {
        if (productDetails == null
                || productDetails.getSubscriptionOfferDetails() == null
                || productDetails.getSubscriptionOfferDetails().isEmpty()) {
            return null;
        }
        for (ProductDetails.SubscriptionOfferDetails offer :
                productDetails.getSubscriptionOfferDetails()) {
            if (PRO_BASE_PLAN_ID.equals(offer.getBasePlanId())) {
                return offer.getOfferToken();
            }
        }
        return productDetails.getSubscriptionOfferDetails().get(0).getOfferToken();
    }

    private void queryProProductDetails() {
        if (billingClient == null || !billingClient.isReady()) {
            startBillingConnection();
            return;
        }

        QueryProductDetailsParams.Product product =
                QueryProductDetailsParams.Product.newBuilder()
                        .setProductId(PRO_SUBSCRIPTION_ID)
                        .setProductType(BillingClient.ProductType.SUBS)
                        .build();
        QueryProductDetailsParams params = QueryProductDetailsParams.newBuilder()
                .setProductList(Collections.singletonList(product))
                .build();

        billingClient.queryProductDetailsAsync(params, new ProductDetailsResponseListener() {
            @Override
            public void onProductDetailsResponse(
                    BillingResult billingResult,
                    QueryProductDetailsResult productDetailsResult) {
                if (billingResult.getResponseCode() == BillingClient.BillingResponseCode.OK
                        && productDetailsResult != null
                        && !productDetailsResult.getProductDetailsList().isEmpty()) {
                    proSubscriptionDetails = productDetailsResult.getProductDetailsList().get(0);
                    if (pendingProPurchaseLaunch) {
                        pendingProPurchaseLaunch = false;
                        launchProPurchase();
                    }
                } else {
                    Log.w(TAG, "Cannot fetch PRO product: " + billingResult.getDebugMessage());
                }
            }
        });
    }

    private void queryModuleValvesProductDetails() {
        if (billingClient == null || !billingClient.isReady()) {
            startBillingConnection();
            return;
        }

        QueryProductDetailsParams.Product product =
                QueryProductDetailsParams.Product.newBuilder()
                        .setProductId(MODULE_VALVES_PRODUCT_ID)
                        .setProductType(BillingClient.ProductType.INAPP)
                        .build();
        QueryProductDetailsParams params = QueryProductDetailsParams.newBuilder()
                .setProductList(Collections.singletonList(product))
                .build();

        billingClient.queryProductDetailsAsync(params, new ProductDetailsResponseListener() {
            @Override
            public void onProductDetailsResponse(
                    BillingResult billingResult,
                    QueryProductDetailsResult productDetailsResult) {
                if (billingResult.getResponseCode() == BillingClient.BillingResponseCode.OK
                        && productDetailsResult != null
                        && !productDetailsResult.getProductDetailsList().isEmpty()) {
                    moduleValvesProductDetails = productDetailsResult.getProductDetailsList().get(0);
                    if (pendingModuleValvesLaunch) {
                        pendingModuleValvesLaunch = false;
                        launchModulePurchase();
                    }
                } else {
                    Log.w(TAG, "Cannot fetch valves module product: " + billingResult.getDebugMessage());
                }
            }
        });
    }

    private void queryOwnedPurchases() {
        if (billingClient == null || !billingClient.isReady()) {
            startBillingConnection();
            return;
        }
        queryOwnedInAppPurchases();
        queryOwnedSubscriptionPurchases();
    }

    private void queryOwnedInAppPurchases() {
        QueryPurchasesParams params = QueryPurchasesParams.newBuilder()
                .setProductType(BillingClient.ProductType.INAPP)
                .build();
        billingClient.queryPurchasesAsync(params, new PurchasesResponseListener() {
            @Override
            public void onQueryPurchasesResponse(BillingResult billingResult, List<Purchase> purchases) {
                if (billingResult.getResponseCode() != BillingClient.BillingResponseCode.OK) {
                    Log.w(TAG, "Cannot query purchases: " + billingResult.getDebugMessage());
                    return;
                }
                boolean ownsLegacyPro = false;
                boolean ownsValves = false;
                if (purchases != null) {
                    for (Purchase purchase : purchases) {
                        handlePurchase(purchase);
                        if (purchase != null
                                && purchase.getPurchaseState() == Purchase.PurchaseState.PURCHASED) {
                            if (purchase.getProducts().contains(LEGACY_PRO_PRODUCT_ID)) {
                                ownsLegacyPro = true;
                            }
                            if (purchase.getProducts().contains(MODULE_VALVES_PRODUCT_ID)) {
                                ownsValves = true;
                            }
                        }
                    }
                }
                if (!ownsLegacyPro && isLegacyProNoAdsActive()) {
                    setProNoAdsActive(false);
                }
                if (!ownsValves && isModuleValvesOwned()) {
                    setModuleValvesOwned(false);
                }
            }
        });
    }

    private void queryOwnedSubscriptionPurchases() {
        QueryPurchasesParams params = QueryPurchasesParams.newBuilder()
                .setProductType(BillingClient.ProductType.SUBS)
                .build();
        billingClient.queryPurchasesAsync(params, new PurchasesResponseListener() {
            @Override
            public void onQueryPurchasesResponse(BillingResult billingResult, List<Purchase> purchases) {
                if (billingResult.getResponseCode() != BillingClient.BillingResponseCode.OK) {
                    Log.w(TAG, "Cannot query subscriptions: " + billingResult.getDebugMessage());
                    return;
                }
                boolean ownsSubscription = false;
                if (purchases != null) {
                    for (Purchase purchase : purchases) {
                        handlePurchase(purchase);
                        if (purchase != null
                                && purchase.getPurchaseState() == Purchase.PurchaseState.PURCHASED
                                && purchase.getProducts().contains(PRO_SUBSCRIPTION_ID)) {
                            ownsSubscription = true;
                        }
                    }
                }
                if (!ownsSubscription && isProSubscriptionActive()) {
                    setProSubscriptionActive(false);
                }
            }
        });
    }

    @Override
    public void onPurchasesUpdated(BillingResult billingResult, List<Purchase> purchases) {
        int code = billingResult.getResponseCode();
        if (code == BillingClient.BillingResponseCode.OK && purchases != null) {
            for (Purchase purchase : purchases) {
                handlePurchase(purchase);
            }
        } else if (code == BillingClient.BillingResponseCode.ITEM_ALREADY_OWNED) {
            queryOwnedPurchases();
        } else if (code != BillingClient.BillingResponseCode.USER_CANCELED) {
            Log.w(TAG, "Purchase update failed: " + billingResult.getDebugMessage());
        }
    }

    private boolean handlePurchase(Purchase purchase) {
        if (purchase == null) {
            return false;
        }
        if (purchase.getPurchaseState() != Purchase.PurchaseState.PURCHASED) {
            Log.i(TAG, "Purchase is pending.");
            return false;
        }

        boolean handled = false;
        if (purchase.getProducts().contains(LEGACY_PRO_PRODUCT_ID)) {
            setProNoAdsActive(true);
            handled = true;
        }
        if (purchase.getProducts().contains(PRO_SUBSCRIPTION_ID)) {
            setProSubscriptionActive(true);
            handled = true;
        }
        if (purchase.getProducts().contains(MODULE_VALVES_PRODUCT_ID)) {
            setModuleValvesOwned(true);
            handled = true;
        }
        if (!handled) {
            return false;
        }

        if (!purchase.isAcknowledged() && billingClient != null && billingClient.isReady()) {
            AcknowledgePurchaseParams params = AcknowledgePurchaseParams.newBuilder()
                    .setPurchaseToken(purchase.getPurchaseToken())
                    .build();
            billingClient.acknowledgePurchase(params, new AcknowledgePurchaseResponseListener() {
                @Override
                public void onAcknowledgePurchaseResponse(BillingResult billingResult) {
                    if (billingResult.getResponseCode() != BillingClient.BillingResponseCode.OK) {
                        Log.w(TAG, "Acknowledge failed: " + billingResult.getDebugMessage());
                    }
                }
            });
        }
        return true;
    }

    private boolean isLegacyProNoAdsActive() {
        return getSharedPreferences(PREFS_NAME, MODE_PRIVATE)
                .getBoolean(PREF_PRO_NO_ADS, false);
    }

    private boolean isProSubscriptionActive() {
        return getSharedPreferences(PREFS_NAME, MODE_PRIVATE)
                .getBoolean(PREF_PRO_SUBSCRIPTION, false);
    }

    private void setProNoAdsActive(boolean active) {
        SharedPreferences.Editor editor = getSharedPreferences(PREFS_NAME, MODE_PRIVATE).edit();
        editor.putBoolean(PREF_PRO_NO_ADS, active);
        editor.apply();
        updateAdsForProStatus();
    }

    private void setProSubscriptionActive(boolean active) {
        SharedPreferences.Editor editor = getSharedPreferences(PREFS_NAME, MODE_PRIVATE).edit();
        editor.putBoolean(PREF_PRO_SUBSCRIPTION, active);
        editor.apply();
        updateAdsForProStatus();
    }

    private void updateAdsForProStatus() {
        runOnUiThread(new Runnable() {
            @Override
            public void run() {
                if (isProNoAdsActive()) {
                    hideBanner();
                } else {
                    attachBanner();
                }
            }
        });
    }

    private void setModuleValvesOwned(boolean owned) {
        SharedPreferences.Editor editor = getSharedPreferences(PREFS_NAME, MODE_PRIVATE).edit();
        editor.putBoolean(PREF_MODULE_VALVES, owned);
        editor.apply();
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (bannerAdView != null && !isProNoAdsActive()) {
            bannerAdView.resume();
        }
        if (billingClient != null && billingClient.isReady()) {
            queryOwnedPurchases();
        } else {
            startBillingConnection();
        }
    }

    @Override
    protected void onPause() {
        if (bannerAdView != null) {
            bannerAdView.pause();
        }
        super.onPause();
    }

    @Override
    protected void onDestroy() {
        removeAnimatedIntro();
        hideBanner();
        if (billingClient != null) {
            billingClient.endConnection();
            billingClient = null;
        }
        super.onDestroy();
    }
}

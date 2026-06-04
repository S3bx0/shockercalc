package pl.mdpuch.shockercalc;

import android.content.SharedPreferences;
import android.content.pm.ApplicationInfo;
import android.os.Bundle;
import android.util.DisplayMetrics;
import android.util.Log;
import android.view.Gravity;
import android.view.ViewGroup;
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
import com.google.android.ump.ConsentDebugSettings;
import com.google.android.ump.ConsentInformation;
import com.google.android.ump.ConsentRequestParameters;
import com.google.android.ump.FormError;
import com.google.android.ump.UserMessagingPlatform;

import org.kivy.android.PythonActivity;

import java.util.Collections;
import java.util.List;

public class ShockerCalcActivity extends PythonActivity implements PurchasesUpdatedListener {
    private static final String TAG = "ShockerCalc";
    private static final String LIVE_BANNER_AD_UNIT_ID =
            "ca-app-pub-7481054652344026/5599859341";
    private static final String TEST_BANNER_AD_UNIT_ID =
            "ca-app-pub-3940256099942544/9214589741";
    private static final String LIVE_REWARDED_AD_UNIT_ID =
            "ca-app-pub-7481054652344026/1548239161";
    private static final String TEST_REWARDED_AD_UNIT_ID =
            "ca-app-pub-3940256099942544/5224354917";
    private static final String PRO_PRODUCT_ID = "pro_no_ads";
    private static final String PREFS_NAME = "shockercalc_billing";
    private static final String PREF_PRO_NO_ADS = "pro_no_ads";
    private static final String PREF_PENDING_REWARD_TOKENS = "pending_reward_tokens";

    private AdView bannerAdView;
    private FrameLayout bannerContainer;
    private RewardedAd rewardedAd;
    private boolean rewardedLoading;
    private boolean adsInitialized;
    private ConsentInformation consentInformation;
    private BillingClient billingClient;
    private ProductDetails proProductDetails;
    private boolean billingConnecting;
    private boolean pendingProPurchaseLaunch;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        initializeBilling();
        initializeAds();
    }

    private void initializeAds() {
        if (isProNoAdsActive()) {
            return;
        }
        requestConsentThenInitAds();
    }

    /**
     * Uruchamia przepływ zgody Google UMP (wymagany dla użytkowników z EOG/UK
     * przy reklamach spersonalizowanych). Po zebraniu zgody — lub gdy nie jest
     * wymagana — inicjalizuje SDK reklam tylko jeśli {@code canRequestAds()}.
     */
    private void requestConsentThenInitAds() {
        ConsentRequestParameters.Builder paramsBuilder =
                new ConsentRequestParameters.Builder();
        if (isDebugBuild()) {
            // W debug wymuszamy geografię EOG, aby przetestować formularz zgody.
            ConsentDebugSettings debugSettings = new ConsentDebugSettings.Builder(this)
                    .setDebugGeography(ConsentDebugSettings.DebugGeography.DEBUG_GEOGRAPHY_EEA)
                    .build();
            paramsBuilder.setConsentDebugSettings(debugSettings);
        }
        ConsentRequestParameters params = paramsBuilder.build();

        consentInformation = UserMessagingPlatform.getConsentInformation(this);
        consentInformation.requestConsentInfoUpdate(
                this,
                params,
                new ConsentInformation.OnConsentInfoUpdateSuccessListener() {
                    @Override
                    public void onConsentInfoUpdateSuccess() {
                        UserMessagingPlatform.loadAndShowConsentFormIfRequired(
                                ShockerCalcActivity.this,
                                new ConsentInformation.OnConsentFormDismissedListener() {
                                    @Override
                                    public void onConsentFormDismissed(FormError formError) {
                                        if (formError != null) {
                                            Log.w(TAG, "Consent form error: "
                                                    + formError.getMessage());
                                        }
                                        maybeInitializeAdsAfterConsent();
                                    }
                                });
                    }
                },
                new ConsentInformation.OnConsentInfoUpdateFailureListener() {
                    @Override
                    public void onConsentInfoUpdateFailure(FormError formError) {
                        Log.w(TAG, "Consent info update failed: "
                                + (formError != null ? formError.getMessage() : "unknown"));
                        // Mimo błędu próbujemy zainicjalizować (np. gdy poza EOG).
                        maybeInitializeAdsAfterConsent();
                    }
                });
    }

    private void maybeInitializeAdsAfterConsent() {
        if (consentInformation == null || !consentInformation.canRequestAds()) {
            Log.i(TAG, "Ads not requested: consent not granted / not available.");
            return;
        }
        startMobileAdsSdk();
    }

    /** True, gdy dostępny jest formularz opcji prywatności (zmiana zgody). */
    public boolean isPrivacyOptionsRequired() {
        return consentInformation != null
                && consentInformation.getPrivacyOptionsRequirementStatus()
                == ConsentInformation.PrivacyOptionsRequirementStatus.REQUIRED;
    }

    /** Ponownie otwiera formularz zgody (wywoływane z menu Prywatność). */
    public void showPrivacyOptionsForm() {
        runOnUiThread(new Runnable() {
            @Override
            public void run() {
                UserMessagingPlatform.showPrivacyOptionsForm(
                        ShockerCalcActivity.this,
                        new ConsentInformation.OnConsentFormDismissedListener() {
                            @Override
                            public void onConsentFormDismissed(FormError formError) {
                                if (formError != null) {
                                    Log.w(TAG, "Privacy options error: "
                                            + formError.getMessage());
                                }
                            }
                        });
            }
        });
    }

    private void startMobileAdsSdk() {
        if (adsInitialized || isProNoAdsActive()) {
            return;
        }
        new Thread(new Runnable() {
            @Override
            public void run() {
                MobileAds.initialize(
                        ShockerCalcActivity.this,
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
        return isDebugBuild() ? TEST_BANNER_AD_UNIT_ID : LIVE_BANNER_AD_UNIT_ID;
    }

    private String getRewardedAdUnitId() {
        return isDebugBuild() ? TEST_REWARDED_AD_UNIT_ID : LIVE_REWARDED_AD_UNIT_ID;
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
                ad.show(ShockerCalcActivity.this, new OnUserEarnedRewardListener() {
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
        return getSharedPreferences(PREFS_NAME, MODE_PRIVATE).getBoolean(PREF_PRO_NO_ADS, false);
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
                if (proProductDetails == null) {
                    pendingProPurchaseLaunch = true;
                    queryProProductDetails();
                    return;
                }
                BillingFlowParams.ProductDetailsParams productParams =
                        BillingFlowParams.ProductDetailsParams.newBuilder()
                                .setProductDetails(proProductDetails)
                                .build();
                BillingFlowParams flowParams = BillingFlowParams.newBuilder()
                        .setProductDetailsParamsList(Collections.singletonList(productParams))
                        .build();
                BillingResult result = billingClient.launchBillingFlow(
                        ShockerCalcActivity.this,
                        flowParams
                );
                if (result.getResponseCode() == BillingClient.BillingResponseCode.ITEM_ALREADY_OWNED) {
                    queryOwnedPurchases();
                } else if (result.getResponseCode() != BillingClient.BillingResponseCode.OK) {
                    Log.w(TAG, "PRO purchase launch failed: " + result.getDebugMessage());
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

    private void queryProProductDetails() {
        if (billingClient == null || !billingClient.isReady()) {
            startBillingConnection();
            return;
        }

        QueryProductDetailsParams.Product product =
                QueryProductDetailsParams.Product.newBuilder()
                        .setProductId(PRO_PRODUCT_ID)
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
                    proProductDetails = productDetailsResult.getProductDetailsList().get(0);
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

    private void queryOwnedPurchases() {
        if (billingClient == null || !billingClient.isReady()) {
            startBillingConnection();
            return;
        }
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
                boolean ownsPro = false;
                if (purchases != null) {
                    for (Purchase purchase : purchases) {
                        ownsPro = handlePurchase(purchase) || ownsPro;
                    }
                }
                if (!ownsPro && isProNoAdsActive()) {
                    setProNoAdsActive(false);
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
        if (purchase == null || !purchase.getProducts().contains(PRO_PRODUCT_ID)) {
            return false;
        }
        if (purchase.getPurchaseState() != Purchase.PurchaseState.PURCHASED) {
            Log.i(TAG, "PRO purchase is pending.");
            return false;
        }

        setProNoAdsActive(true);
        if (!purchase.isAcknowledged() && billingClient != null && billingClient.isReady()) {
            AcknowledgePurchaseParams params = AcknowledgePurchaseParams.newBuilder()
                    .setPurchaseToken(purchase.getPurchaseToken())
                    .build();
            billingClient.acknowledgePurchase(params, new AcknowledgePurchaseResponseListener() {
                @Override
                public void onAcknowledgePurchaseResponse(BillingResult billingResult) {
                    if (billingResult.getResponseCode() != BillingClient.BillingResponseCode.OK) {
                        Log.w(TAG, "PRO acknowledge failed: " + billingResult.getDebugMessage());
                    }
                }
            });
        }
        return true;
    }

    private void setProNoAdsActive(boolean active) {
        SharedPreferences.Editor editor = getSharedPreferences(PREFS_NAME, MODE_PRIVATE).edit();
        editor.putBoolean(PREF_PRO_NO_ADS, active);
        editor.apply();
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
        hideBanner();
        if (billingClient != null) {
            billingClient.endConnection();
            billingClient = null;
        }
        super.onDestroy();
    }
}

package pl.smilczarek.refrigerationcalc;

import android.app.Activity;
import android.content.SharedPreferences;
import android.util.DisplayMetrics;
import android.util.Log;
import android.view.Gravity;
import android.view.ViewGroup;
import android.widget.FrameLayout;

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

/** Owns AdMob banner and rewarded-ad state for the Android activity. */
final class AdvertisingService {
    interface NoAdsProvider {
        boolean isNoAdsActive();
    }

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
    private static final String PREF_PENDING_REWARD_TOKENS = "pending_reward_tokens";

    private final Activity activity;
    private final SharedPreferences preferences;
    private final boolean debugBuild;
    private final NoAdsProvider noAdsProvider;

    private AdView bannerAdView;
    private FrameLayout bannerContainer;
    private RewardedAd rewardedAd;
    private boolean rewardedLoading;
    private boolean adsInitialized;
    private volatile String activeAdTab = "freezing";

    AdvertisingService(
            Activity activity,
            SharedPreferences preferences,
            boolean debugBuild,
            NoAdsProvider noAdsProvider) {
        this.activity = activity;
        this.preferences = preferences;
        this.debugBuild = debugBuild;
        this.noAdsProvider = noAdsProvider;
    }

    void startMobileAdsSdk() {
        if (adsInitialized || noAdsProvider.isNoAdsActive()) {
            return;
        }
        new Thread(new Runnable() {
            @Override
            public void run() {
                MobileAds.initialize(
                        activity,
                        new OnInitializationCompleteListener() {
                            @Override
                            public void onInitializationComplete(
                                    InitializationStatus initializationStatus) {
                                activity.runOnUiThread(new Runnable() {
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
        if (noAdsProvider.isNoAdsActive() || bannerAdView != null) {
            return;
        }

        ViewGroup root = activity.findViewById(android.R.id.content);
        if (root == null) {
            Log.w(TAG, "Cannot attach banner: root content view is null.");
            return;
        }

        bannerContainer = new FrameLayout(activity);
        FrameLayout.LayoutParams containerParams = new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT);
        containerParams.gravity = Gravity.BOTTOM | Gravity.CENTER_HORIZONTAL;

        bannerAdView = new AdView(activity);
        bannerAdView.setAdUnitId(getBannerAdUnitId());
        bannerAdView.setAdSize(getAdSize());

        bannerContainer.addView(bannerAdView);
        root.addView(bannerContainer, containerParams);

        bannerAdView.loadAd(new AdRequest.Builder().build());
        Log.i(TAG, "AdMob banner requested. Debug test ads: " + debugBuild);
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
        if (debugBuild) {
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
        if (debugBuild) {
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

    void setActiveAdTab(final String tab) {
        final String normalized = normalizeAdTab(tab);
        if (normalized.equals(activeAdTab)) {
            return;
        }
        activeAdTab = normalized;
        if (noAdsProvider.isNoAdsActive()) {
            return;
        }
        activity.runOnUiThread(new Runnable() {
            @Override
            public void run() {
                if (bannerAdView != null || bannerContainer != null) {
                    hideBanner();
                    attachBanner();
                }
                if (rewardedAd != null) {
                    rewardedAd = null;
                }
                loadRewardedAd();
            }
        });
    }

    private void loadRewardedAd() {
        if (noAdsProvider.isNoAdsActive() || rewardedAd != null || rewardedLoading) {
            return;
        }
        rewardedLoading = true;
        RewardedAd.load(
                activity,
                getRewardedAdUnitId(),
                new AdRequest.Builder().build(),
                new RewardedAdLoadCallback() {
                    @Override
                    public void onAdLoaded(RewardedAd ad) {
                        rewardedLoading = false;
                        rewardedAd = ad;
                        Log.i(TAG, "Rewarded ad loaded. Debug test ads: " + debugBuild);
                    }

                    @Override
                    public void onAdFailedToLoad(LoadAdError error) {
                        rewardedLoading = false;
                        rewardedAd = null;
                        Log.w(TAG, "Rewarded ad failed to load: " + error.getMessage());
                    }
                });
    }

    boolean isRewardedAdReady() {
        return rewardedAd != null;
    }

    void showRewardedAd() {
        activity.runOnUiThread(new Runnable() {
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
                ad.show(activity, new OnUserEarnedRewardListener() {
                    @Override
                    public void onUserEarnedReward(RewardItem rewardItem) {
                        grantRewardToken();
                    }
                });
            }
        });
    }

    private void grantRewardToken() {
        int pending = preferences.getInt(PREF_PENDING_REWARD_TOKENS, 0) + 1;
        preferences.edit().putInt(PREF_PENDING_REWARD_TOKENS, pending).apply();
        Log.i(TAG, "Reward token granted. Pending: " + pending);
    }

    int consumePendingRewardTokens() {
        int pending = preferences.getInt(PREF_PENDING_REWARD_TOKENS, 0);
        if (pending > 0) {
            preferences.edit().putInt(PREF_PENDING_REWARD_TOKENS, 0).apply();
        }
        return pending;
    }

    private AdSize getAdSize() {
        DisplayMetrics metrics = activity.getResources().getDisplayMetrics();
        int adWidth = (int) (metrics.widthPixels / metrics.density);
        if (adWidth <= 0) {
            adWidth = 360;
        }
        return AdSize.getCurrentOrientationAnchoredAdaptiveBannerAdSize(
                activity,
                adWidth);
    }

    int getBannerHeightDp() {
        if (bannerAdView == null || bannerAdView.getAdSize() == null) {
            return 0;
        }
        return bannerAdView.getAdSize().getHeight();
    }

    void updateForProStatus() {
        activity.runOnUiThread(new Runnable() {
            @Override
            public void run() {
                if (noAdsProvider.isNoAdsActive()) {
                    hideBanner();
                } else {
                    attachBanner();
                }
            }
        });
    }

    void onResume() {
        if (bannerAdView != null && !noAdsProvider.isNoAdsActive()) {
            bannerAdView.resume();
        }
    }

    void onPause() {
        if (bannerAdView != null) {
            bannerAdView.pause();
        }
    }

    void onDestroy() {
        hideBanner();
    }
}

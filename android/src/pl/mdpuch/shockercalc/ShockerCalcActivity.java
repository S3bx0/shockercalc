package pl.mdpuch.shockercalc;

import android.os.Bundle;
import android.util.DisplayMetrics;
import android.util.Log;
import android.view.Gravity;
import android.view.ViewGroup;
import android.widget.FrameLayout;

import com.google.android.gms.ads.AdRequest;
import com.google.android.gms.ads.AdSize;
import com.google.android.gms.ads.AdView;
import com.google.android.gms.ads.MobileAds;
import com.google.android.gms.ads.initialization.InitializationStatus;
import com.google.android.gms.ads.initialization.OnInitializationCompleteListener;

import org.kivy.android.PythonActivity;

public class ShockerCalcActivity extends PythonActivity {
    private static final String TAG = "ShockerCalcAdMob";
    private static final String LIVE_BANNER_AD_UNIT_ID =
            "ca-app-pub-7481054652344026/5599859341";
    private static final String TEST_BANNER_AD_UNIT_ID =
            "ca-app-pub-3940256099942544/9214589741";

    private AdView bannerAdView;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        initializeAds();
    }

    private void initializeAds() {
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
                                        attachBanner();
                                    }
                                });
                            }
                        });
            }
        }).start();
    }

    private void attachBanner() {
        if (bannerAdView != null) {
            return;
        }

        ViewGroup root = findViewById(android.R.id.content);
        if (root == null) {
            Log.w(TAG, "Cannot attach banner: root content view is null.");
            return;
        }

        FrameLayout container = new FrameLayout(this);
        FrameLayout.LayoutParams containerParams = new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT
        );
        containerParams.gravity = Gravity.BOTTOM | Gravity.CENTER_HORIZONTAL;

        bannerAdView = new AdView(this);
        bannerAdView.setAdUnitId(getBannerAdUnitId());
        bannerAdView.setAdSize(getAdSize());

        container.addView(bannerAdView);
        root.addView(container, containerParams);

        bannerAdView.loadAd(new AdRequest.Builder().build());
        Log.i(TAG, "AdMob banner requested. Debug test ads: " + BuildConfig.DEBUG);
    }

    private String getBannerAdUnitId() {
        return BuildConfig.DEBUG ? TEST_BANNER_AD_UNIT_ID : LIVE_BANNER_AD_UNIT_ID;
    }

    private AdSize getAdSize() {
        DisplayMetrics metrics = getResources().getDisplayMetrics();
        int adWidth = (int) (metrics.widthPixels / metrics.density);
        if (adWidth <= 0) {
            adWidth = 360;
        }
        return AdSize.getLargeAnchoredAdaptiveBannerAdSize(this, adWidth);
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (bannerAdView != null) {
            bannerAdView.resume();
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
        if (bannerAdView != null) {
            bannerAdView.destroy();
            bannerAdView = null;
        }
        super.onDestroy();
    }
}

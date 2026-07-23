from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JAVA_DIR = ROOT / "android" / "src" / "pl" / "smilczarek" / "refrigerationcalc"
ACTIVITY = JAVA_DIR / "RefrigerationCalcActivity.java"
SERVICE = JAVA_DIR / "AdvertisingService.java"


def _compact(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").split())


def test_activity_keeps_thin_pyjnius_advertising_delegates():
    activity = _compact(ACTIVITY)

    assert "private AdvertisingService advertisingService;" in activity
    assert "advertising().setActiveAdTab(tab);" in activity
    assert "return advertising().isRewardedAdReady();" in activity
    assert "advertising().showRewardedAd();" in activity
    assert "return advertising().consumePendingRewardTokens();" in activity
    assert "return advertising().getBannerHeightDp();" in activity
    assert "advertising().updateForProStatus();" in activity
    assert "advertisingService.onResume();" in activity
    assert "advertisingService.onPause();" in activity
    assert "advertisingService.onDestroy();" in activity


def test_activity_no_longer_owns_admob_sdk_implementation():
    activity = ACTIVITY.read_text(encoding="utf-8")

    assert "import com.google.android.gms.ads" not in activity
    assert "AdView bannerAdView" not in activity
    assert "RewardedAd rewardedAd" not in activity
    assert "LIVE_BANNER_AD_UNIT_ID" not in activity
    assert "LIVE_REWARDED_AD_UNIT_ID" not in activity
    assert "attachBanner" not in activity
    assert "loadRewardedAd" not in activity
    assert "grantRewardToken" not in activity
    assert len(activity.splitlines()) < 900


def test_advertising_service_preserves_ad_unit_routing():
    service = SERVICE.read_text(encoding="utf-8")

    assert "final class AdvertisingService" in service
    assert '"ca-app-pub-7481054652344026/5599859341"' in service
    assert '"ca-app-pub-7481054652344026/6303778370"' in service
    assert '"ca-app-pub-7481054652344026/8198860699"' in service
    assert '"ca-app-pub-7481054652344026/1548239161"' in service
    assert '"ca-app-pub-7481054652344026/1060900411"' in service
    assert '"ca-app-pub-7481054652344026/7623346864"' in service
    assert '"ca-app-pub-3940256099942544/9214589741"' in service
    assert '"ca-app-pub-3940256099942544/5224354917"' in service
    assert 'if ("labor".equals(activeAdTab))' in service
    assert 'if ("valves".equals(activeAdTab))' in service
    assert 'return "freezing";' in service


def test_advertising_service_preserves_banner_and_reward_flow():
    service = SERVICE.read_text(encoding="utf-8")

    assert "MobileAds.initialize(" in service
    assert "AdSize.getCurrentOrientationAnchoredAdaptiveBannerAdSize(" in service
    assert "private volatile int bannerHeightDp;" in service
    assert "bannerHeightDp = bannerAdSize.getHeight();" in service
    assert "return bannerHeightDp;" in service
    assert "bannerAdView.getAdSize()" not in service
    assert "bannerAdView.loadAd(new AdRequest.Builder().build())" in service
    assert "RewardedAd.load(" in service
    assert "ad.setFullScreenContentCallback(" in service
    assert "ad.show(activity," in service
    assert '"pending_reward_tokens"' in service
    assert "grantRewardToken();" in service
    assert "preferences.edit().putInt(PREF_PENDING_REWARD_TOKENS, 0).apply();" in service


def test_advertising_service_preserves_pro_and_lifecycle_contract():
    service = SERVICE.read_text(encoding="utf-8")

    assert "noAdsProvider.isNoAdsActive()" in service
    assert "void updateForProStatus()" in service
    assert "void onResume()" in service
    assert "bannerAdView.resume();" in service
    assert "void onPause()" in service
    assert "bannerAdView.pause();" in service
    assert "void onDestroy()" in service
    assert "hideBanner();" in service

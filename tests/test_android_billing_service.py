from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JAVA_DIR = ROOT / "android" / "src" / "pl" / "smilczarek" / "refrigerationcalc"
ACTIVITY = JAVA_DIR / "RefrigerationCalcActivity.java"
SERVICE = JAVA_DIR / "BillingService.java"


def _compact(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").split())


def test_activity_keeps_thin_pyjnius_billing_delegates():
    activity = _compact(ACTIVITY)

    assert "private BillingService billingService;" in activity
    assert "billing().initialize();" in activity
    assert "return billing().isProNoAdsActive();" in activity
    assert "return billing().getProFormattedPrice();" in activity
    assert "billing().launchProPurchase();" in activity
    assert "return billing().isModuleValvesOwned();" in activity
    assert "billing().launchModulePurchase();" in activity
    assert "billing().onResume();" in activity
    assert "billingService.onDestroy();" in activity
    assert "advertising().updateForProStatus();" in activity


def test_activity_no_longer_owns_billing_sdk_implementation():
    activity = ACTIVITY.read_text(encoding="utf-8")

    assert "import com.android.billingclient" not in activity
    assert "implements PurchasesUpdatedListener" not in activity
    assert "BillingClient billingClient" not in activity
    assert "ProductDetails proSubscriptionDetails" not in activity
    assert "LEGACY_PRO_PRODUCT_ID" not in activity
    assert "PRO_SUBSCRIPTION_ID" not in activity
    assert "MODULE_VALVES_PRODUCT_ID" not in activity
    assert "queryOwnedPurchases" not in activity
    assert "handlePurchase" not in activity
    assert len(activity.splitlines()) < 550


def test_billing_service_preserves_product_and_preference_contract():
    service = SERVICE.read_text(encoding="utf-8")

    assert "final class BillingService implements PurchasesUpdatedListener" in service
    assert 'LEGACY_PRO_PRODUCT_ID = "pro_no_ads"' in service
    assert 'PRO_SUBSCRIPTION_ID = "refrigeration_pro"' in service
    assert 'PRO_BASE_PLAN_ID = "monthly-499"' in service
    assert 'MODULE_VALVES_PRODUCT_ID = "module_valves"' in service
    assert 'PREF_PRO_NO_ADS = "pro_no_ads"' in service
    assert 'PREF_PRO_SUBSCRIPTION = "refrigeration_pro"' in service
    assert 'PREF_MODULE_VALVES = "module_valves"' in service


def test_billing_service_preserves_connection_and_purchase_launches():
    service = _compact(SERVICE)

    assert "BillingClient.newBuilder(activity)" in service
    assert ".setListener(this)" in service
    assert ".enableAutoServiceReconnection()" in service
    assert ".enableOneTimeProducts()" in service
    assert "billingClient.startConnection(" in service
    assert ".setProductType(BillingClient.ProductType.SUBS)" in service
    assert ".setProductType(BillingClient.ProductType.INAPP)" in service
    assert ".setOfferToken(offerToken)" in service
    assert "billingClient.launchBillingFlow(activity, flowParams)" in service
    assert "pendingProPurchaseLaunch = true;" in service
    assert "pendingModuleValvesLaunch = true;" in service


def test_billing_service_exposes_localized_recurring_price():
    service = _compact(SERVICE)

    assert 'private volatile String proFormattedPrice = "";' in service
    assert "String getProFormattedPrice()" in service
    assert "return proFormattedPrice;" in service
    assert "getSubscriptionOfferDetails(productDetails)" in service
    assert "PRO_BASE_PLAN_ID.equals(offer.getBasePlanId())" in service
    assert "offer.getPricingPhases().getPricingPhaseList()" in service
    assert "ProductDetails.RecurrenceMode.INFINITE_RECURRING" in service
    assert "phase.getFormattedPrice()" in service
    assert "proFormattedPrice = getSubscriptionFormattedPrice(proSubscriptionDetails);" in service


def test_billing_service_preserves_ownership_sync_and_revocation():
    service = _compact(SERVICE)

    assert "queryOwnedInAppPurchases();" in service
    assert "queryOwnedSubscriptionPurchases();" in service
    assert "handlePurchase(purchase);" in service
    assert "if (!ownsLegacyPro && isLegacyProNoAdsActive())" in service
    assert "setProNoAdsActive(false);" in service
    assert "if (!ownsSubscription && isProSubscriptionActive())" in service
    assert "setProSubscriptionActive(false);" in service
    assert "if (!ownsValves && isModuleValvesOwned())" in service
    assert "setModuleValvesOwned(false);" in service


def test_billing_service_preserves_acknowledge_and_lifecycle_contract():
    service = _compact(SERVICE)

    assert "code != BillingClient.BillingResponseCode.USER_CANCELED" in service
    assert "!purchase.isAcknowledged()" in service
    assert ".setPurchaseToken(purchase.getPurchaseToken())" in service
    assert "billingClient.acknowledgePurchase(" in service
    assert "noAdsStatusChanged.run();" in service
    assert "void onResume()" in service
    assert "void onDestroy()" in service
    assert "billingClient.endConnection();" in service

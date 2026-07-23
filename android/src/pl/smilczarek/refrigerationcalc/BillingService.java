package pl.smilczarek.refrigerationcalc;

import android.app.Activity;
import android.content.SharedPreferences;
import android.util.Log;

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

import java.util.Collections;
import java.util.List;

/** Owns Google Play Billing products, purchases and persisted entitlements. */
final class BillingService implements PurchasesUpdatedListener {
    private static final String TAG = "RefrigerationCalc";
    private static final String LEGACY_PRO_PRODUCT_ID = "pro_no_ads";
    private static final String PRO_SUBSCRIPTION_ID = "refrigeration_pro";
    private static final String PRO_BASE_PLAN_ID = "monthly-499";
    private static final String MODULE_VALVES_PRODUCT_ID = "module_valves";
    private static final String PREF_PRO_NO_ADS = "pro_no_ads";
    private static final String PREF_PRO_SUBSCRIPTION = "refrigeration_pro";
    private static final String PREF_MODULE_VALVES = "module_valves";

    private final Activity activity;
    private final SharedPreferences preferences;
    private final Runnable noAdsStatusChanged;

    private BillingClient billingClient;
    private ProductDetails proSubscriptionDetails;
    private ProductDetails moduleValvesProductDetails;
    private volatile String proFormattedPrice = "";
    private boolean billingConnecting;
    private boolean pendingProPurchaseLaunch;
    private boolean pendingModuleValvesLaunch;

    BillingService(
            Activity activity,
            SharedPreferences preferences,
            Runnable noAdsStatusChanged) {
        this.activity = activity;
        this.preferences = preferences;
        this.noAdsStatusChanged = noAdsStatusChanged;
    }

    void initialize() {
        if (billingClient != null) {
            return;
        }
        billingClient = BillingClient.newBuilder(activity)
                .setListener(this)
                .enableAutoServiceReconnection()
                .enablePendingPurchases(
                        PendingPurchasesParams.newBuilder()
                                .enableOneTimeProducts()
                                .build()
                )
                .build();
        startConnection();
    }

    boolean isProNoAdsActive() {
        return preferences.getBoolean(PREF_PRO_NO_ADS, false)
                || preferences.getBoolean(PREF_PRO_SUBSCRIPTION, false);
    }

    boolean isModuleValvesOwned() {
        return preferences.getBoolean(PREF_MODULE_VALVES, false);
    }

    String getProFormattedPrice() {
        return proFormattedPrice;
    }

    void launchProPurchase() {
        activity.runOnUiThread(new Runnable() {
            @Override
            public void run() {
                if (isProNoAdsActive()) {
                    noAdsStatusChanged.run();
                    return;
                }
                if (billingClient == null) {
                    initialize();
                }
                if (billingClient == null || !billingClient.isReady()) {
                    pendingProPurchaseLaunch = true;
                    startConnection();
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
                BillingResult result = billingClient.launchBillingFlow(activity, flowParams);
                if (result.getResponseCode()
                        == BillingClient.BillingResponseCode.ITEM_ALREADY_OWNED) {
                    queryOwnedPurchases();
                } else if (result.getResponseCode()
                        != BillingClient.BillingResponseCode.OK) {
                    Log.w(TAG, "PRO subscription launch failed: "
                            + result.getDebugMessage());
                }
            }
        });
    }

    void launchModulePurchase() {
        activity.runOnUiThread(new Runnable() {
            @Override
            public void run() {
                if (isModuleValvesOwned()) {
                    return;
                }
                if (billingClient == null) {
                    initialize();
                }
                if (billingClient == null || !billingClient.isReady()) {
                    pendingModuleValvesLaunch = true;
                    startConnection();
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
                BillingResult result = billingClient.launchBillingFlow(activity, flowParams);
                if (result.getResponseCode()
                        == BillingClient.BillingResponseCode.ITEM_ALREADY_OWNED) {
                    queryOwnedPurchases();
                } else if (result.getResponseCode()
                        != BillingClient.BillingResponseCode.OK) {
                    Log.w(TAG, "Module valves purchase launch failed: "
                            + result.getDebugMessage());
                }
            }
        });
    }

    private void startConnection() {
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
                if (billingResult.getResponseCode()
                        == BillingClient.BillingResponseCode.OK) {
                    queryProProductDetails();
                    queryModuleValvesProductDetails();
                    queryOwnedPurchases();
                } else {
                    Log.w(TAG, "Billing setup failed: "
                            + billingResult.getDebugMessage());
                }
            }

            @Override
            public void onBillingServiceDisconnected() {
                billingConnecting = false;
            }
        });
    }

    private String getSubscriptionOfferToken(ProductDetails productDetails) {
        ProductDetails.SubscriptionOfferDetails offer =
                getSubscriptionOfferDetails(productDetails);
        return offer == null ? null : offer.getOfferToken();
    }

    private ProductDetails.SubscriptionOfferDetails getSubscriptionOfferDetails(
            ProductDetails productDetails) {
        if (productDetails == null
                || productDetails.getSubscriptionOfferDetails() == null
                || productDetails.getSubscriptionOfferDetails().isEmpty()) {
            return null;
        }
        for (ProductDetails.SubscriptionOfferDetails offer :
                productDetails.getSubscriptionOfferDetails()) {
            if (PRO_BASE_PLAN_ID.equals(offer.getBasePlanId())) {
                return offer;
            }
        }
        return productDetails.getSubscriptionOfferDetails().get(0);
    }

    private String getSubscriptionFormattedPrice(ProductDetails productDetails) {
        ProductDetails.SubscriptionOfferDetails offer =
                getSubscriptionOfferDetails(productDetails);
        if (offer == null || offer.getPricingPhases() == null) {
            return "";
        }
        List<ProductDetails.PricingPhase> phases =
                offer.getPricingPhases().getPricingPhaseList();
        if (phases == null || phases.isEmpty()) {
            return "";
        }
        for (ProductDetails.PricingPhase phase : phases) {
            if (phase.getRecurrenceMode()
                    == ProductDetails.RecurrenceMode.INFINITE_RECURRING) {
                return phase.getFormattedPrice();
            }
        }
        return phases.get(phases.size() - 1).getFormattedPrice();
    }

    private void queryProProductDetails() {
        if (billingClient == null || !billingClient.isReady()) {
            startConnection();
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

        billingClient.queryProductDetailsAsync(
                params,
                new ProductDetailsResponseListener() {
                    @Override
                    public void onProductDetailsResponse(
                            BillingResult billingResult,
                            QueryProductDetailsResult productDetailsResult) {
                        if (billingResult.getResponseCode()
                                == BillingClient.BillingResponseCode.OK
                                && productDetailsResult != null
                                && !productDetailsResult.getProductDetailsList().isEmpty()) {
                            proSubscriptionDetails =
                                    productDetailsResult.getProductDetailsList().get(0);
                            proFormattedPrice =
                                    getSubscriptionFormattedPrice(proSubscriptionDetails);
                            if (pendingProPurchaseLaunch) {
                                pendingProPurchaseLaunch = false;
                                launchProPurchase();
                            }
                        } else {
                            Log.w(TAG, "Cannot fetch PRO product: "
                                    + billingResult.getDebugMessage());
                        }
                    }
                });
    }

    private void queryModuleValvesProductDetails() {
        if (billingClient == null || !billingClient.isReady()) {
            startConnection();
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

        billingClient.queryProductDetailsAsync(
                params,
                new ProductDetailsResponseListener() {
                    @Override
                    public void onProductDetailsResponse(
                            BillingResult billingResult,
                            QueryProductDetailsResult productDetailsResult) {
                        if (billingResult.getResponseCode()
                                == BillingClient.BillingResponseCode.OK
                                && productDetailsResult != null
                                && !productDetailsResult.getProductDetailsList().isEmpty()) {
                            moduleValvesProductDetails =
                                    productDetailsResult.getProductDetailsList().get(0);
                            if (pendingModuleValvesLaunch) {
                                pendingModuleValvesLaunch = false;
                                launchModulePurchase();
                            }
                        } else {
                            Log.w(TAG, "Cannot fetch valves module product: "
                                    + billingResult.getDebugMessage());
                        }
                    }
                });
    }

    private void queryOwnedPurchases() {
        if (billingClient == null || !billingClient.isReady()) {
            startConnection();
            return;
        }
        queryOwnedInAppPurchases();
        queryOwnedSubscriptionPurchases();
    }

    private void queryOwnedInAppPurchases() {
        QueryPurchasesParams params = QueryPurchasesParams.newBuilder()
                .setProductType(BillingClient.ProductType.INAPP)
                .build();
        billingClient.queryPurchasesAsync(
                params,
                new PurchasesResponseListener() {
                    @Override
                    public void onQueryPurchasesResponse(
                            BillingResult billingResult,
                            List<Purchase> purchases) {
                        if (billingResult.getResponseCode()
                                != BillingClient.BillingResponseCode.OK) {
                            Log.w(TAG, "Cannot query purchases: "
                                    + billingResult.getDebugMessage());
                            return;
                        }
                        boolean ownsLegacyPro = false;
                        boolean ownsValves = false;
                        if (purchases != null) {
                            for (Purchase purchase : purchases) {
                                handlePurchase(purchase);
                                if (purchase != null
                                        && purchase.getPurchaseState()
                                        == Purchase.PurchaseState.PURCHASED) {
                                    if (purchase.getProducts().contains(
                                            LEGACY_PRO_PRODUCT_ID)) {
                                        ownsLegacyPro = true;
                                    }
                                    if (purchase.getProducts().contains(
                                            MODULE_VALVES_PRODUCT_ID)) {
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
        billingClient.queryPurchasesAsync(
                params,
                new PurchasesResponseListener() {
                    @Override
                    public void onQueryPurchasesResponse(
                            BillingResult billingResult,
                            List<Purchase> purchases) {
                        if (billingResult.getResponseCode()
                                != BillingClient.BillingResponseCode.OK) {
                            Log.w(TAG, "Cannot query subscriptions: "
                                    + billingResult.getDebugMessage());
                            return;
                        }
                        boolean ownsSubscription = false;
                        if (purchases != null) {
                            for (Purchase purchase : purchases) {
                                handlePurchase(purchase);
                                if (purchase != null
                                        && purchase.getPurchaseState()
                                        == Purchase.PurchaseState.PURCHASED
                                        && purchase.getProducts().contains(
                                                PRO_SUBSCRIPTION_ID)) {
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
    public void onPurchasesUpdated(
            BillingResult billingResult,
            List<Purchase> purchases) {
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

        if (!purchase.isAcknowledged()
                && billingClient != null
                && billingClient.isReady()) {
            AcknowledgePurchaseParams params =
                    AcknowledgePurchaseParams.newBuilder()
                            .setPurchaseToken(purchase.getPurchaseToken())
                            .build();
            billingClient.acknowledgePurchase(
                    params,
                    new AcknowledgePurchaseResponseListener() {
                        @Override
                        public void onAcknowledgePurchaseResponse(
                                BillingResult billingResult) {
                            if (billingResult.getResponseCode()
                                    != BillingClient.BillingResponseCode.OK) {
                                Log.w(TAG, "Acknowledge failed: "
                                        + billingResult.getDebugMessage());
                            }
                        }
                    });
        }
        return true;
    }

    private boolean isLegacyProNoAdsActive() {
        return preferences.getBoolean(PREF_PRO_NO_ADS, false);
    }

    private boolean isProSubscriptionActive() {
        return preferences.getBoolean(PREF_PRO_SUBSCRIPTION, false);
    }

    private void setProNoAdsActive(boolean active) {
        preferences.edit().putBoolean(PREF_PRO_NO_ADS, active).apply();
        noAdsStatusChanged.run();
    }

    private void setProSubscriptionActive(boolean active) {
        preferences.edit().putBoolean(PREF_PRO_SUBSCRIPTION, active).apply();
        noAdsStatusChanged.run();
    }

    private void setModuleValvesOwned(boolean owned) {
        preferences.edit().putBoolean(PREF_MODULE_VALVES, owned).apply();
    }

    void onResume() {
        if (billingClient != null && billingClient.isReady()) {
            queryOwnedPurchases();
        } else {
            if (billingClient == null) {
                initialize();
            } else {
                startConnection();
            }
        }
    }

    void onDestroy() {
        if (billingClient != null) {
            billingClient.endConnection();
            billingClient = null;
        }
    }
}

package pl.smilczarek.refrigerationcalc;

import android.app.Activity;
import android.util.Log;

import com.google.android.ump.ConsentDebugSettings;
import com.google.android.ump.ConsentForm;
import com.google.android.ump.ConsentInformation;
import com.google.android.ump.ConsentRequestParameters;
import com.google.android.ump.FormError;
import com.google.android.ump.UserMessagingPlatform;

/** Owns the Google UMP consent flow used before advertising is initialized. */
final class PrivacyConsentService {
    private static final String TAG = "RefrigerationCalc";

    private final Activity activity;
    private final boolean debugBuild;
    private final Runnable adsInitializer;

    private ConsentInformation consentInformation;

    PrivacyConsentService(Activity activity, boolean debugBuild, Runnable adsInitializer) {
        this.activity = activity;
        this.debugBuild = debugBuild;
        this.adsInitializer = adsInitializer;
    }

    /** Requests current consent information and displays the required form. */
    void requestConsent() {
        ConsentRequestParameters.Builder paramsBuilder =
                new ConsentRequestParameters.Builder();
        if (debugBuild) {
            ConsentDebugSettings debugSettings = new ConsentDebugSettings.Builder(activity)
                    .setDebugGeography(
                            ConsentDebugSettings.DebugGeography.DEBUG_GEOGRAPHY_EEA)
                    .build();
            paramsBuilder.setConsentDebugSettings(debugSettings);
        }
        ConsentRequestParameters params = paramsBuilder.build();

        consentInformation = UserMessagingPlatform.getConsentInformation(activity);
        consentInformation.requestConsentInfoUpdate(
                activity,
                params,
                new ConsentInformation.OnConsentInfoUpdateSuccessListener() {
                    @Override
                    public void onConsentInfoUpdateSuccess() {
                        UserMessagingPlatform.loadAndShowConsentFormIfRequired(
                                activity,
                                new ConsentForm.OnConsentFormDismissedListener() {
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
                        maybeInitializeAdsAfterConsent();
                    }
                });
    }

    private void maybeInitializeAdsAfterConsent() {
        if (consentInformation == null || !consentInformation.canRequestAds()) {
            Log.i(TAG, "Ads not requested: consent not granted / not available.");
            return;
        }
        adsInitializer.run();
    }

    boolean isPrivacyOptionsRequired() {
        return consentInformation != null
                && consentInformation.getPrivacyOptionsRequirementStatus()
                == ConsentInformation.PrivacyOptionsRequirementStatus.REQUIRED;
    }

    void showPrivacyOptionsForm() {
        activity.runOnUiThread(new Runnable() {
            @Override
            public void run() {
                UserMessagingPlatform.showPrivacyOptionsForm(
                        activity,
                        new ConsentForm.OnConsentFormDismissedListener() {
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
}

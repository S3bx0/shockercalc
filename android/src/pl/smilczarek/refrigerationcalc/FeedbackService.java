package pl.smilczarek.refrigerationcalc;

import android.app.Activity;
import android.content.ActivityNotFoundException;
import android.content.Intent;
import android.net.Uri;
import android.util.Log;

/** Opens user-controlled feedback destinations without sending anything itself. */
final class FeedbackService {
    private static final String TAG = "RefrigerationCalc";

    private final Activity activity;

    FeedbackService(Activity activity) {
        this.activity = activity;
    }

    void openEmail(
            final String recipient,
            final String subject,
            final String body) {
        activity.runOnUiThread(new Runnable() {
            @Override
            public void run() {
                try {
                    Intent intent = new Intent(Intent.ACTION_SENDTO);
                    intent.setData(buildMailtoUri(recipient, subject, body));
                    activity.startActivity(intent);
                } catch (ActivityNotFoundException noEmailApp) {
                    openShareFallback(recipient, subject, body);
                } catch (Exception error) {
                    Log.e(TAG, "openFeedbackEmail nie powiodlo sie", error);
                }
            }
        });
    }

    /**
     * Opens this application's Google Play details page. A tester who joined a
     * test can voluntarily select Google Play's private-feedback option there.
     */
    void openGooglePlayListing(final String packageName) {
        activity.runOnUiThread(new Runnable() {
            @Override
            public void run() {
                String safePackage = packageName != null ? packageName.trim() : "";
                if (safePackage.isEmpty()) {
                    Log.w(TAG, "Brak pakietu aplikacji dla Google Play");
                    return;
                }
                try {
                    Intent intent = new Intent(
                            Intent.ACTION_VIEW,
                            Uri.parse("market://details?id=" + Uri.encode(safePackage)));
                    intent.setPackage("com.android.vending");
                    activity.startActivity(intent);
                } catch (ActivityNotFoundException noPlayStore) {
                    openGooglePlayWebFallback(safePackage);
                } catch (Exception error) {
                    Log.e(TAG, "openGooglePlayListing nie powiodlo sie", error);
                }
            }
        });
    }

    private Uri buildMailtoUri(String recipient, String subject, String body) {
        String safeRecipient = recipient != null ? recipient : "";
        String safeSubject = subject != null ? subject : "";
        String safeBody = body != null ? body : "";
        return Uri.parse(
                "mailto:" + Uri.encode(safeRecipient)
                        + "?subject=" + Uri.encode(safeSubject)
                        + "&body=" + Uri.encode(safeBody));
    }

    private void openShareFallback(
            String recipient,
            String subject,
            String body) {
        try {
            Intent fallback = new Intent(Intent.ACTION_SEND);
            fallback.setType("message/rfc822");
            fallback.putExtra(Intent.EXTRA_EMAIL, new String[] {recipient});
            fallback.putExtra(Intent.EXTRA_SUBJECT, subject);
            fallback.putExtra(Intent.EXTRA_TEXT, body);
            activity.startActivity(Intent.createChooser(fallback, subject));
        } catch (Exception error) {
            Log.e(TAG, "Brak aplikacji do wyslania opinii", error);
        }
    }

    private void openGooglePlayWebFallback(String packageName) {
        try {
            Intent fallback = new Intent(
                    Intent.ACTION_VIEW,
                    Uri.parse(
                            "https://play.google.com/store/apps/details?id="
                                    + Uri.encode(packageName)));
            activity.startActivity(fallback);
        } catch (Exception error) {
            Log.e(TAG, "Brak Google Play dla opinii testowej", error);
        }
    }
}

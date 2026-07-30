package pl.smilczarek.refrigerationcalc;

import android.app.Activity;
import android.content.ActivityNotFoundException;
import android.content.Intent;
import android.net.Uri;
import android.util.Log;

/** Opens a user-editable feedback draft without sending anything itself. */
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
}

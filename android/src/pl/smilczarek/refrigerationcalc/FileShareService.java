package pl.smilczarek.refrigerationcalc;

import android.app.Activity;
import android.content.ContentResolver;
import android.content.ContentValues;
import android.content.Intent;
import android.net.Uri;
import android.os.Build;
import android.os.Environment;
import android.os.StrictMode;
import android.provider.MediaStore;
import android.util.Log;

import java.io.File;
import java.io.FileInputStream;
import java.io.InputStream;
import java.io.OutputStream;

/** Owns Android file export and Sharesheet integration. */
final class FileShareService {
    private static final String TAG = "RefrigerationCalc";

    private final Activity activity;

    FileShareService(Activity activity) {
        this.activity = activity;
    }

    void shareFile(
            final String path,
            final String mimeType,
            final String subject,
            final String text) {
        activity.runOnUiThread(new Runnable() {
            @Override
            public void run() {
                try {
                    File file = new File(path);
                    if (!file.exists()) {
                        Log.w(TAG, "shareFile: plik nie istnieje " + path);
                        return;
                    }

                    Uri uri = null;
                    // Android 10+ (API 29): kopiujemy plik do publicznego
                    // MediaStore (Pobrane) i udostępniamy content:// URI.
                    if (Build.VERSION.SDK_INT >= 29) {
                        uri = exportToDownloads(file, mimeType);
                    }
                    if (uri == null) {
                        // Fallback dla starszych Androidow: file:// + StrictMode.
                        StrictMode.setVmPolicy(
                                new StrictMode.VmPolicy.Builder().build());
                        uri = Uri.fromFile(file);
                    }

                    Intent intent = new Intent(Intent.ACTION_SEND);
                    intent.setType(
                            mimeType != null
                                    ? mimeType
                                    : "application/octet-stream");
                    intent.putExtra(Intent.EXTRA_STREAM, uri);
                    if (subject != null) {
                        intent.putExtra(Intent.EXTRA_SUBJECT, subject);
                    }
                    if (text != null) {
                        intent.putExtra(Intent.EXTRA_TEXT, text);
                    }
                    intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
                    activity.startActivity(Intent.createChooser(intent, subject));
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
            ContentResolver resolver = activity.getContentResolver();
            ContentValues values = new ContentValues();
            values.put(MediaStore.Downloads.DISPLAY_NAME, file.getName());
            values.put(
                    MediaStore.Downloads.MIME_TYPE,
                    mimeType != null ? mimeType : "application/pdf");
            values.put(
                    MediaStore.Downloads.RELATIVE_PATH,
                    Environment.DIRECTORY_DOWNLOADS);
            values.put(MediaStore.Downloads.IS_PENDING, 1);

            Uri item = resolver.insert(
                    MediaStore.Downloads.EXTERNAL_CONTENT_URI,
                    values);
            if (item == null) {
                return null;
            }
            OutputStream output = null;
            InputStream input = null;
            try {
                output = resolver.openOutputStream(item);
                input = new FileInputStream(file);
                byte[] buffer = new byte[8192];
                int count;
                while ((count = input.read(buffer)) > 0) {
                    output.write(buffer, 0, count);
                }
            } finally {
                if (input != null) {
                    try {
                        input.close();
                    } catch (Exception ignored) {
                        // Best-effort cleanup.
                    }
                }
                if (output != null) {
                    try {
                        output.close();
                    } catch (Exception ignored) {
                        // Best-effort cleanup.
                    }
                }
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
}

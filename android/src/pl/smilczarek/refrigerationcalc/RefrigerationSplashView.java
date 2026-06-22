package pl.smilczarek.refrigerationcalc;

import android.animation.ValueAnimator;
import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.ImageDecoder;
import android.graphics.Movie;
import android.graphics.drawable.Animatable2;
import android.graphics.drawable.AnimatedImageDrawable;
import android.graphics.drawable.Drawable;
import android.os.Build;
import android.os.SystemClock;
import android.util.Log;
import android.widget.ImageView;

import java.io.IOException;
import java.io.InputStream;

/** Plays the approved Refrigeration Calc intro without redrawing its geometry. */
final class RefrigerationSplashView extends ImageView {
    static final long ANIMATION_DURATION_MS = 4900L;

    private static final String TAG = "RefrigerationSplash";
    private static final long COMPLETION_GRACE_MS = 700L;

    private AnimatedImageDrawable animatedDrawable;
    private Animatable2.AnimationCallback animationCallback;
    private Movie fallbackMovie;
    private long fallbackStartedAtMs;
    private Runnable onFinished;
    private boolean finished;
    private final Runnable completionRunnable = this::finishOnce;

    RefrigerationSplashView(Context context) {
        super(context);
        setBackgroundColor(Color.WHITE);
        setScaleType(ScaleType.FIT_CENTER);
        setAdjustViewBounds(false);
        setClickable(true);
        loadApprovedAnimation();
    }

    private void loadApprovedAnimation() {
        final int resourceId = getResources().getIdentifier(
                "refrigeration_intro", "raw", getContext().getPackageName());
        if (resourceId == 0) {
            Log.e(TAG, "Approved intro resource is missing.");
            return;
        }

        if (Build.VERSION.SDK_INT >= 28) {
            try {
                final ImageDecoder.Source source = ImageDecoder.createSource(
                        getResources(), resourceId);
                final Drawable drawable = ImageDecoder.decodeDrawable(source);
                if (drawable instanceof AnimatedImageDrawable) {
                    animatedDrawable = (AnimatedImageDrawable) drawable;
                    animatedDrawable.setRepeatCount(0);
                    setImageDrawable(animatedDrawable);
                    return;
                }
            } catch (IOException | RuntimeException exc) {
                Log.w(TAG, "Native animated image decoder unavailable", exc);
            }
        }

        try (InputStream stream = getResources().openRawResource(resourceId)) {
            fallbackMovie = Movie.decodeStream(stream);
        } catch (IOException | RuntimeException exc) {
            Log.e(TAG, "Unable to decode approved intro animation", exc);
        }
    }

    void start(Runnable completion) {
        stopPlayback();
        onFinished = completion;
        finished = false;

        if (Build.VERSION.SDK_INT >= 26 && !ValueAnimator.areAnimatorsEnabled()) {
            postDelayed(completionRunnable, 360L);
            return;
        }

        if (Build.VERSION.SDK_INT >= 28 && animatedDrawable != null) {
            animationCallback = new Animatable2.AnimationCallback() {
                @Override
                public void onAnimationEnd(Drawable drawable) {
                    finishOnce();
                }
            };
            animatedDrawable.registerAnimationCallback(animationCallback);
            animatedDrawable.start();
            postDelayed(completionRunnable, ANIMATION_DURATION_MS + COMPLETION_GRACE_MS);
            return;
        }

        if (fallbackMovie != null) {
            fallbackStartedAtMs = SystemClock.uptimeMillis();
            postInvalidateOnAnimation();
            postDelayed(completionRunnable, ANIMATION_DURATION_MS);
            return;
        }

        postDelayed(completionRunnable, 360L);
    }

    void stop() {
        stopPlayback();
        finished = true;
        onFinished = null;
    }

    private void stopPlayback() {
        removeCallbacks(completionRunnable);
        if (Build.VERSION.SDK_INT >= 28 && animatedDrawable != null) {
            if (animationCallback != null) {
                animatedDrawable.unregisterAnimationCallback(animationCallback);
                animationCallback = null;
            }
            animatedDrawable.stop();
        }
        fallbackStartedAtMs = 0L;
    }

    private void finishOnce() {
        if (finished) {
            return;
        }
        finished = true;
        stopPlayback();
        final Runnable completion = onFinished;
        onFinished = null;
        if (completion != null) {
            completion.run();
        }
    }

    @Override
    protected void onDraw(Canvas canvas) {
        super.onDraw(canvas);
        if (animatedDrawable != null || fallbackMovie == null || fallbackStartedAtMs == 0L) {
            return;
        }

        final int movieWidth = fallbackMovie.width();
        final int movieHeight = fallbackMovie.height();
        if (movieWidth <= 0 || movieHeight <= 0) {
            return;
        }

        final long elapsed = Math.max(0L, SystemClock.uptimeMillis() - fallbackStartedAtMs);
        fallbackMovie.setTime((int) Math.min(elapsed, ANIMATION_DURATION_MS - 1L));

        final float scale = Math.min(
                getWidth() / (float) movieWidth,
                getHeight() / (float) movieHeight);
        final float left = (getWidth() - movieWidth * scale) * 0.5f;
        final float top = (getHeight() - movieHeight * scale) * 0.5f;
        canvas.save();
        canvas.translate(left, top);
        canvas.scale(scale, scale);
        fallbackMovie.draw(canvas, 0f, 0f);
        canvas.restore();

        if (!finished && elapsed < ANIMATION_DURATION_MS) {
            postInvalidateOnAnimation();
        }
    }

    @Override
    protected void onDetachedFromWindow() {
        stop();
        super.onDetachedFromWindow();
    }
}

package pl.smilczarek.refrigerationcalc;

import android.animation.Animator;
import android.animation.AnimatorListenerAdapter;
import android.animation.ValueAnimator;
import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.LinearGradient;
import android.graphics.Paint;
import android.graphics.Shader;
import android.graphics.Typeface;
import android.view.View;
import android.view.animation.AccelerateDecelerateInterpolator;

/** Lightweight splash animation with no Lottie or bitmap dependency. */
final class RefrigerationSplashView extends View {
    static final long ANIMATION_DURATION_MS = 1800L;

    private static final int PARTICLE_COUNT = 34;
    private final Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final float density;
    private final float[] particleAngles = new float[PARTICLE_COUNT];
    private final float[] particleRadii = new float[PARTICLE_COUNT];
    private final float[] particleSizes = new float[PARTICLE_COUNT];
    private ValueAnimator animator;
    private float progress;

    RefrigerationSplashView(Context context) {
        super(context);
        density = getResources().getDisplayMetrics().density;
        setLayerType(View.LAYER_TYPE_HARDWARE, null);
        for (int i = 0; i < PARTICLE_COUNT; i++) {
            particleAngles[i] = (float) ((i * 2.39996323) % (Math.PI * 2.0));
            particleRadii[i] = 0.34f + ((i * 37) % 61) / 100f;
            particleSizes[i] = dp(1.0f + ((i * 17) % 10) / 8f);
        }
    }

    void start(Runnable onFinished) {
        stop();
        animator = ValueAnimator.ofFloat(0f, 1f);
        animator.setDuration(ANIMATION_DURATION_MS);
        animator.setInterpolator(new AccelerateDecelerateInterpolator());
        animator.addUpdateListener(animation -> {
            progress = (float) animation.getAnimatedValue();
            invalidate();
        });
        animator.addListener(new AnimatorListenerAdapter() {
            @Override
            public void onAnimationEnd(Animator animation) {
                if (onFinished != null) {
                    onFinished.run();
                }
            }
        });
        animator.start();
    }

    void stop() {
        if (animator != null) {
            animator.removeAllListeners();
            animator.cancel();
            animator = null;
        }
    }

    @Override
    protected void onDetachedFromWindow() {
        stop();
        super.onDetachedFromWindow();
    }

    @Override
    protected void onDraw(Canvas canvas) {
        super.onDraw(canvas);
        final float width = getWidth();
        final float height = getHeight();
        if (width <= 0 || height <= 0) {
            return;
        }

        drawBackground(canvas, width, height);

        final float shortest = Math.min(width, height);
        final float centerX = width * 0.5f;
        final float centerY = height * (height < width ? 0.40f : 0.42f);
        final float radius = Math.min(shortest * 0.17f, dp(92));
        final float eased = easeOutCubic(Math.min(1f, progress / 0.72f));

        drawParticles(canvas, centerX, centerY, radius, progress);
        drawFrostTrail(canvas, centerX, centerY, radius, progress);

        canvas.save();
        canvas.rotate(-16f + 16f * eased, centerX, centerY);
        canvas.scale(0.68f + 0.32f * eased, 0.68f + 0.32f * eased, centerX, centerY);
        drawSnowflake(canvas, centerX, centerY, radius, eased);
        canvas.restore();

        drawBrand(canvas, width, height, centerY, radius, progress);
        drawProgress(canvas, width, height, progress);
    }

    private void drawBackground(Canvas canvas, float width, float height) {
        paint.setShader(new LinearGradient(
                0f,
                0f,
                0f,
                height,
                Color.rgb(3, 20, 39),
                Color.rgb(5, 45, 78),
                Shader.TileMode.CLAMP));
        canvas.drawRect(0f, 0f, width, height, paint);
        paint.setShader(null);
    }

    private void drawSnowflake(Canvas canvas, float cx, float cy, float radius, float alpha) {
        paint.setStyle(Paint.Style.STROKE);
        paint.setStrokeCap(Paint.Cap.ROUND);
        paint.setStrokeJoin(Paint.Join.ROUND);
        paint.setStrokeWidth(Math.max(dp(3), radius * 0.052f));
        paint.setColor(Color.rgb(139, 218, 255));
        paint.setAlpha((int) (255 * alpha));

        for (int arm = 0; arm < 6; arm++) {
            double angle = Math.PI * arm / 3.0 - Math.PI / 2.0;
            float endX = cx + (float) Math.cos(angle) * radius;
            float endY = cy + (float) Math.sin(angle) * radius;
            canvas.drawLine(cx, cy, endX, endY, paint);

            for (float fraction : new float[] {0.58f, 0.80f}) {
                float branchX = cx + (float) Math.cos(angle) * radius * fraction;
                float branchY = cy + (float) Math.sin(angle) * radius * fraction;
                float branchLength = radius * 0.22f;
                for (float side : new float[] {-1f, 1f}) {
                    double branchAngle = angle + Math.PI + side * Math.PI / 4.2;
                    float tipX = branchX + (float) Math.cos(branchAngle) * branchLength;
                    float tipY = branchY + (float) Math.sin(branchAngle) * branchLength;
                    canvas.drawLine(branchX, branchY, tipX, tipY, paint);
                }
            }
        }

        paint.setStyle(Paint.Style.FILL);
        paint.setColor(Color.rgb(222, 247, 255));
        canvas.drawCircle(cx, cy, Math.max(dp(3), radius * 0.055f), paint);
    }

    private void drawParticles(Canvas canvas, float cx, float cy, float radius, float t) {
        paint.setStyle(Paint.Style.FILL);
        for (int i = 0; i < PARTICLE_COUNT; i++) {
            float local = clamp((t * 1.45f) - (i % 7) * 0.035f);
            float angle = particleAngles[i] + t * (1.2f + (i % 5) * 0.11f);
            float distance = radius * (0.9f + particleRadii[i] * 1.45f);
            float x = cx + (float) Math.cos(angle) * distance;
            float y = cy + (float) Math.sin(angle) * distance * 0.82f;
            float pulse = 0.45f + 0.55f * (float) Math.sin(t * 11f + i);
            paint.setColor(i % 4 == 0 ? Color.rgb(207, 245, 255) : Color.rgb(72, 181, 235));
            paint.setAlpha((int) (190 * local * Math.max(0.18f, pulse)));
            canvas.drawCircle(x, y, particleSizes[i], paint);
        }
    }

    private void drawFrostTrail(Canvas canvas, float cx, float cy, float radius, float t) {
        paint.setStyle(Paint.Style.FILL);
        final int points = 28;
        for (int i = 0; i < points; i++) {
            float fraction = i / (float) (points - 1);
            float reveal = clamp(t * 1.45f - fraction * 0.64f);
            double angle = -2.55 + fraction * 4.5 + t * 0.48;
            float distance = radius * (1.12f + fraction * 0.82f);
            float x = cx + (float) Math.cos(angle) * distance;
            float y = cy + (float) Math.sin(angle) * distance * 0.55f;
            paint.setColor(Color.rgb(112, 216, 255));
            paint.setAlpha((int) (150 * reveal * (1f - fraction * 0.55f)));
            canvas.drawCircle(x, y, dp(0.8f + (i % 3) * 0.45f), paint);
        }
    }

    private void drawBrand(
            Canvas canvas,
            float width,
            float height,
            float snowY,
            float snowRadius,
            float t) {
        float alpha = clamp((t - 0.48f) / 0.30f);
        float titleY = Math.min(height * 0.69f, snowY + snowRadius + dp(82));

        paint.setStyle(Paint.Style.FILL);
        paint.setTextAlign(Paint.Align.CENTER);
        paint.setTypeface(Typeface.create("sans-serif-medium", Typeface.NORMAL));
        paint.setTextSize(Math.min(dp(30), width * 0.073f));
        paint.setColor(Color.WHITE);
        paint.setAlpha((int) (255 * alpha));
        canvas.drawText("Refrigeration Calc", width * 0.5f, titleY, paint);

        paint.setTypeface(Typeface.create("sans-serif", Typeface.NORMAL));
        paint.setTextSize(Math.min(dp(14), width * 0.036f));
        paint.setColor(Color.rgb(184, 215, 232));
        paint.setAlpha((int) (230 * alpha));
        canvas.drawText("Cold calculations, clear results.", width * 0.5f, titleY + dp(30), paint);
    }

    private void drawProgress(Canvas canvas, float width, float height, float t) {
        float barWidth = Math.min(dp(96), width * 0.28f);
        float left = (width - barWidth) * 0.5f;
        float top = height - Math.max(dp(48), height * 0.07f);
        paint.setStyle(Paint.Style.STROKE);
        paint.setStrokeCap(Paint.Cap.ROUND);
        paint.setStrokeWidth(dp(2));
        paint.setColor(Color.rgb(39, 92, 128));
        paint.setAlpha(220);
        canvas.drawLine(left, top, left + barWidth, top, paint);
        paint.setColor(Color.rgb(107, 215, 255));
        canvas.drawLine(left, top, left + barWidth * clamp(t), top, paint);
    }

    private float dp(float value) {
        return value * density;
    }

    private static float clamp(float value) {
        return Math.max(0f, Math.min(1f, value));
    }

    private static float easeOutCubic(float value) {
        float inverse = 1f - clamp(value);
        return 1f - inverse * inverse * inverse;
    }
}

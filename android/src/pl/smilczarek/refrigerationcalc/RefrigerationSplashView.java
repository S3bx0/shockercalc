package pl.smilczarek.refrigerationcalc;

import android.animation.Animator;
import android.animation.AnimatorListenerAdapter;
import android.animation.ValueAnimator;
import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.LinearGradient;
import android.graphics.Paint;
import android.graphics.Path;
import android.graphics.PathMeasure;
import android.graphics.RadialGradient;
import android.graphics.RectF;
import android.graphics.Shader;
import android.graphics.Typeface;
import android.os.Build;
import android.view.View;
import android.view.animation.LinearInterpolator;

/** Lightweight native animation of the approved Refrigeration Calc emblem. */
final class RefrigerationSplashView extends View {
    static final long ANIMATION_DURATION_MS = 4600L;

    private static final int POLYGON_SIDES = 8;
    private static final int RADIAL_PARTICLE_COUNT = 22;
    private static final int[] ORBIT_COLORS = {
        Color.rgb(180, 229, 250),
        Color.rgb(22, 169, 181),
        Color.rgb(39, 137, 232)
    };
    private static final float[] ORBIT_ROTATIONS = {-12f, 3f, 18f};
    private static final float[] ORBIT_OFFSET_X = {-0.08f, 0.065f, 0.06f};
    private static final float[] ORBIT_OFFSET_Y = {-0.08f, -0.02f, 0.08f};
    private static final float[] RADIAL_ANGLES = {
        -73f, -55f, -41f, -26f, -12f, 4f, 19f, 33f, 49f, 68f, 86f,
        107f, 126f, 145f, 161f, 177f, 195f, 214f, 233f, 252f, 278f, 315f
    };
    private static final float[] RADIAL_SPEEDS = {
        0.82f, 1.04f, 0.91f, 1.22f, 0.76f, 1.14f, 0.88f, 1.29f, 0.97f,
        1.08f, 0.79f, 1.18f, 0.93f, 1.25f, 0.85f, 1.12f, 0.74f, 1.31f,
        1.01f, 0.89f, 1.16f, 0.95f
    };
    private static final float[] RADIAL_PHASES = {
        0.03f, 0.47f, 0.81f, 0.24f, 0.66f, 0.12f, 0.91f, 0.36f, 0.58f,
        0.75f, 0.18f, 0.69f, 0.42f, 0.87f, 0.07f, 0.53f, 0.96f, 0.30f,
        0.63f, 0.15f, 0.78f, 0.40f
    };
    private static final float[] RADIAL_SIZE_FACTORS = {
        0.86f, 1.12f, 0.94f, 1.24f, 0.82f, 1.04f, 0.91f, 1.18f, 0.88f,
        1.09f, 0.79f, 1.20f, 0.97f, 1.15f, 0.84f, 1.06f, 0.76f, 1.22f,
        1.01f, 0.90f, 1.17f, 0.95f
    };
    private static final float[] ORBIT_SPEEDS = {1.93f, 2.21f, 2.49f};

    private final Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final float density;
    private ValueAnimator animator;
    private float progress;

    RefrigerationSplashView(Context context) {
        super(context);
        density = getResources().getDisplayMetrics().density;
        setLayerType(View.LAYER_TYPE_HARDWARE, null);
    }

    void start(Runnable onFinished) {
        stop();
        if (Build.VERSION.SDK_INT >= 26 && !ValueAnimator.areAnimatorsEnabled()) {
            progress = 1f;
            invalidate();
            if (onFinished != null) {
                postDelayed(onFinished, 360L);
            }
            return;
        }
        animator = ValueAnimator.ofFloat(0f, 1f);
        animator.setDuration(ANIMATION_DURATION_MS);
        animator.setInterpolator(new LinearInterpolator());
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
        if (width <= 0f || height <= 0f) {
            return;
        }

        drawBackground(canvas, width, height);

        final float shortest = Math.min(width, height);
        final float centerX = width * 0.5f;
        final float centerY = height * (height < width ? 0.50f : 0.44f);
        final float badgeRadius = Math.min(shortest * 0.34f, dp(188));
        final float innerRadius = badgeRadius * 0.42f;
        final float orbitRadius = badgeRadius * 1.25f;
        final float reveal = easeOutCubic(clamp(progress / 0.18f));
        final float logoScale = 0.80f + 0.20f * reveal;

        canvas.save();
        canvas.scale(logoScale, logoScale, centerX, centerY);
        drawOuterLayers(canvas, centerX, centerY, orbitRadius, badgeRadius, progress);
        drawBadge(canvas, centerX, centerY, badgeRadius, reveal);
        drawRadialSnowflakes(
                canvas, centerX, centerY, innerRadius, badgeRadius, progress, reveal);
        drawInnerDisc(canvas, centerX, centerY, innerRadius, reveal);
        drawSnowflake(canvas, centerX, centerY, innerRadius * 0.70f, reveal);
        drawCurvedBrand(canvas, centerX, centerY, badgeRadius, reveal);
        drawOrbitComets(canvas, centerX, centerY, orbitRadius, badgeRadius, progress);
        canvas.restore();
    }

    private void drawBackground(Canvas canvas, float width, float height) {
        paint.setStyle(Paint.Style.FILL);
        paint.setShader(new LinearGradient(
                0f,
                0f,
                0f,
                height,
                Color.rgb(255, 255, 255),
                Color.rgb(235, 248, 253),
                Shader.TileMode.CLAMP));
        canvas.drawRect(0f, 0f, width, height, paint);
        paint.setShader(null);
    }

    private void drawOuterLayers(
            Canvas canvas,
            float cx,
            float cy,
            float orbitRadius,
            float badgeRadius,
            float t) {
        final float reveal = easeOutCubic(clamp(t / 0.28f));
        final int fillAlpha = (int) (255f * reveal);

        for (int index = 0; index < ORBIT_COLORS.length; index++) {
            final float polygonX = cx + ORBIT_OFFSET_X[index] * badgeRadius;
            final float polygonY = cy + ORBIT_OFFSET_Y[index] * badgeRadius;
            drawPolygon(
                    canvas,
                    polygonX,
                    polygonY,
                    orbitRadius,
                    ORBIT_ROTATIONS[index],
                    ORBIT_COLORS[index],
                    fillAlpha);
        }
    }

    private void drawPolygon(
            Canvas canvas,
            float cx,
            float cy,
            float radius,
            float rotation,
            int color,
            int fillAlpha) {
        final Path path = polygonPath(cx, cy, radius, rotation);
        paint.setShader(null);
        paint.setColor(color);
        paint.setStyle(Paint.Style.FILL);
        paint.setAlpha(fillAlpha);
        canvas.drawPath(path, paint);
    }

    private Path polygonPath(float cx, float cy, float radius, float rotation) {
        final Path path = new Path();
        for (int side = 0; side < POLYGON_SIDES; side++) {
            final double angle = Math.toRadians(rotation + side * 360f / POLYGON_SIDES - 90f);
            final float x = cx + (float) Math.cos(angle) * radius;
            final float y = cy + (float) Math.sin(angle) * radius;
            if (side == 0) {
                path.moveTo(x, y);
            } else {
                path.lineTo(x, y);
            }
        }
        path.close();
        return path;
    }

    private void drawBadge(Canvas canvas, float cx, float cy, float radius, float alpha) {
        paint.setStyle(Paint.Style.FILL);
        paint.setShader(new RadialGradient(
                cx,
                cy - radius * 0.12f,
                radius * 1.15f,
                Color.rgb(5, 33, 68),
                Color.rgb(1, 19, 45),
                Shader.TileMode.CLAMP));
        paint.setAlpha((int) (255f * alpha));
        canvas.drawCircle(cx, cy, radius, paint);
        paint.setShader(null);
    }

    private void drawInnerDisc(Canvas canvas, float cx, float cy, float radius, float alpha) {
        paint.setStyle(Paint.Style.FILL);
        paint.setShader(new RadialGradient(
                cx - radius * 0.24f,
                cy - radius * 0.28f,
                radius * 1.25f,
                Color.rgb(91, 218, 248),
                Color.rgb(14, 169, 225),
                Shader.TileMode.CLAMP));
        paint.setAlpha((int) (255f * alpha));
        canvas.drawCircle(cx, cy, radius, paint);
        paint.setShader(null);
    }

    private void drawSnowflake(Canvas canvas, float cx, float cy, float radius, float alpha) {
        paint.setStyle(Paint.Style.STROKE);
        paint.setStrokeCap(Paint.Cap.ROUND);
        paint.setStrokeJoin(Paint.Join.ROUND);
        paint.setStrokeWidth(Math.max(dp(3f), radius * 0.105f));
        paint.setColor(Color.WHITE);
        paint.setAlpha((int) (255f * alpha));

        for (int arm = 0; arm < 6; arm++) {
            final double angle = Math.PI * arm / 3.0 - Math.PI / 2.0;
            final float endX = cx + (float) Math.cos(angle) * radius;
            final float endY = cy + (float) Math.sin(angle) * radius;
            canvas.drawLine(cx, cy, endX, endY, paint);

            final float branchX = cx + (float) Math.cos(angle) * radius * 0.67f;
            final float branchY = cy + (float) Math.sin(angle) * radius * 0.67f;
            for (float side : new float[] {-1f, 1f}) {
                final double branchAngle = angle + side * Math.PI / 4.0;
                final float branchLength = radius * 0.30f;
                canvas.drawLine(
                        branchX,
                        branchY,
                        branchX + (float) Math.cos(branchAngle) * branchLength,
                        branchY + (float) Math.sin(branchAngle) * branchLength,
                        paint);
            }
        }
    }

    private void drawCurvedBrand(
            Canvas canvas, float cx, float cy, float badgeRadius, float alpha) {
        paint.setStyle(Paint.Style.FILL);
        paint.setTypeface(Typeface.create("sans-serif", Typeface.BOLD));
        paint.setTextAlign(Paint.Align.LEFT);
        paint.setColor(Color.WHITE);
        paint.setAlpha((int) (255f * alpha));

        paint.setTextSize(badgeRadius * 0.135f);
        paint.setLetterSpacing(0.10f);
        drawTextOnArcCentered(
                canvas,
                "REFRIGERATION",
                cx,
                cy,
                badgeRadius * 0.76f,
                204f,
                132f);

        paint.setTextSize(badgeRadius * 0.175f);
        paint.setLetterSpacing(0.16f);
        drawTextOnArcCentered(
                canvas,
                "CALC",
                cx,
                cy,
                badgeRadius * 0.77f,
                152f,
                -124f);

        paint.setLetterSpacing(0f);
        paint.setColor(Color.rgb(92, 215, 247));
        paint.setAlpha((int) (255f * alpha));
        final float dotRadius = badgeRadius * 0.022f;
        canvas.drawCircle(cx - badgeRadius * 0.72f, cy + badgeRadius * 0.30f, dotRadius, paint);
        canvas.drawCircle(cx + badgeRadius * 0.72f, cy + badgeRadius * 0.30f, dotRadius, paint);
    }

    private void drawTextOnArcCentered(
            Canvas canvas,
            String text,
            float cx,
            float cy,
            float radius,
            float startAngle,
            float sweepAngle) {
        final RectF oval = new RectF(cx - radius, cy - radius, cx + radius, cy + radius);
        final Path path = new Path();
        path.addArc(oval, startAngle, sweepAngle);
        final float pathLength = new PathMeasure(path, false).getLength();
        final float offset = Math.max(0f, (pathLength - paint.measureText(text)) * 0.5f);
        canvas.drawTextOnPath(text, path, offset, 0f, paint);
    }

    private void drawRadialSnowflakes(
            Canvas canvas,
            float cx,
            float cy,
            float innerRadius,
            float badgeRadius,
            float t,
            float reveal) {
        for (int index = 0; index < RADIAL_PARTICLE_COUNT; index++) {
            final float local = fractional(
                    t * RADIAL_SPEEDS[index] + RADIAL_PHASES[index]);
            final float depth = local * local * local;
            final float angle = RADIAL_ANGLES[index];
            final double radians = Math.toRadians(angle);
            final float start = innerRadius * 1.12f;
            final float end = badgeRadius * 0.91f;
            final float distance = start + (end - start) * depth;
            final float x = cx + (float) Math.cos(radians) * distance;
            final float y = cy + (float) Math.sin(radians) * distance;
            final float particleRadius = badgeRadius
                    * (0.010f + 0.030f * depth)
                    * RADIAL_SIZE_FACTORS[index];
            final float particleReveal = easeOutCubic(clamp((t - 0.10f) / 0.16f));
            final float visibility = (float) Math.sin(Math.PI * local) * particleReveal;

            drawRadialTail(
                    canvas,
                    x,
                    y,
                    (float) Math.cos(radians),
                    (float) Math.sin(radians),
                    badgeRadius,
                    depth,
                    visibility);
            drawTinySnowflake(canvas, x, y, particleRadius, visibility, Color.rgb(210, 246, 255));
        }
    }

    private void drawRadialTail(
            Canvas canvas,
            float x,
            float y,
            float directionX,
            float directionY,
            float badgeRadius,
            float depth,
            float visibility) {
        final float length = badgeRadius * (0.025f + 0.15f * depth);
        paint.setStrokeCap(Paint.Cap.ROUND);
        for (int point = 1; point <= 5; point++) {
            final float fraction = point / 5f;
            paint.setStyle(Paint.Style.FILL);
            paint.setColor(Color.rgb(76, 199, 244));
            paint.setAlpha((int) (145f * visibility * (1f - fraction)));
            final float pointX = x - directionX * length * fraction;
            final float pointY = y - directionY * length * fraction;
            canvas.drawCircle(pointX, pointY, Math.max(dp(0.7f), length * 0.018f), paint);
        }
    }

    private void drawOrbitComets(
            Canvas canvas,
            float cx,
            float cy,
            float orbitRadius,
            float badgeRadius,
            float t) {
        final float cometReveal = easeOutCubic(clamp((t - 0.14f) / 0.18f));
        if (cometReveal <= 0f) {
            return;
        }
        for (int orbit = 0; orbit < ORBIT_COLORS.length; orbit++) {
            final float polygonX = cx + ORBIT_OFFSET_X[orbit] * badgeRadius;
            final float polygonY = cy + ORBIT_OFFSET_Y[orbit] * badgeRadius;
            final float phase = fractional(t * ORBIT_SPEEDS[orbit] + orbit * 0.31f);
            final float[] point = new float[2];

            for (int trail = 7; trail >= 1; trail--) {
                pointOnPolygon(
                        polygonX,
                        polygonY,
                        orbitRadius,
                        ORBIT_ROTATIONS[orbit],
                        fractional(phase - trail * 0.012f),
                        point);
                paint.setStyle(Paint.Style.FILL);
                paint.setColor(Color.rgb(199, 245, 255));
                paint.setAlpha((int) (115f * cometReveal * (1f - trail / 8f)));
                canvas.drawCircle(point[0], point[1], badgeRadius * 0.010f, paint);
            }

            pointOnPolygon(
                    polygonX,
                    polygonY,
                    orbitRadius,
                    ORBIT_ROTATIONS[orbit],
                    phase,
                    point);
            drawTinySnowflake(
                    canvas,
                    point[0],
                    point[1],
                    badgeRadius * 0.040f,
                    cometReveal,
                    Color.WHITE);
        }
    }

    private void pointOnPolygon(
            float cx,
            float cy,
            float radius,
            float rotation,
            float phase,
            float[] output) {
        final float position = phase * POLYGON_SIDES;
        final int side = Math.min(POLYGON_SIDES - 1, (int) Math.floor(position));
        final float sideProgress = position - side;
        final double angleA = Math.toRadians(rotation + side * 360f / POLYGON_SIDES - 90f);
        final double angleB = Math.toRadians(
                rotation + ((side + 1) % POLYGON_SIDES) * 360f / POLYGON_SIDES - 90f);
        final float ax = cx + (float) Math.cos(angleA) * radius;
        final float ay = cy + (float) Math.sin(angleA) * radius;
        final float bx = cx + (float) Math.cos(angleB) * radius;
        final float by = cy + (float) Math.sin(angleB) * radius;
        output[0] = ax + (bx - ax) * sideProgress;
        output[1] = ay + (by - ay) * sideProgress;
    }

    private void drawTinySnowflake(
            Canvas canvas, float cx, float cy, float radius, float alpha, int color) {
        paint.setStyle(Paint.Style.STROKE);
        paint.setStrokeCap(Paint.Cap.ROUND);
        paint.setStrokeWidth(Math.max(dp(0.8f), radius * 0.22f));
        paint.setColor(color);
        paint.setAlpha((int) (255f * clamp(alpha)));
        for (int arm = 0; arm < 3; arm++) {
            final double angle = Math.toRadians(arm * 60f);
            final float dx = (float) Math.cos(angle) * radius;
            final float dy = (float) Math.sin(angle) * radius;
            canvas.drawLine(cx - dx, cy - dy, cx + dx, cy + dy, paint);
        }
    }

    private float dp(float value) {
        return value * density;
    }

    private static float fractional(float value) {
        return value - (float) Math.floor(value);
    }

    private static float clamp(float value) {
        return Math.max(0f, Math.min(1f, value));
    }

    private static float easeOutCubic(float value) {
        final float inverse = 1f - clamp(value);
        return 1f - inverse * inverse * inverse;
    }

}

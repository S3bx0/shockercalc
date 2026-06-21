# Refrigeration Calc - brand and motion specification

Status: the simplified v2 design direction is approved. New variants must keep
its hierarchy and may refine only geometry, spacing and rendering quality. The
production icon is not replaced until it passes the small-size and adaptive-mask
checks.

## Static emblem

- Canonical approved reference: `assets/brand/approved-emblem-reference.png`.
- Production assets are generated directly from this raster reference. No
  approximate SVG substitute is used for the launcher or Play Store icon.
- The central mark is a simple six-arm snowflake inside a small cyan circle.
- The large midnight-navy circle carries `REFRIGERATION` on the upper arc and
  `CALC` on the lower arc.
- Exactly three broad, rounded 8-sided shapes sit behind the large circle.
  They use light ice, turquoise and blue, with different rotations matching
  the approved v2 concept.
- Comets, trails and radial particles belong to motion, not the static mark.
- The launcher icon will omit curved text if the 48 px readability test fails.

## Proportions

The badge needs a deliberately wide motion annulus, similar to the visual
hierarchy of the Android 17 emblem:

- outer badge radius: about 42% of the square canvas;
- inner snowflake-disc radius: 17-19% of the square canvas;
- clear annulus between both circles: at least 22% of the canvas radius;
- curved text baseline: about 31-34% of the canvas radius;
- all critical launcher-icon content stays inside the central 66% safe zone.

The inner disc must not grow until the moving snowflakes have no room. The
annulus is a functional part of the animation, not leftover background.

## Radial snowflake motion

- Particles begin close to the inner circle at 20-30% of their final size.
- Their scale grows continuously with distance and reaches 100% near the outer
  circle. This creates the impression that they fly from depth toward the
  viewer.
- Radial speed accelerates toward the edge; use an ease-in curve rather than a
  constant velocity.
- Comet tails start short and faint, then lengthen with speed. They fade before
  touching the outer circle.
- Use 6-10 visible radial particles at once. Offset their start times and
  angles so they never form a synchronized ring.
- Primary flight lanes avoid the letter shapes. Tiny low-opacity particles may
  pass through the open side sectors of the text annulus.
- Particles disappear at the outer edge without a hard cut or visible reset.

## Outer orbital motion

- Three rounded 8-sided paths sit just outside the large circle.
- Each path has a different rotation and a unique tangency point.
- The filled outer layers keep their approved colors and opacity throughout the
  intro. Orbital paths are never drawn; only the moving snowflakes and their
  fading tails reveal the routes.
- One small snowflake travels along each path at a different phase. The final
  approved orbit speed is 30% lower than the initial preview, keeping the
  comets lively without distracting from the central flight effect.
- Orbital snowflakes keep an almost constant size because they remain on one
  visual depth plane.
- Each leaves a short fading trail; trails never meet at one point or form a
  permanent bright ring.

## Timing and accessibility

- Target duration: 4.0-5.0 seconds; the approved implementation uses 4.6 seconds
  before a clean transition to the main UI.
- Motion must remain smooth on mid-range phones and avoid large bitmap frames.
- Reduced-motion mode shows the static emblem with a short opacity transition.
- The existing lightweight splash remains the fallback until the new version
  passes cold-start and low-memory tests.

## Acceptance checks

- readable and balanced at 512 px, 192 px, 48 px and 32 px;
- no clipping in circle, squircle, rounded-square and teardrop adaptive masks;
- exact spelling of `REFRIGERATION` and `CALC`;
- recognizable as refrigeration/engineering rather than a winter decoration;
- no collision between curved text, radial particles and the central disc;
- animation tested on light/dark system themes and reduced-motion settings.

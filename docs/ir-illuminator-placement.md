# IR illuminator placement

Dark-pupil tracking needs the eye lit in near-IR (around 850nm) with the illuminator positioned **off** the camera's optical axis. Placement is a joint decision with camera aim, not a separate one, and it is the most common cause of a detector that "does not work" when the code is fine.

## Dark pupil vs bright pupil

- **On-axis illumination** (light source next to the lens) retroreflects off the retina and the pupil appears *bright*, the red-eye effect in IR.
- **Off-axis illumination** leaves the pupil the darkest region in the image. This is dark-pupil tracking, and it is what Pupil Core cameras and this pipeline assume.

Keep the illuminator well off the camera axis. If the pupil ever appears brighter than the iris in your feed, the illuminator has crept too close to the lens and the detector's core assumption has inverted.

## Wavelength

850nm is the usual choice: invisible enough not to distract, and within silicon sensor response. 940nm is more fully invisible but sensor sensitivity drops sharply, so you need more power for the same image. Start at 850nm.

The camera needs an IR-pass filter (and no IR-cut filter). Pupil Core eye cameras ship configured for this. If you are substituting another camera, this is the first thing to check: a stock webcam with an IR-cut filter will see almost nothing from an 850nm emitter.

## Safety

Near-IR is invisible, so the blink reflex does not protect the eye. This matters and is worth being deliberate about rather than eyeballing.

- Keep irradiance at the cornea low. Commercial eye trackers operate far below the IEC 62471 exempt-group limits, and there is no reason to run brighter: the detector needs contrast, not brightness.
- Use the lowest power that gives a clean threshold. If the image is noisy, fix it with a longer exposure or a wider aperture before adding illuminator power.
- Diffuse rather than focus. A small intense emitter aimed at the eye is worse than a diffused one at the same total output, both for safety and for glint quality.
- Prefer several low-power emitters over one bright one.
- Do not point an unregulated high-power IR LED at an eye "just for testing". Test against a hand or a printed eye target first, and confirm the image is usable at low power.

If you are unsure whether your setup is within limits, it is, in practice, well within them at the power levels that produce a good dark-pupil image. The risk comes from cranking power to fix a problem that was actually camera aim or exposure.

## The birdbath problem

This is the part specific to VITURE and the reason placement cannot just be copied from an open-frame eye tracker.

Birdbath optics put a partially reflective combiner directly in front of the eye, close in. That combiner is reflective in near-IR and it sits between your illuminator and your camera. Three failure modes follow:

1. **Direct reflection into the camera.** The illuminator's own light bounces off the combiner straight back into the lens, producing a large bright artifact that can swamp the eye entirely.
2. **Ghost glints.** Secondary reflections put extra bright spots on the eye image that a naive glint filter mistakes for real corneal reflections.
3. **Uneven illumination.** The combiner shadows part of the eye, so the pupil is well lit at one gaze angle and poorly lit at another. This one is insidious: detection works at center gaze and fails at the corners, which is exactly where calibration accuracy matters most.

Mitigations, roughly in order of how much they help:

- Illuminate from **below** the combiner, on the same side as the camera, so neither light path crosses the combiner surface at a reflective angle.
- Angle the emitter so its specular reflection off the combiner goes somewhere other than the lens. This is a geometry problem you solve by moving the emitter a few millimeters and watching the feed, not by calculating.
- Shield the emitter so it cannot throw light directly forward. A small printed baffle on the mount does more than any amount of software.
- Check illumination at all nine calibration target positions, not just center. If corner gaze loses the pupil, fix the light before touching the detector.

## Glints and the detector

Corneal glints from the illuminator appear as small bright spots. Under dark-pupil detection they matter in two ways:

- A glint landing **inside** the pupil punches a hole in the threshold blob and biases the centroid toward the glint. Fill contour holes or morphologically close before the ellipse fit. See [gate-2-on-device-detection.md](gate-2-on-device-detection.md).
- A glint landing on the **pupil boundary** distorts the ellipse fit, which is worse, because it moves the centroid without obviously breaking the blob.

Both argue for positioning the emitter so its glint sits on the iris, away from the pupil, across the working range of gaze angles. Since the pupil moves and the glint moves less, there is usually a placement where the glint stays clear.

This project does not use glints for tracking (that is pupil-glint vector tracking, a different technique with its own slippage tradeoffs). Here glints are purely an artifact to be positioned out of the way.

## Practical procedure

1. Get a usable image with ambient IR or a hand-held emitter before committing to a mount position.
2. Move the emitter while watching the live feed. You are looking for: pupil clearly darkest region, glint on the iris not the pupil, no large combiner reflection, and all of that holding as you look at each corner of the display.
3. Only then fix the emitter position in the mount.
4. Re-check after any change to camera angle. The two are coupled; moving one invalidates the tuning of the other.

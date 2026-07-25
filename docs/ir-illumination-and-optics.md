# IR illumination and birdbath optics

**Research correction:** this document originally treated IR illuminator placement as an open design task. It is not. Pupil Core eye cameras ship with **IR illumination integrated into the camera module** ([accessories](https://pupil-labs.com/products/core/accessories)). Aiming the camera aims the light.

That removes a design variable and adds a constraint: you can no longer move the illuminator independently to dodge a reflection. Camera angle is now the only lever, and it has to satisfy illumination geometry, viewing geometry, and combiner-reflection avoidance simultaneously.

If you are building the [DIY variant](https://docs.pupil-labs.com/core/diy/) with modified webcams instead, illuminator placement is back on the table, and the dark-pupil section below applies to your design directly.

## Dark pupil, and why the geometry is fixed

- **On-axis illumination** (light beside the lens) retroreflects off the retina and the pupil appears *bright*: the red-eye effect in IR.
- **Off-axis illumination** leaves the pupil the darkest region in the image. This is dark-pupil tracking, and it is what Pupil Core and this pipeline assume.

Pupil's integrated illuminators are positioned for dark-pupil operation by design, so you get this for free. The thing to verify on your own build is simply that the pupil really is the darkest large region in the live feed, across the full range of gaze angles. If it ever appears brighter than the iris, something is wrong with your geometry and the detector's core assumption has inverted.

## Wavelength

850nm is the usual choice: invisible enough not to distract, within silicon sensor response. 940nm is more fully invisible but sensor sensitivity drops sharply, so it needs more power for the same image.

Pupil Labs do not publish the wavelength of the integrated illuminators; 850nm is the standard for this class of device. The camera has the matching IR-pass filter and no IR-cut filter, which is handled for you on Pupil hardware. On a DIY build this is the first thing to check: a stock webcam with an IR-cut filter still installed will see almost nothing from an 850nm emitter, which is why the DIY guide has you replace that filter with exposed film.

## Safety

Near-IR is invisible, so the blink reflex does not protect the eye. Worth being deliberate about rather than eyeballing.

- Commercial eye trackers, Pupil Core included, operate far below the IEC 62471 exempt-group limits. Using the integrated illuminators as shipped keeps you in that regime.
- On a DIY build: use the lowest power that gives a clean threshold. If the image is noisy, fix it with a longer exposure or a wider aperture before adding illuminator power.
- Diffuse rather than focus. A small intense emitter aimed at the eye is worse than a diffused one at the same total output, both for safety and for glint quality.
- Prefer several low-power emitters over one bright one.
- Do not point an unregulated high-power IR LED at an eye "just for testing". Test against a hand or a printed eye target first.

The risk here comes almost entirely from cranking power to fix a problem that was actually camera aim or exposure.

## The birdbath problem

This is the part specific to VITURE, and the reason placement cannot be copied from an open-frame eye tracker.

Birdbath optics put a partially reflective combiner directly in front of the eye, close in. That combiner is reflective in near-IR, and it sits between the camera's own illuminator and its lens. Three failure modes follow:

1. **Direct reflection into the camera.** The module's illumination bounces off the combiner straight back into its own lens, producing a bright artifact that can swamp the eye. With an integrated illuminator this is the dangerous one, because the light source cannot be moved away from the lens independently.
2. **Ghost glints.** Secondary reflections put extra bright spots on the eye image that a naive filter mistakes for real corneal reflections.
3. **Uneven illumination.** The combiner shadows part of the eye, so the pupil is well lit at one gaze angle and poorly lit at another. Insidious: detection works at center gaze and fails at the corners, which is exactly where calibration accuracy matters most.

Mitigations, in rough order of how much they help:

- Position the camera **below the combiner**, angled up, so neither the outgoing illumination nor the return path crosses the combiner at a reflective angle. This is the same constraint that drives the 30 to 45 degree elevation in the mount.
- Rotate the module a few degrees and watch the feed. Specular reflection is a geometry problem you solve empirically, not by calculation.
- A small printed baffle on the mount, shielding the module from throwing light directly forward, does more than any amount of software.
- Check illumination at all nine calibration target positions, not just center. If corner gaze loses the pupil, fix the light before touching the detector.

## Glints and the detector

Corneal glints appear as small bright spots. Under dark-pupil detection they matter in two ways:

- A glint landing **inside** the pupil punches a hole in the threshold blob and biases the centroid toward the glint. Fill contour holes or morphologically close before the ellipse fit. See [gate-2-on-device-detection.md](gate-2-on-device-detection.md).
- A glint landing on the **pupil boundary** distorts the ellipse fit, which is worse, because it moves the centroid without obviously breaking the blob.

Both argue for a camera angle whose glint sits on the iris, clear of the pupil, across the working range of gaze angles. The pupil moves and the glint moves less, so there is usually an angle where the glint stays clear. At 192x192 there are only about 190 pixels across the whole image, so a glint is a large fraction of the pupil and this matters more than it would on a bigger sensor.

This project does not use glints for tracking (that is pupil-glint vector tracking, a different technique with its own slippage tradeoffs). Here glints are purely an artifact to position out of the way.

## Practical procedure

1. Before committing to a mount position, hold the camera by hand and watch the live feed.
2. Move it around. You are looking for: pupil clearly the darkest region, glint on the iris rather than the pupil, no large combiner reflection, and all of that holding as you look at each corner of the display.
3. If no hand-held position satisfies all four, no printed mount will either, and the geometry needs rethinking before you spend prints on it.
4. Only then fix the position in the mount.
5. Re-check after any change to camera angle. With integrated illumination, camera aim and illumination geometry are the same variable.

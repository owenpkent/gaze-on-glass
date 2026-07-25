# Slippage and drift

The known weakness of the 2D approach, stated plainly, plus what is done about it.

## The problem

A 2D calibration is a fixed function from pupil position in the eye image to position on screen. It is only valid while the geometric relationship between camera and eye holds. If the camera moves relative to the eye after calibration, every mapped coordinate is wrong by a corresponding amount, and **nothing in the pipeline can detect that this happened**. The pupil is still found, confidence is still high, the numbers still look plausible. They are just wrong.

That silence is what makes slippage the serious failure mode. Detection failure is loud and obvious. Slippage is quiet.

## Why this project accepts it

pye3d's 3D eye model exists in large part to solve exactly this: fit an eye model, track the eyeball center, and stay accurate as the headset shifts. Adopting it would bring three costs:

1. **Licensing.** pye3d is not LGPL. Standalone use is permitted for academic purposes; commercial use is tied to official Pupil Core hardware. Keeping it out of v1 keeps this repo cleanly Apache-2.
2. **Compute.** The 3D model is meaningfully heavier than a threshold and an ellipse fit, and Gate 2 already has to prove two eyes at 120 to 200Hz on a phone, which is a 5 to 8ms budget per frame pair including MJPEG decode.
3. **Complexity, for a benefit this design largely does not need.** The target is a flat display at a single fixed focal plane, rendered 1:1. A 2D mapping is the mathematically appropriate tool for that; the 3D model's world-space gaze vector is machinery this project has no use for.

So the tradeoff is deliberate: engineer slippage away in hardware rather than model it in software. That only holds if the hardware side is taken seriously, which is why the mount is treated as load-bearing rather than as packaging.

## Sources of drift, roughly in order

**Glasses reseating.** The user pushes the glasses up their nose. This is the big one, it happens constantly in normal wear, and no mount rigidity prevents it, because it moves the whole assembly including the camera relative to the eye. Fast recalibration is the only real answer.

**Mount flex.** Force on the camera arm from a cable tug, a cheek, or a hand. Prevented by arm cross-section and by clamping rather than friction-fitting.

**Mount creep.** Slow plastic deformation under sustained load, accelerated by heat. This is why the mount README says PETG or ABS, not PLA. Creep drift is the worst kind to diagnose because it has a time constant of tens of minutes and looks like "the tracker gets worse over a session" rather than like a discrete event.

**Thermal expansion.** Small, but real over a long session on a warm face with a warm phone attached.

**Clamp loosening.** Vibration and repeated donning work a marginal clamp loose. Check `clamp_gap` before blaming anything else.

## Defenses

### 1. The mount (primary)

Clamped, not friction-fit. Thick arm. PETG or ABS. Layer orientation across the arm. See [../mount/README.md](../mount/README.md).

The test: press gently on the camera arm and watch the pupil position in the live feed. If it moves visibly, the mount is not adequate, and no software will compensate.

### 2. Fast recalibration (fallback)

Since reseating cannot be prevented, make recalibration cheap enough that it stops mattering. A five-second recalibration gesture changes drift from a serious limitation into a minor annoyance; a thirty-second one means users tolerate bad tracking instead.

Ideas worth building, in rough order of value:

- **Single-point offset correction.** Show one center target, collect a fixation, and apply the difference as a constant offset on top of the existing polynomial. Corrects pure translation, which is most of what reseating produces, in about a second. This is the highest-value item on the roadmap and it is cheap: it needs no refit, just an offset term.
- **Reduced-grid refit.** Five points instead of nine, for when a pure offset is not enough.
- **Full recalibration.** The existing nine-point flow.

### 3. Detecting drift (unsolved)

Ideally the system would notice it has drifted and prompt a recalibration. No detector currently does this. Some plausible signals, none implemented or validated:

- **Pupil position distribution shift.** Over a session the pupil's mean position in the eye image should be roughly stable. A sustained shift suggests the camera moved rather than that the user is looking somewhere new.
- **Interaction failure rate.** If a consumer app reports that gaze-driven selections are being corrected or missed unusually often, that is evidence of drift.
- **Binocular disagreement.** The two eyes map to screen positions that should agree closely. A growing systematic disagreement means at least one camera moved. This is the most promising signal, because it needs no assumptions about user behaviour, and it comes for free from data the pipeline already produces.

Binocular disagreement is worth prototyping first if drift detection is ever built.

## What honesty requires

If you use this system, expect to recalibrate. Not once, per session, possibly more than once per session. That is the cost of the 2D approach, and the design accepts it in exchange for simplicity, speed, clean licensing, and a pipeline that runs entirely on a phone.

If your application cannot tolerate periodic recalibration, this is the wrong design and the optional pye3d module on the roadmap is the honest answer, license terms and all.

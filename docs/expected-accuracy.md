# Expected accuracy

What this design should achieve, why, and what it will not.

**All figures here are predictions from the design and from published 2D eye-tracking results, not measurements from this system.** Nothing has been built yet. This document will be corrected with real numbers once Gates 1 and 2 pass and a mount exists. Until then, treat every number as a target to test against rather than a claim.

## The target

**1 to 2 degrees of visual angle**, held-out, with a rigid mount and well-aimed cameras.

This is the normal band for 2D polynomial regression eye tracking. It is not a compromise figure: on a fixed focal plane with a rigidly mounted camera, a 2nd-order polynomial is the right model, and 2D approaches routinely land here. Sub-degree is achievable with good conditions and shows up in the synthetic tests in `calibration/tests/`, but real detection noise, real fixation instability, and real optics all cost you something.

For calibration, published figures on comparable hardware:

| System | Figure |
| --- | --- |
| Pupil Core, full 3D pipeline, calibrated | 0.60 deg accuracy, 0.02 deg precision |
| Pupil Labs Neon, uncalibrated | 1.8 deg |
| Pupil Labs Neon, with offset correction | 1.3 deg |

So 1 to 2 degrees for a 2D polynomial sits below Pupil's own 3D pipeline with better software behind it, and roughly level with a calibration-free deep-learning tracker after offset correction. That is the right place for this design to aim.

## What that means on screen

**Published VITURE FOV figures are diagonal.** Converting to the horizontal and vertical the calibration module wants:

| Model | Panel | Diagonal FOV | Horizontal | Vertical |
| --- | --- | --- | --- | --- |
| Luma / Luma Pro / Luma Ultra | 1920x1200 (16:10) | 50 to 52 deg | ~45 deg | ~29 deg |
| VITURE Pro | 1920x1080 (16:9) | ~46 deg | ~41 deg | ~23 deg |
| VITURE One | 1920x1080 (16:9) | 43 deg | ~38 deg | ~22 deg |

Passing the diagonal figure to `fit_profile` instead of the horizontal and vertical pair will overstate your angular error by roughly 15% horizontally and nearly double it vertically.

For a Luma Pro at ~45 deg horizontal across 1920 px, about **43 px per degree**:

| Accuracy | Screen error | Practical meaning |
| --- | --- | --- |
| 0.5 deg | ~21 px | Small UI elements are selectable. |
| 1.0 deg | ~43 px | Comfortable for buttons and list rows. |
| 2.0 deg | ~85 px | Coarse regions only. Large targets, or gaze plus a confirm action. |
| 3.0 deg | ~128 px | Not usable for pointing. |

The design implication: build interactions around targets of at least 100px, or pair gaze with dwell or a click. Do not design a gaze-driven cursor that expects pixel precision, at any accuracy in this band.

Substitute your own display's FOV and resolution; pass `fov_degrees` to `fit_profile` and the validation reports will do this conversion for you.

## Where the error comes from

Roughly in order of expected contribution:

**Pupil centroid noise.** Threshold-based detection on a noisy IR image gives a centroid that jitters by a pixel or two frame to frame. This is the largest single error source, and the eye camera resolution sets its scale directly: at **192x192** one pixel is 1/192 of the image, at **400x400** it is 1/400. That is the whole argument for preferring 400x400 @ 120Hz over 192x192 @ 200Hz for this application. Other mitigations: better illumination, longer exposure, light temporal smoothing (at the cost of latency).

**Fixation instability.** The eye does not hold still. Microsaccades and drift move gaze by a fraction of a degree even during a deliberate fixation. This is a floor, not a bug, and it is why `FixationCollector` averages a burst rather than taking a single frame.

**Model error.** The polynomial does not perfectly describe the pupil-to-screen relationship. It is a good approximation over a display-sized FOV and gets worse toward the edges, which is why targets sit 10% in from the borders and why the corners are the first place accuracy degrades.

**Slippage.** Zero at calibration time, growing thereafter. See [slippage-and-drift.md](slippage-and-drift.md). Unlike the others this is unbounded, which is why the mount is treated as load-bearing.

**Corneal refraction.** The pupil you see is a refracted virtual image, displaced slightly from the physical pupil, and the displacement varies with gaze angle. pye3d models this; a 2D polynomial partially absorbs it into the fit, since it is a smooth function of gaze angle. This is a real source of residual error but a small one at these accuracies.

## What this design does not produce

- **Pupil diameter.** The ellipse fit gives an apparent size in image pixels, but converting that to millimeters needs the 3D model this project deliberately omits. Not needed for screen pointing.
- **True 3D gaze vector.** Output is a 2D screen position on one fixed plane. There is no world-space ray.
- **Depth or vergence.** Single focal plane. Not applicable.
- **Slippage-invariant accuracy.** Explicitly traded away. Hardware rigidity plus fast recalibration is the answer, not software compensation.

## Latency, which matters as much as accuracy

Accuracy gets quoted and latency gets felt. **This is where the real cameras beat the project's original assumptions by a wide margin**, because they run at 120 to 200Hz rather than the 30Hz first assumed.

| Stage | 400x400 @ 120Hz | 192x192 @ 200Hz |
| --- | --- | --- |
| Camera latency (specified) | 4.5 ms | 4.5 ms |
| Frame period | 8.3 ms | 5.0 ms |
| MJPEG decode + detection, two eyes | must fit the frame period (Gate 2 target) | must fit the frame period |
| Mapping and emission | negligible, a 6-term polynomial evaluation | negligible |
| Display: one frame at 120Hz | 8.3 ms | 8.3 ms |

Roughly **25 to 35 ms end to end**, against the 50 to 70 ms originally budgeted at 30Hz. That is comfortably into "feels attached to the eye" territory for a smoothed cursor, not just dwell selection, and it is the single biggest thing the hardware research improved.

Note the consequence for the resolution choice: since even 120Hz already puts total latency below the perceptual threshold for this kind of interaction, **spending the difference on spatial resolution rather than framerate is the right trade**. 200Hz buys 3.3 ms of latency you will not notice; 400x400 buys centroid precision you will.

Any temporal smoothing you add trades latency for stability directly. Add it deliberately, at the consumer end where the tradeoff can be tuned per use case, rather than baking it into the gaze stream.

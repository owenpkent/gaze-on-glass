# Expected accuracy

What this design should achieve, why, and what it will not.

**All figures here are predictions from the design and from published 2D eye-tracking results, not measurements from this system.** Nothing has been built yet. This document will be corrected with real numbers once Gates 1 and 2 pass and a mount exists. Until then, treat every number as a target to test against rather than a claim.

## The target

**1 to 2 degrees of visual angle**, held-out, with a rigid mount and well-aimed cameras.

This is the normal band for 2D polynomial regression eye tracking. It is not a compromise figure: on a fixed focal plane with a rigidly mounted camera, a 2nd-order polynomial is the right model, and 2D approaches routinely land here. Sub-degree is achievable with good conditions and shows up in the synthetic tests in `calibration/tests/`, but real detection noise, real fixation instability, and real optics all cost you something.

## What that means on screen

For a VITURE-class display, roughly 36 degrees horizontal at 1920 pixels wide:

| Accuracy | Screen error | Practical meaning |
| --- | --- | --- |
| 0.5 deg | ~27 px | Small UI elements are selectable. |
| 1.0 deg | ~53 px | Comfortable for buttons and list rows. |
| 2.0 deg | ~107 px | Coarse regions only. Large targets, or gaze plus a confirm action. |
| 3.0 deg | ~160 px | Not usable for pointing. |

The design implication: build interactions around targets of at least 100px, or pair gaze with dwell or a click. Do not design a gaze-driven cursor that expects pixel precision, at any accuracy in this band.

Substitute your own display's FOV and resolution; pass `fov_degrees` to `fit_profile` and the validation reports will do this conversion for you.

## Where the error comes from

Roughly in order of expected contribution:

**Pupil centroid noise.** Threshold-based detection on a noisy IR image gives a centroid that jitters by a pixel or two frame to frame. Over an 800x600 image mapped to a 36-degree FOV, a pixel of pupil jitter is a meaningful fraction of a degree. Mitigations: better illumination, longer exposure, light temporal smoothing (at the cost of latency).

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

Accuracy gets quoted and latency gets felt. Budget:

| Stage | Expected |
| --- | --- |
| Camera exposure and USB transfer | ~33ms at 30Hz, one frame period |
| Detection | under 16ms for two eyes (Gate 2 target) |
| Mapping and emission | negligible, a 6-term polynomial evaluation |
| Consumer app response | its own problem |

So roughly 50 to 70ms end to end at 30Hz. That is fine for dwell selection and for a smoothed cursor. It is noticeably laggy for anything expecting the cursor to feel attached to the eye, and no amount of accuracy work changes that. If latency matters more than accuracy for your use case, the lever is camera framerate, not the detector.

Any temporal smoothing you add trades latency for stability directly. Add it deliberately, at the consumer end where the tradeoff can be tuned per use case, rather than baking it into the gaze stream.

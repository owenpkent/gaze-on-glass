# gaze-calibration

Framework-agnostic 2D pupil-to-screen gaze calibration. Pure numpy: no OpenCV, no camera, no Android, no UI.

This is the reusable core of [Gaze on Glass](../README.md), but it is not specific to it. Anything that produces a pupil centroid per frame and wants to know where on a flat display the user is looking can use it.

## Install

```bash
pip install -e ".[dev]"
pytest
```

Requires Python 3.10+ and numpy.

## The model

Two independent least-squares polynomials per eye, over the six 2nd-order terms of the normalized pupil position:

```
sx = a0 + a1*px + a2*py + a3*px^2 + a4*px*py + a5*py^2
sy = b0 + b1*px + b2*py + b3*px^2 + b4*px*py + b5*py^2
```

Six coefficients each, so six fixation points is the mathematical minimum and nine is the practical one. Pupil positions are normalized to the eye image (0..1) before fitting, so coefficients stay well scaled and survive a change of capture resolution.

Why 2nd order: the pupil moves on a sphere, so its projection into the camera image is roughly sinusoidal in gaze angle. Over a display-sized FOV a quadratic absorbs that to well under the tracker's noise floor. `tests/test_calibration.py` fits against a synthetic spherical eye with an oblique camera and asserts sub-degree error on held-out targets, which is the premise of the whole design stated as a test.

## Usage

```python
import numpy as np
from gaze_calibration import (
    Eye, FixationCollector, default_target_grid,
    fit_profile, validate_profile, save_profile,
)

targets = default_target_grid(3, 3)      # 9 normalized screen positions

# 1. Collect: show each target, push frames in, keep the settled ones.
left_samples, kept_targets = [], []
for target in targets:
    show(target)
    c = FixationCollector()
    for frame in capture_for(milliseconds=800):
        pupil, confidence = detect_pupil(frame)     # your detector
        c.add(pupil, confidence)
    result = c.result()
    if result.accepted:
        left_samples.append(result.pupil)
        kept_targets.append(target)
    else:
        print("retry:", result.reason)

# 2. Fit.
profile = fit_profile(
    {Eye.LEFT: (np.array(left_samples), np.array(kept_targets))},
    image_size=(400, 400),         # Pupil Core eye camera
    screen_size=(1920, 1200),      # glasses display, NOT the phone panel
    fov_degrees=(45.0, 29.0),      # HORIZONTAL and VERTICAL, not diagonal
    metadata={"mount": "rev-a"},
)

# 3. Validate on a second, offset grid, then save.
reports = validate_profile(profile, {Eye.LEFT: held_out_pupil}, held_out_targets)
print(reports["left"].summary())
save_profile(profile, "profile.json")

# 4. Use.
screen = profile.map_binocular({Eye.LEFT: pupil}, confidence={Eye.LEFT: conf})
x_px, y_px = profile.to_pixels(screen)
```

## Modules

| Module | What it does |
| --- | --- |
| `polynomial` | The fit itself: design matrix, least squares, `PolynomialMapper`. |
| `profile` | Binocular container, confidence-weighted eye combination, JSON save/load. |
| `validation` | Held-out error in normalized, pixel, and angular units. |
| `collect` | Fixation burst handling: drop the saccade, filter by confidence, reject a burst too spread out to be a fixation. |

## Things worth knowing

**Validate on a grid the fit never saw.** Residual error on the fitting grid is not accuracy, it is how much a 6-coefficient polynomial can bend through your points. `fit_polynomial_mapper` reports `residual_rms` for diagnostics only. Use `validate_profile` against an offset grid for anything you intend to quote.

**Binocular averaging is not free accuracy, it is noise cancellation.** It helps because per-eye errors are largely independent. Pass real detector confidences; an eye at confidence 0 is dropped, so a binocular profile degrades to monocular on the frames where one detector loses the pupil, rather than dragging in a bad sample.

**A profile is only valid for the physical setup it was captured on.** Camera moved, mount changed, glasses reseated: refit. The `metadata` dict is there so you can record what setup a profile belongs to, which matters more than it sounds once you have a handful of them.

**Confidence in, confidence out.** `FixationCollector` defaults (settle 40% of the burst, confidence floor 0.6, max dispersion 0.02 normalized) are reasonable starting points, not tuned constants. Tune them against your detector once you have one. They are rate-agnostic: the settle fraction is a proportion of the burst, so an 800ms dwell works out to 96 usable samples at 120Hz or 160 at 200Hz without changing anything.

**`fov_degrees` is horizontal and vertical, not diagonal.** Display vendors publish diagonal FOV. Passing the diagonal figure straight through inflates every angular error you report: for a 16:10 panel at 52 deg diagonal, the real values are about 45 and 29 deg, so the diagonal overstates horizontal by 15% and vertical by nearly 80%. Convert first. Normalized and pixel error are unaffected, so if you are unsure, omit `fov_degrees` and quote those instead of quoting a wrong angle.

## License

Apache-2.0, same as the rest of the repo.

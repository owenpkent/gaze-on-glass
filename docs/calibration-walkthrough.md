# Calibration walkthrough

How to run a calibration, what good looks like, and how to tell when it went wrong.

The math lives in [`calibration/`](../calibration/) and is usable standalone. This document is about the procedure around it, which is where accuracy is actually won or lost.

## Before you start

Calibration cannot fix bad input. Confirm first:

- Pupil detected reliably (above 95%) at neutral gaze, and **still detected when looking at each corner of the display**. Corner detection is the usual failure and it is an illumination or camera-aim problem, not a calibration problem.
- Glasses seated the way they will be worn. Calibrate in the position you will use.
- Mount rigid. Press gently on the camera arm: if the pupil position in the feed shifts, calibration is going to drift and the mount needs work before anything else.

## The procedure

### 1. Show targets

Nine points (3x3) is the practical minimum, 25 (5x5) is the comfortable maximum. Beyond that you are spending user patience on diminishing returns: the 6-coefficient polynomial cannot exploit the extra information.

Keep targets 10% in from each edge (`default_target_grid`'s default margin). Targets in the literal corners sit where the polynomial extrapolates worst and where the eyelid starts occluding the pupil, so they add noise rather than coverage.

Target design matters more than it seems: a small high-contrast dot with a distinct center gives a tighter fixation than a large blob. A shrinking animation that settles to a dot pulls the eye in and reduces settling time.

### 2. Collect per target

Show the target, wait, sample. `FixationCollector` handles the details:

```python
from gaze_calibration import FixationCollector

c = FixationCollector()          # settle 40%, confidence floor 0.6, max dispersion 0.02
for frame in capture_for(milliseconds=800):
    pupil, confidence = detect_pupil(frame)
    c.add(pupil, confidence)

result = c.result()
if result.accepted:
    samples.append((result.pupil, target))
else:
    retry(target, reason=result.reason)
```

800ms per target is a reasonable dwell: roughly 300ms for the saccade and overshoot to settle, 500ms of usable fixation. The collector discards the leading 40% for exactly this reason.

**Re-show rejected targets rather than dropping them.** A missing target leaves a region of the screen unconstrained, and the polynomial will do something arbitrary there. Re-show at most twice, then abort the calibration and tell the user why: repeated rejection means something is wrong upstream that another attempt will not fix.

### 3. Fit

```python
from gaze_calibration import Eye, fit_profile

profile = fit_profile(
    {Eye.LEFT: (left_pupil, targets), Eye.RIGHT: (right_pupil, targets)},
    image_size=(800, 600),
    screen_size=(1920, 1080),
    fov_degrees=(36.0, 20.0),
    metadata={"mount": "rev-a", "session": "2026-07-25"},
)
```

Each eye is fitted independently, so a rejected sample on one eye does not cost you the other eye's sample at that target.

### 4. Validate on points the fit never saw

This is not optional, and the residual on the fitting grid is not a substitute. A 6-coefficient polynomial bending through 9 points will always show a small residual; that number describes the flexibility of the model, not the accuracy of the tracker.

Show a second grid, offset from the first (a 4x4 between the 3x3 targets works well), collect the same way, then:

```python
from gaze_calibration import validate_profile

reports = validate_profile(profile, {Eye.LEFT: lp, Eye.RIGHT: rp}, val_targets)
print(reports["binocular"].summary())
```

### 5. Save

```python
from gaze_calibration import save_profile
save_profile(profile, "profiles/2026-07-25-rev-a.json")
```

Record what setup the profile belongs to in `metadata`. Once you have a handful of profiles across mount revisions, this is the difference between a useful archive and a directory of indistinguishable JSON.

## What good looks like

| Held-out mean error | Verdict |
| --- | --- |
| under 1.0 deg | Good. This is what a rigid mount and clean detection should give. |
| 1.0 to 2.0 deg | Acceptable. Usable for pointing at reasonably sized targets. |
| 2.0 to 3.0 deg | Something is wrong. Look at the diagnostics below before accepting it. |
| above 3.0 deg | Do not ship this. The fit is describing noise. |

Check `p95` as well as the mean. A good mean with a bad p95 means specific screen regions are failing, usually the corners, which points at detection rather than at the fit.

## Diagnosing a bad calibration

**Error concentrated in the corners.** Detection is failing at extreme gaze angles: eyelid occlusion, or the pupil leaving the camera's field of view. Fix camera aim or illumination. No amount of refitting helps.

**Error uniformly mediocre everywhere.** Usually noisy centroids. Check `FixationResult.dispersion` values from the collection pass: if bursts were consistently near the rejection threshold, the detector is jittering and the fit is averaging noise.

**One eye far worse than the other.** That camera is aimed or lit worse. Fix it, or drop to a monocular profile for that session, which is better than dragging a bad eye into the average.

**Good immediately after calibration, degrading over minutes.** Slippage or mount creep. This is the known weakness of the 2D approach. Check mount rigidity, and check you did not print the mount in PLA. See [slippage-and-drift.md](slippage-and-drift.md).

**Good in the center, systematically offset toward one edge.** Often a head or glasses position that changed between calibration and use. Recalibrate in the position you will actually use.

## Recalibration

A profile is valid only for the physical setup it was captured on. Recalibrate whenever the glasses are reseated, the mount is touched, the camera resolution changes, or accuracy visibly drifts.

Design the calibration UI so this is cheap. If recalibrating is a 30-second ordeal, users tolerate bad tracking instead; if it is a five-second gesture, drift stops being a serious problem. The 2D approach trades slippage robustness for simplicity, and a fast recalibration path is how you buy most of that back.

# Gate 2: on-device UVC capture and pupil detection at framerate

**Question:** can the phone grab two UVC eye streams at 800x600 @ 30Hz and produce a stable pupil centroid for each, sustained, without thermal throttling or frame backlog?

Pupil Capture does not run on Android, so this pipeline is reimplemented natively. Gate 2 is about proving the reimplementation is viable on the target SoC before building an app around it.

## The three things being tested

1. **UVC capture works from an unprivileged Android app.** LineageOS provides the kernel-side UVC support; the app side needs a libuvc-based library (the `UVCCamera` / `libuvccamera` family, or `saki4510t`-lineage forks) because Android's Camera2 API does not expose arbitrary USB video devices.
2. **Detection is fast enough.** Threshold, contour, ellipse fit on an 800x600 8-bit image is cheap. The premise is that a mid-range SoC handles two of these at 30Hz with headroom. Measure, do not assume.
3. **It stays fast.** A phone that hits 30Hz for ten seconds and 12Hz after five minutes has failed this gate. Thermal behaviour is the real test, especially with the display mirroring and two cameras drawing current from the same port.

## Minimum viable detector

The dark-pupil approach, in the order the operations should be applied:

1. Grab the frame, luminance only. IR eye images are effectively monochrome; do not pay for color conversion.
2. Downscale if it helps. Pupil centroid accuracy survives 2x downscaling far better than intuition suggests, and it quarters the pixel cost. Try it before optimizing anything else.
3. Blur lightly (3x3 or 5x5 Gaussian) to kill sensor noise that would otherwise fragment the threshold.
4. Threshold. The pupil is the darkest large region under IR illumination. A fixed threshold works if illumination is controlled; an adaptive or percentile-based threshold (for example, the darkest 5% of pixels) survives changing conditions better.
5. Find contours, discard by area and by aspect ratio.
6. Fit an ellipse to the surviving candidate. `cv::fitEllipse` on the largest plausible contour.
7. Centroid is the ellipse center. Confidence can come from contour circularity, fit residual, and how cleanly the area falls in the expected band.

Glints from the IR illuminator sit *inside* the pupil as small bright spots and will punch holes in the threshold blob. A morphological close, or filling contour holes before the ellipse fit, deals with this. Do not skip it: hole-punched blobs bias the centroid in the direction of the glint, which is a systematic error that calibration will happily bake in.

## Measuring

Instrument these separately, since a pipeline that misses 30Hz for capture reasons needs a completely different fix than one that misses it for compute reasons:

| Metric | Target | Notes |
| --- | --- | --- |
| Frame arrival interval per camera | 33.3ms, low variance | If this is unstable, it is a USB or driver problem, not a CV problem. Revisit Gate 1. |
| Detection time per frame | well under 16ms for two eyes | Leaves headroom for mapping, emission, and the UI thread. |
| Sustained rate over 10 minutes | no degradation | The real test. Run it with the glasses actually displaying. |
| Detection rate (frames with a pupil found) | above 95% at neutral gaze | Below this, it is an illumination or camera-aim problem, not a code problem. |
| Battery and case temperature | not thermally throttling | Note whether PD charging through the hub changes this. |

Log per-frame timings to a CSV and look at the distribution, not the mean. A pipeline with a 4ms mean and a 60ms p99 drops frames in exactly the situations that matter.

## Threading

Naive single-threaded capture-then-detect will serialize two cameras behind each other. The shape that works:

- One capture thread per camera, doing nothing but pulling frames and handing off the latest one.
- Detection consuming the **most recent** frame, dropping any it fell behind on. Gaze is a live signal; processing a 200ms-old frame to keep a queue tidy is worse than dropping it.
- Mapping and emission on a third, cheap thread.

Explicitly do not build an unbounded queue anywhere in this pipeline. Latency compounds silently and the symptom (gaze lagging behind the eye) is easy to misattribute to calibration.

## What passing looks like

Two eyes, 800x600, 30Hz sustained for ten minutes with the glasses displaying, above 95% detection at neutral gaze, and a visible centroid that tracks the pupil without jitter that would swamp a 1 degree accuracy target.

At that point the viability question is answered and steps 4 to 6 of the critical path are known engineering.

## What failing looks like, and what to try

**Capture rate unstable.** USB or driver, not CV. Re-run Gate 1 with two cameras. Try MJPEG instead of uncompressed. Try 640x480.

**Detection too slow.** Downscale first, it is the biggest single win. Then check that you are not doing color conversion, not copying frames unnecessarily, and are using the OpenCV Android SDK's native path rather than round-tripping through Java bitmaps.

**Thermal throttling.** Downscale, drop to 720x540 or 640x480, or reduce to 20Hz and see whether the accuracy target still holds. 20Hz gaze is usable for pointing.

**Detection unreliable.** Almost always illumination or camera aim rather than algorithm. See [ir-illuminator-placement.md](ir-illuminator-placement.md) before touching the detector.

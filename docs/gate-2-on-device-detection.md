# Gate 2: on-device UVC capture and pupil detection at framerate

**Question:** can the phone stream two Pupil Core eye cameras and produce a stable pupil centroid for each, sustained, without thermal throttling or frame backlog?

Pupil Capture does not run on Android, so this pipeline is reimplemented natively. Gate 2 proves the reimplementation is viable on the target SoC before an app is built around it.

Component specs and citations: [hardware-reference.md](hardware-reference.md).

## Pick the operating point first

The cameras offer two modes, and the choice is not obvious:

| Mode | Pixels/frame | Frame budget (binocular) | Per-eye raw bandwidth |
| --- | --- | --- | --- |
| 192x192 @ 200Hz | 36,864 | **5 ms** | ~59 Mbps |
| 400x400 @ 120Hz | 160,000 | **8.3 ms** | ~154 Mbps |

**400x400 @ 120Hz is probably the right choice for this project.** A screen-pointing application does not need 200Hz, and the extra spatial resolution goes straight into centroid precision: at 192x192, one pixel of centroid error is 1/192 of the image, versus 1/400. Since pupil centroid noise is the largest single contributor to gaze error, that difference shows up directly in accuracy.

Measure both anyway. The reservation behaviour may differ (see [Gate 1](gate-1-usb-enumeration-test.md)), and it is possible the higher-resolution mode is the one that fails to open two cameras.

## The capture path is constrained, and not by choice

**Android's Java USB host API does not support isochronous transfers.** `UsbDeviceConnection` handles control, bulk, and interrupt only. UVC video streaming is isochronous. The platform API therefore cannot stream from a webcam at all, at any resolution.

Every working Android UVC library resolves this identically: take the file descriptor from `UsbDeviceConnection`, hand it to a native libusb built against Android's usbfs, and run libuvc on top. This is userspace. It needs **no root and no kernel UVC driver**, which corrects an earlier assumption in this project: a custom ROM was never required, and stock Android is the better target. Persistent USB permission comes from a manifest intent filter, and `CAMERA` permission is required on Android 9 and later even though you are not using the platform camera.

AOSP's built-in external camera support (UVC through Camera2) is real but unusable here: the reference configuration caps at 30fps/640x480, 15fps/720p, 10fps/1080p, and the documentation states it is "not designed to support performance-intensive, complex tasks involving high-resolution and high-speed streaming," targeting "lightweight use cases such as video chatting and photo kiosks."

### Library choice

| Library | Status |
| --- | --- |
| [ernestp/AndroidUSBCamera](https://github.com/ernestp/AndroidUSBCamera) | **Maintained.** Android 16, 16KB page size, permission and reliability fixes. Current best default. |
| [shiyinghan/UVCAndroid](https://github.com/shiyinghan/UVCAndroid) | Maintained, on Maven Central. |
| [saki4510t/UVCCamera](https://github.com/saki4510t/UVCCamera) | Dormant since Jan 2017. Still the reference everyone forked; multi-camera demo in `USBCameraTest7`. |
| [pupil-labs/libuvc](https://github.com/pupil-labs/libuvc) | Pupil Labs' own fork with turbojpeg. Worth reading for camera-specific handling. |

Whichever you pick, the **bandwidth factor** knob is the one that matters, since it is the mitigation for isochronous over-reservation.

## Minimum viable detector

Dark-pupil, in the order the operations should be applied:

1. Grab the frame, luminance only. IR eye images are effectively monochrome; do not pay for color conversion.
2. **MJPEG decode.** At 120 to 200Hz binocular this is 240 to 400 decodes per second and is likely your largest single cost. Use a turbojpeg-backed path, not a Java bitmap round-trip.
3. Blur lightly (3x3) to kill sensor noise that would fragment the threshold. At 192x192 even a 5x5 is a meaningful fraction of the pupil, so keep the kernel small.
4. Threshold. The pupil is the darkest large region under IR illumination. A fixed threshold works if illumination is controlled; a percentile-based one (darkest ~5% of pixels) survives changing conditions better.
5. Find contours, discard by area and aspect ratio.
6. Fit an ellipse to the surviving candidate (`cv::fitEllipse`).
7. Centroid is the ellipse center. Confidence from contour circularity, fit residual, and whether the area falls in the expected band.

The camera's integrated IR illuminator produces glints that sit **inside** the pupil and punch holes in the threshold blob. Morphologically close, or fill contour holes, before the ellipse fit. Do not skip this: hole-punched blobs bias the centroid toward the glint, a systematic error that calibration will happily bake in.

Downscaling, the usual first optimization, is **not** available here. 192x192 is already small and halving it would cost accuracy you cannot spare.

## Measuring

Instrument these separately: a pipeline missing framerate for capture reasons needs a completely different fix than one missing it for compute reasons.

| Metric | Target | Notes |
| --- | --- | --- |
| Frame arrival interval per camera | 5.0ms @200Hz / 8.3ms @120Hz, low variance | If unstable, it is USB or driver, not CV. Revisit Gate 1. |
| MJPEG decode time per frame | measure separately from detection | Expected to dominate. |
| Detection time per frame | small fraction of the frame budget | 192x192 thresholding is trivial; if this is slow, something is copying frames. |
| Sustained rate over 10 minutes | no degradation | The real test. Run it with the glasses actually displaying. |
| Detection rate | above 95% at neutral gaze | Below this it is illumination or camera aim, not code. |
| Battery drain and case temperature | not thermally throttling | Glasses draw ~5W on top of everything else. Note whether PD charging changes it. |

Log per-frame timings to CSV and look at the distribution, not the mean. A 2ms mean with a 40ms p99 drops frames exactly when it matters, and at a 5ms budget a single p99 outlier costs you eight frames.

## Threading

Naive capture-then-detect serializes the two cameras behind each other. The shape that works:

- One capture thread per camera, doing nothing but pulling frames and publishing the latest.
- Detection consuming the **most recent** frame, dropping anything it fell behind on. Gaze is a live signal; processing a 200ms-old frame to keep a queue tidy is worse than dropping it.
- Mapping and emission on a third, cheap thread.

No unbounded queue anywhere in this pipeline. At 200Hz a queue builds latency eight times faster than it would at 30Hz, and the symptom (gaze lagging the eye) is easy to misattribute to calibration.

## What passing looks like

Two eyes at the chosen operating point, sustained for ten minutes with the glasses displaying, above 95% detection at neutral gaze, and a visible centroid tracking the pupil without jitter that would swamp a 1 degree accuracy target.

At that point the viability question is answered and steps 4 to 6 of the critical path are known engineering.

## What failing looks like, and what to try

**Second camera will not open.** Isochronous over-reservation. Lower the bandwidth factor. See [Gate 1](gate-1-usb-enumeration-test.md).

**Capture rate unstable.** USB or driver, not CV. Try the other resolution mode; try one camera to isolate.

**Decode too slow.** Confirm you are on a native turbojpeg path and not decoding through Java. If the SoC genuinely cannot keep up, drop to 120Hz at 400x400, then to 60Hz. 60Hz gaze is still perfectly usable for pointing.

**Thermal throttling.** Reduce framerate before resolution: this application needs spatial precision far more than temporal.

**Detection unreliable.** Almost always illumination or camera aim rather than algorithm. See [ir-illumination-and-optics.md](ir-illumination-and-optics.md) before touching the detector.

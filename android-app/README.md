# android-app

The on-device pipeline: UVC capture, OpenCV 2D pupil detection, calibration UI, gaze emission.

**Not written yet, deliberately.** Gates 1 and 2 in the [root README](../README.md) have not been tested. Building an app before knowing whether the phone can enumerate a camera alongside DP Alt Mode video, or sustain two 800x600 streams at 30Hz, would be building on an unverified premise. The gate docs ([Gate 1](../docs/gate-1-usb-enumeration-test.md), [Gate 2](../docs/gate-2-on-device-detection.md)) are the actual next work.

What follows is the intended shape, recorded so that when the gates pass the design decisions are already made.

## Intended structure

```
android-app/
  app/            UI: calibration flow, live preview, status
  capture/        UVC device discovery, permission, per-camera capture threads
  detect/         OpenCV dark-pupil detection, JNI boundary
  mapping/        port of gaze_calibration, or JNI to a native build of it
  emit/           loopback socket server implementing protocol/
```

## Decisions already made

**UVC library.** Android's Camera2 API does not expose arbitrary USB video devices, so capture goes through a libuvc-based library (`UVCCamera` / `libuvccamera` lineage). This needs USB host permission and works on LineageOS because the ROM ships UVC kernel support. Verify the specific fork's license before committing to it; some are permissive and some are not.

**OpenCV, not a hand-rolled detector.** OpenCV Android SDK is Apache-2, has the ellipse fit and contour work already, and is fast enough. Use the native path rather than round-tripping frames through Java bitmaps.

**MJPEG, probably mandatory.** If Gate 1 comes back at USB 2.0 (the likely 4-lane DP case), two uncompressed 800x600 YUY2 streams at 30Hz will not fit in 480 Mbps. MJPEG will.

**Drop frames, never queue them.** Gaze is a live signal. Detection consumes the most recent frame and discards anything it fell behind on. No unbounded queue anywhere in the pipeline. See [Gate 2](../docs/gate-2-on-device-detection.md).

**Mapping ported, not reimplemented.** The polynomial math is in [`calibration/`](../calibration/) with tests. Port it, keep the tests meaningful, and do not let the two drift apart. It is 6 coefficients and a dot product; the risk is not difficulty, it is silent divergence.

**Emission over a loopback socket.** Specified in [`protocol/`](../protocol/). Readable from any app or WebView on the device without an AIDL dependency.

## Open questions

- Foreground service versus bound service. A foreground service with a persistent notification is probably right: gaze should survive the calibration UI being backgrounded.
- Whether the calibration UI belongs in this app or in a separate one. Probably this one, since it needs the raw pupil feed.
- Where the profile lives on disk and how a consumer app learns which profile is active.
- Whether to expose the eye preview at all in the shipping app. Useful for debugging camera aim, and camera aim is the thing most likely to be wrong.

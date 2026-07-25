# android-app

The on-device pipeline: UVC capture, OpenCV 2D pupil detection, calibration UI, gaze emission.

**Not written yet, deliberately.** Gates 1 and 2 in the [root README](../README.md) have not been tested. Building an app before knowing whether the phone can stream two UVC cameras alongside DP Alt Mode video would be building on an unverified premise. The gate docs ([Gate 1](../docs/gate-1-usb-enumeration-test.md), [Gate 2](../docs/gate-2-on-device-detection.md)) are the actual next work.

What follows is the intended shape, recorded so that when the gates pass the design decisions are already made. Specs and citations behind these decisions: [hardware-reference.md](../docs/hardware-reference.md).

## Intended structure

```
android-app/
  app/            UI: calibration flow, live preview, status
  present/        Presentation-based rendering to the glasses display
  capture/        UVC device discovery, permission, per-camera capture threads
  detect/         OpenCV dark-pupil detection, JNI boundary
  mapping/        port of gaze_calibration, or JNI to a native build of it
  emit/           loopback socket server implementing protocol/
```

## Decisions already made

**Render through `Presentation`, do not mirror.** The glasses are a secondary display at 1920x1200 (Luma series) or 1920x1080 (One/Pro). Mirroring a 20:9 phone panel onto it letterboxes, which would silently break the "screen space is what the user sees" premise the entire calibration rests on. Android's [`Presentation`](https://developer.android.com/reference/android/app/Presentation) API renders directly to the secondary display at its native resolution, so the app owns every pixel in the glasses. This was not obvious until the display specs were checked, and it is the correction most likely to have cost a rebuild later.

**Native libuvc, not Camera2. This is forced, not preferred.** Android's Java USB host API does not support isochronous transfers, and UVC video streaming is isochronous, so `UsbDeviceConnection` alone cannot stream video at all. The working path everywhere is: get the fd from `UsbDeviceConnection`, hand it to native libusb over usbfs, run libuvc on top. Userspace, no root, no kernel UVC driver. AOSP's external camera HAL does expose UVC through Camera2, but its reference config caps around 30fps at 640x480 and the docs state it is not for high-speed streaming, so it cannot serve 120 to 200Hz.

**Library: [ernestp/AndroidUSBCamera](https://github.com/ernestp/AndroidUSBCamera)** as the default, with [shiyinghan/UVCAndroid](https://github.com/shiyinghan/UVCAndroid) as the alternative. Both are maintained; the widely-cited saki4510t/UVCCamera has been dormant since January 2017. Verify the license of whichever fork is chosen: the family is Apache-2.0 but the bundled `jni/libjpeg`, `jni/libusb`, and `jni/libuvc` carry their own terms.

**Expose the bandwidth factor.** It is the mitigation for USB isochronous over-reservation, which is the most likely way two cameras fail to stream simultaneously. It needs to be reachable from the app, not buried, because tuning it is part of bring-up.

**Operating point: 400x400 @ 120Hz, probably.** The cameras also offer 192x192 @ 200Hz. Screen pointing does not need 200Hz, and at 192x192 a one-pixel centroid error is 1/192 of the image against 1/400, so the extra resolution converts directly into accuracy. Make it configurable and measure both in Gate 2, including which mode reserves less bandwidth.

**MJPEG decode is the cost centre, not detection.** At 120Hz binocular that is 240 decodes per second in an 8.3ms budget; at 200Hz, 400 decodes in 5ms. The thresholding and ellipse fit on a 400x400 image are trivial by comparison. Use a turbojpeg-backed native path and never round-trip through Java bitmaps.

**OpenCV Android SDK**, Apache-2.0. Use the **`16kb-page-fix`** package variant: the standard SDK was built with an older NDK and its C++ runtime is not aligned for 16KB page devices, which Google Play now requires.

**Drop frames, never queue them.** Gaze is a live signal. Detection consumes the most recent frame and discards anything it fell behind on. No unbounded queue anywhere. At 200Hz a queue accrues latency more than six times faster than it would at 30Hz.

**Mapping ported, not reimplemented.** The polynomial math is in [`calibration/`](../calibration/) with tests. Port it and keep the tests meaningful. It is 6 coefficients and a dot product; the risk is not difficulty, it is silent divergence.

**Emission over a loopback socket**, specified in [`protocol/`](../protocol/), with per-client rate capping so a consumer that wants 30Hz is not forced to parse 200 messages a second.

## Open questions

- Foreground service versus bound service. A foreground service with a persistent notification is probably right: gaze should survive the calibration UI being backgrounded.
- Whether the calibration UI belongs in this app or a separate one. Probably this one, since it needs the raw pupil feed.
- Where the profile lives on disk and how a consumer app learns which profile is active.
- Whether to ship the eye preview in the release build. Useful for debugging camera aim, and camera aim is the thing most likely to be wrong.
- Power. The glasses draw about 5W with no battery of their own, plus two cameras, plus detection at 120Hz, plus the phone's own display. Sustained-session battery life is unknown and may turn out to be the practical limit rather than anything computational.

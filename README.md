# Gaze on Glass

Open-source, single-device gaze tracking for VITURE XR glasses using Pupil Core eye cameras, running entirely on a stock Android phone. No root, no custom ROM.

## What this is

A phone drives the VITURE glasses as a mirrored display over USB-C DP Alt Mode. Pupil Core IR eye cameras are rigidly mounted to the VITURE frame and connect to the same phone over UVC. The phone detects the pupil, maps it to screen coordinates via a calibration, and emits gaze as a stream any local app can consume. No desktop host, no second device, no Pupil Capture.

The core insight: because the glasses present the phone's framebuffer on a single fixed focal plane, "where the user looks" is just a 2D pupil-to-screen-pixel mapping. No head pose, no world-space gaze vector, no VITURE SDK. That collapses the hard AR coordinate-fusion problem into a flat 2D calibration.

One caveat that took research to surface: **do not rely on display mirroring**. A 20:9 phone panel mirrored onto a 16:10 glasses display gets letterboxed, and normalized screen coordinates then describe the phone panel rather than what the user actually sees. The app renders to the secondary display through Android's `Presentation` API instead, so it owns every pixel in the glasses and the 1:1 premise is exactly true rather than approximately true.

## Status

Pre-viability. The two hardware/runtime gates below have not been tested yet. Nothing downstream of them is worth building until they pass. The `calibration/` module is implemented and independently usable today, because it is pure math and does not depend on either gate.

Component specifications have been researched against primary sources and are collected in [docs/hardware-reference.md](docs/hardware-reference.md), which also lists the assumptions that research corrected. Read it before buying anything.

## Why 2D (not pye3d)

pye3d's 3D eye model exists mainly to compensate for headset slippage and to produce accurate world-space gaze vectors with corneal refraction correction. This project engineers both away:

- Cameras are rigidly mounted, so slippage is minimized by hardware, not modeled in software.
- The target is a flat, fixed-focal-plane display mirrored 1:1, so a 2D pupil to 2D screen mapping is the mathematically appropriate tool.

A 2D dark-pupil detector feeding a polynomial calibration is the correct design here, not a downgrade. It also keeps licensing clean (OpenCV Apache-2, no non-LGPL pye3d entanglement).

### What 2D gives up (stated honestly)

- Slippage robustness: if the glasses shift mid-session, calibration drifts and must be redone. Rigid mounting is the defense; a fast re-calibration gesture is the fallback.
- Pupil diameter and true 3D gaze angle: not produced, not needed for screen pointing.
- Depth / vergence: irrelevant on a single focal plane.

## Hardware

Full specifications with citations: [docs/hardware-reference.md](docs/hardware-reference.md).

- **VITURE XR glasses** (Sony Micro-OLED birdbath, USB-C DP Alt Mode video in). Luma Pro is 1920x1200 per eye at 120Hz, 52 deg diagonal FOV; older One/Pro models are 1920x1080 at 43 to 46 deg. No battery: the glasses draw about 5W from the host.
- **Pupil Core eye cameras**, UVC, IR, dark-pupil, **192x192 @ 200Hz or 400x400 @ 120Hz**, global shutter, 4.5ms latency, **IR illumination integrated into the module**. They enumerate as `Pupil Cam 3 ID0` / `ID1` and are fully UVC compliant. EUR 685 each, so EUR 1,370 for a pair, which is the dominant cost of this build.
- **Android phone**, stock firmware. Nothing in this pipeline needs root or a custom ROM: UVC capture runs in userspace over the USB host API, and everything else is public API. The binding constraint is **DP Alt Mode**, which most phones lack and many spec sheets do not mention. A custom ROM is if anything a liability here, since DP Alt Mode output is vendor-specific and is a known casualty of custom ROMs.
- **USB-C hub** passing DP Alt Mode video out AND a downstream UVC data path in.
- **Custom rigid mount** fixing the eye cameras to the VITURE frame.

400x400 @ 120Hz is probably the better operating point than 192x192 @ 200Hz: a screen-pointing application does not need 200Hz, and the extra spatial resolution converts directly into centroid precision and therefore accuracy. Gate 2 should measure both.

## The two gating unknowns (resolve these FIRST)

Everything else is engineering you can already do. These two decide whether the single-device design is viable at all.

### Gate 1: USB topology (video-out + camera-in on one port)

DP Alt Mode and USB data can coexist on one USB-C port, but when DP takes all four high-speed lanes, USB data drops to USB 2.0 (480 Mbps). VITURE does not publish how many lanes the glasses negotiate, and no teardown surfaced that answers it. Bandwidth arithmetic says 2-lane is plausible (1920x1200 @ 120Hz needs roughly 8 Gbps and two HBR3 lanes carry about 13 Gbps), which would leave USB 3.x intact, but this is an empirical question.

**The real risk is not raw throughput, it is USB isochronous bandwidth over-reservation.** UVC streams isochronously and reserves guaranteed bus bandwidth from a figure the camera firmware declares, and cameras routinely overstate it by 4x or more. Only ~384 Mbps of a USB 2.0 bus is available for periodic transfers. Two cameras that each over-declare simply fail to open, regardless of how little data they actually send. Pupil Core hits this in practice: Pupil Labs' own Vive add-on docs require disabling or downgrading the headset's built-in camera to free bandwidth for dual 200Hz eye streams.

Actual payload is comfortable either way, about 59 Mbps per eye uncompressed at 192x192 @ 200Hz and less in MJPEG. If Gate 1 fails, it will be reservation, not bandwidth, and the lever is the bandwidth-factor override that Android UVC libraries expose.

Full procedure and mitigations: [docs/gate-1-usb-enumeration-test.md](docs/gate-1-usb-enumeration-test.md).

### Gate 2: On-device UVC + pupil detection at framerate

Pupil Capture does NOT run on Android. The pipeline is reimplemented natively:

1. Grab UVC frames on Android. **Android's Java USB host API cannot do isochronous transfers, and UVC video is isochronous**, so streaming goes through native libusb/libuvc using the file descriptor from `UsbDeviceConnection`. This is userspace: no root, and no kernel UVC driver required. AOSP's built-in external camera path is capped around 30fps at 640x480 and is explicitly not for high-speed streaming, so it is not an option here.
2. Detect dark pupil per frame with OpenCV (Android SDK, Apache-2): IR image, threshold, find dark blob, fit ellipse, take centroid.
3. Confirm two eyes sustain framerate on the target SoC. At 192x192 the per-frame pixel work is trivial, but 200Hz binocular means **400 MJPEG decodes per second and a 5ms budget per frame pair**. Per-frame overhead dominates, not thresholding.

Full procedure: [docs/gate-2-on-device-detection.md](docs/gate-2-on-device-detection.md).

Gates 1 and 2 together are the "does this work at all" checkpoint.

## Architecture

```
VITURE glasses (Presentation display) <- DP Alt Mode video --  [ Android phone      ]
Pupil Core eye cameras (IR, UVC)   --> UVC frames -------->  [ 1. UVC capture     ]
                                                             [ 2. 2D pupil detect ]
                                                             [ 3. calib mapping   ]
                                                             [ 4. gaze emit       ]  --> local apps
       (all four stages on the phone, single device)
```

## The 2D pipeline

1. Capture: UVC eye frames on Android, per eye.
2. Detect: OpenCV dark-pupil. Threshold the IR image, find the dark blob, fit an ellipse, take the centroid. Optionally refine with a Swirski-style 2D approach (published, reimplementable). Output: pupil (x, y) in eye-image coords, per eye.
3. Map: pupil (x, y) to normalized screen (x, y) via the calibration polynomial.
4. Emit: gaze as normalized screen coordinates over a defined local transport.

Prototype detection first: everything downstream assumes a stable pupil centroid at framerate.

## Calibration (the reusable jewel)

Standard 2D polynomial approach, per eye. Implemented in [`calibration/`](calibration/) as a dependency-light Python package (numpy only), deliberately framework-agnostic so it can be lifted into any project or ported to the app.

1. Render a grid of fixation targets (9 to 25) at known normalized positions on the glasses display, via the `Presentation` API so there is no letterboxing between what is rendered and what is seen.
2. For each target, wait for fixation to settle, record mean pupil position per eye.
3. Fit two 2nd-order polynomials per eye (one for screen-x, one for screen-y), 6 coefficients each, by least squares.
4. Combine eyes: average mapped screen positions, or weight by detection confidence.
5. Validate on held-out targets, report pixel / angular error. Expect 1 to 2 degrees with a rigid mount and well-aimed cameras. For context, Pupil Core's own full 3D pipeline is specified at 0.60 degrees, so this target is conservative rather than optimistic. Note that published FOV figures are diagonal; pass horizontal and vertical FOV to the fit or the angular error will be wrong.
6. Save the calibration profile as JSON.

Walkthrough: [docs/calibration-walkthrough.md](docs/calibration-walkthrough.md).

## Repo layout

```
gaze-on-glass/
  android-app/     UVC capture, OpenCV 2D pupil detection, calibration UI, gaze emission
  calibration/     polynomial fit + validation, framework-agnostic, independently usable
  mount/           parametric CAD for the rigid camera mount (OpenSCAD source + STL)
  protocol/        gaze output format spec (local socket / intent / broadcast)
  docs/            researched hardware reference, the two gate procedures, IR illumination,
                   calibration walkthrough, expected accuracy, slippage caveat
  README.md
  LICENSE
```

## The mount (physical crux)

Slippage is the one real weakness of 2D, and the mount is the defense, so treat it as load-bearing.

- Aim each IR camera at the eye from below the birdbath combiner (30 to 45 degrees) without occluding the display. Birdbath optics sit close to the eye; clearance is the main challenge.
- Rigidity is everything: any flex between camera and frame invalidates the calibration. Clamp to the frame, do not rely on friction.
- IR illumination is **integrated into the Pupil Core camera module**, so aiming the camera aims the light. That removes a design variable and adds a constraint: the birdbath combiner is reflective in near-IR and can bounce the module's own illumination straight back into its lens.
- Ship parametric source (OpenSCAD) so others can adjust camera angle and frame tolerances, not just a fixed STL. This is what makes the project buildable on someone else's rig. Pupil Labs publish their camera mount geometry as reference (LGPL-3.0, so measure the interface rather than copying the model).
- Expect several print iterations to get angle and clearance right.

See [mount/](mount/).

## Licensing

- Code: Apache-2.0 ([LICENSE](LICENSE)).
- Mount CAD: CERN-OHL-S v2 ([mount/LICENSE](mount/LICENSE)).
- OpenCV: Apache-2, clean.
- pye3d: NOT used in v1. It is not LGPL (permitted standalone only for academic use, or commercial use with official Pupil Core hardware). Keeping it out of v1 keeps the license clean. If added later as an optional high-accuracy module, its terms will be documented clearly.
- VITURE SDK: not required. Glasses are used purely as a mirrored display.

## Critical-path order

1. USB webcam enumeration test through the hub (Gate 1).
2. UVC frame grab on the phone.
3. OpenCV pupil centroid at framerate (Gate 2).
4. Rigid camera mount.
5. 2D polynomial calibration.
6. Gaze output stream + protocol.

Steps 1 to 3 are the viability gate. If they pass, 4 to 6 are known engineering.

## Roadmap beyond v1

- Optional pye3d module for users who accept its license and want slippage compensation.
- Re-calibration gesture for mid-session drift.
- Reference consumer app demonstrating gaze-driven interaction.
- Second display client (web page) if a host-rendered variant is ever wanted.

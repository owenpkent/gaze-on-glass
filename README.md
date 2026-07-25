# Gaze on Glass

Open-source, single-device gaze tracking for VITURE XR glasses using Pupil Core eye cameras, running entirely on an Android (LineageOS) phone.

## What this is

A phone drives the VITURE glasses as a mirrored display over USB-C DP Alt Mode. Pupil Core IR eye cameras are rigidly mounted to the VITURE frame and connect to the same phone over UVC. The phone detects the pupil, maps it to screen coordinates via a calibration, and emits gaze as a stream any local app can consume. No desktop host, no second device, no Pupil Capture.

The core insight: because the glasses mirror the phone framebuffer 1:1, "where the user looks" is just a 2D pupil-to-screen-pixel mapping. No head pose, no world-space gaze vector, no VITURE SDK. That collapses the hard AR coordinate-fusion problem into a flat 2D calibration on a single fixed focal plane.

## Status

Pre-viability. The two hardware/runtime gates below have not been tested yet. Nothing downstream of them is worth building until they pass. The `calibration/` module is implemented and independently usable today, because it is pure math and does not depend on either gate.

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

- VITURE XR glasses (birdbath display, USB-C DP Alt Mode video in). Used purely as a mirrored display.
- Pupil Core eye cameras (UVC, IR, dark-pupil, up to 800x600 @ 30Hz per eye).
- Android phone running LineageOS (for USB host control, UVC kernel support, and unsandboxed hardware access).
- USB-C hub that passes DP Alt Mode video out AND a downstream UVC data path in.
- Custom rigid mount fixing the eye cameras to the VITURE frame.

## The two gating unknowns (resolve these FIRST)

Everything else is engineering you can already do. These two decide whether the single-device design is viable at all.

### Gate 1: USB topology (video-out + camera-in on one port)

DP Alt Mode and USB data can coexist on one USB-C port, but when DP takes the high-speed lanes, USB data may drop to USB 2.0 (480 Mbps). Whether that happens depends on how many DP lanes the VITURE glasses negotiate:

- 2-lane DP: USB 3.x data path survives alongside video. Comfortable.
- 4-lane DP: cameras run over USB 2.0. Still likely workable: two 800x600 @ 30Hz MJPEG eye streams fit inside 480 Mbps.

Full procedure: [docs/gate-1-usb-enumeration-test.md](docs/gate-1-usb-enumeration-test.md).

If the webcam enumerates and streams frames while the glasses show video, Pupil Core cameras (also UVC) will too. If it does not, the single-device design fails at the hardware layer and needs a different hub or a fallback host for the cameras.

### Gate 2: On-device UVC + pupil detection at framerate

Pupil Capture does NOT run on Android. The pipeline is reimplemented natively:

1. Grab UVC frames on Android (libuvc / UVCCamera-style library; requires UVC kernel support, which LineageOS provides).
2. Detect dark pupil per frame with OpenCV (Android SDK, Apache-2): IR image, threshold, find dark blob, fit ellipse, take centroid.
3. Confirm two eyes at 800x600 @ 30Hz sustains framerate on the target SoC. Thresholding at this size is light; a mid-range SoC should manage, but measure it.

Full procedure: [docs/gate-2-on-device-detection.md](docs/gate-2-on-device-detection.md).

Gates 1 and 2 together are the "does this work at all" checkpoint.

## Architecture

```
VITURE glasses (mirrored display)  <-- DP Alt Mode video --  [ Phone / LineageOS ]
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

1. Render a grid of fixation targets (9 to 25) on the phone at known normalized positions. The glasses mirror them, so screen space IS what the user sees.
2. For each target, wait for fixation to settle, record mean pupil position per eye.
3. Fit two 2nd-order polynomials per eye (one for screen-x, one for screen-y), 6 coefficients each, by least squares.
4. Combine eyes: average mapped screen positions, or weight by detection confidence.
5. Validate on held-out targets, report pixel / angular error. Expect 1 to 2 degrees with a rigid mount and well-aimed cameras.
6. Save the calibration profile as JSON.

Walkthrough: [docs/calibration-walkthrough.md](docs/calibration-walkthrough.md).

## Repo layout

```
gaze-on-glass/
  android-app/     UVC capture, OpenCV 2D pupil detection, calibration UI, gaze emission
  calibration/     polynomial fit + validation, framework-agnostic, independently usable
  mount/           parametric CAD for the rigid camera mount (OpenSCAD source + STL)
  protocol/        gaze output format spec (local socket / intent / broadcast)
  docs/            enumeration test, IR illuminator placement, calibration walkthrough,
                   expected accuracy, slippage caveat
  README.md
  LICENSE
```

## The mount (physical crux)

Slippage is the one real weakness of 2D, and the mount is the defense, so treat it as load-bearing.

- Aim each IR camera at the eye from below the birdbath combiner (30 to 45 degrees) without occluding the display. Birdbath optics sit close to the eye; clearance is the main challenge.
- Rigidity is everything: any flex between camera and frame invalidates the calibration. Clamp to the frame, do not rely on friction.
- IR illuminator placement (dark-pupil, ~850nm) affects glint quality and whether the birdbath coating throws reflections back into the camera.
- Ship parametric source (OpenSCAD) so others can adjust camera angle and frame tolerances, not just a fixed STL. This is what makes the project buildable on someone else's rig.
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

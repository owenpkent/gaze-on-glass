# Hardware reference

Consolidated manufacturer specifications and primary-source findings for every component in this design, with citations. Compiled 2026-07-25.

Manuals and datasheets are **cited and linked, not vendored** into this repo, since they are third-party copyrighted material. Every claim below traces to a linked source. Where a number could not be found in a primary source, it says so rather than guessing.

**This document corrected several assumptions the project started with.** Those corrections are listed at the end.

---

## 1. Pupil Core eye cameras

### Specifications

| Property | Value | Source |
| --- | --- | --- |
| Resolution / rate | **192x192 @ 200 Hz**, or **400x400 @ 120 Hz** | [tech specs](https://pupil-labs.com/products/core/tech-specs), [200 FPS blog](https://pupil-labs.com/blog/200-frames-per-second) |
| Shutter | Global | [tech specs](https://pupil-labs.com/products/core/tech-specs) |
| Latency | 4.5 ms | [accessories](https://pupil-labs.com/products/core/accessories) |
| IR illumination | **Integrated in the camera module**, for dark-pupil | [accessories](https://pupil-labs.com/products/core/accessories) |
| Focus | 200 Hz cameras are fixed focus (lens glued); 120 Hz cameras focus manually | [hardware docs](https://docs.pupil-labs.com/core/hardware/) |
| UVC compliance | "Both cameras are **fully UVC compliant** and will work with OpenCV's video backend, Pupil Capture, and libraries like libuvc and pyuvc" | [Vive add-on docs](https://docs.pupil-labs.com/core/vr-ar/vive/) |
| Device names | `Pupil Cam 3 ID0` (right eye), `Pupil Cam 3 ID1` (left eye) | [Vive add-on docs](https://docs.pupil-labs.com/core/vr-ar/vive/) |
| Stream format | MJPEG | [Vive add-on docs](https://docs.pupil-labs.com/core/vr-ar/vive/) |
| Connector | USB-C (headset uses an internal hub behind one cable) | [tech specs](https://pupil-labs.com/products/core/tech-specs) |
| Price | **EUR 685 each**, left and right sold separately | [accessories](https://pupil-labs.com/products/core/accessories) |
| Physical dimensions | **Not published.** Must be measured. | (none) |
| Standalone connectivity | **Unverified.** See the warning below. | (none) |

> **The individually-sold cameras may not be usable without the Pupil Core frame.** Pupil Labs describe them as being "for upgrading existing 120Hz headsets", fitted with "no tools required". That implies they plug into the Core frame's internal wiring and USB hub, which this project does not have. No source documents whether a standalone camera ships with a host connection usable on its own.
>
> This is a procurement blocker, not a technical one, and it is answerable with one email to Pupil Labs. If the answer is no, the cheapest path to real cameras jumps from EUR 1,370 to a complete headset at EUR 3,615. See [bill-of-materials.md](bill-of-materials.md).

### What this changes

The project assumed 800x600 @ 30 Hz. The real cameras are **192x192 @ 200 Hz**: 13x fewer pixels per frame, 6.7x more frames per second. Consequences:

- Per-frame pixel work is trivial. **Per-frame overhead dominates**: at 200 Hz binocular you have a 5 ms budget for 2 MJPEG decodes, 2 detections, a mapping, and an emit. JPEG decode and any JNI or allocation churn is the cost centre, not the thresholding.
- 192x192 is small for centroid precision. A 1-pixel centroid error is 1/192 of the image, versus 1/800 at the assumed resolution. **400x400 @ 120 Hz is likely the better operating point for this project**, since 120 Hz is far more than a screen-pointing application needs and the extra spatial resolution goes directly into accuracy. This is now an explicit tuning decision, and it was not visible before.
- Latency improves dramatically over the original assumption: 4.5 ms camera latency plus a 5 ms frame period, versus 33 ms at 30 Hz.

### Cost

**EUR 1,370** for a binocular pair, before the mount, hub, or phone. That is the dominant cost of this build and it was not previously stated anywhere in the repo. Cheaper paths, in decreasing fidelity: a complete used Pupil Core headset; the [DIY build](https://docs.pupil-labs.com/core/diy/) (modified Logitech C525/C512 or Microsoft HD-6000 webcams with the IR filter replaced and IR LEDs soldered on), which is far cheaper but gives rolling-shutter, lower-rate, hand-focused cameras.

---

## 2. VITURE XR glasses

Model matters. Specs differ across the line and this project's calibration is display-geometry-specific.

| Model | Price | Per-eye resolution | Refresh | Diagonal FOV | Source |
| --- | --- | --- | --- | --- | --- |
| VITURE One / One Lite | discontinued | 1920x1080 | 60 Hz | 43 deg | [VRcompare](https://vr-compare.com/headset/vitureonelite) |
| VITURE Pro | discontinued | 1920x1080 | 120 Hz | ~46 deg (est.) | [VRcompare](https://vr-compare.com/headset/viturepro) |
| VITURE Luma | $399 | 1920x1200 | 120 Hz | 50 deg | [VITURE](https://www.viture.com/luma) |
| VITURE Luma Pro | $499 | **1920x1200** | **120 Hz** | **52 deg** | [VITURE](https://www.viture.com/luma) |
| VITURE Luma Ultra | $599 | 1920x1200 | 120 Hz | 52 deg | [VITURE](https://www.viture.com/luma) |

Display geometry is identical across the Luma line, and the Pro's electrochromic dimming and the Ultra's extra brightness do nothing for gaze tracking. For this project specifically, the $399 Luma is the rational choice. See [bill-of-materials.md](bill-of-materials.md).

Luma Pro detail, from the manufacturer spec table:

- Panel: **Sony Micro-OLED**, contrast >= 100,000:1, 108% sRGB, 1000 nits peak
- Virtual image: 152 inch at 4 m
- IPD: 64.0 +/- 6.0 mm (Regular), 68.0 +/- 6.0 mm (Large)
- Myopia adjustment: to -4.0 D
- Weight: 79 g (Regular) / 81 g (Large)
- **No built-in battery**: draws power from the host device
- Electrochromic film: 0.5% to 40% transmittance
- Connector: USB-C magnetic cable, 1.2 m

**Power draw:** VITURE's own [Pro Mobile Dock](https://www.viture.com/product/viture-pro-mobile-dock) provides **5 V / 1 A (5 W) per glasses port**. Treat 5 W as the glasses budget the phone must supply, on top of the cameras and its own display and compute.

### FOV numbers are diagonal

The 43 / 46 / 52 degree figures are **diagonal** FOV. The calibration module wants horizontal and vertical FOV to convert error into degrees.

| Model | Panel | Diagonal | Horizontal | Vertical |
| --- | --- | --- | --- | --- |
| Luma / Luma Pro / Luma Ultra | 1920x1200 (16:10) | 50 to 52 deg | ~45 deg | ~29 deg |
| VITURE Pro | 1920x1080 (16:9) | ~46 deg | ~41 deg | ~23 deg |
| VITURE One | 1920x1080 (16:9) | 43 deg | ~38 deg | ~22 deg |

Derived by rectilinear projection: `tan(h/2) = tan(d/2) * w/sqrt(w^2+h^2)`. Approximate, since these are not perfectly rectilinear optics, but far closer than using the diagonal directly.

Derive these for your model rather than passing the diagonal figure to `fit_profile`. Passing the diagonal overstates horizontal error by about 15% and vertical by nearly 80%.

### The aspect-ratio trap (new, and it matters)

The project premise is "the glasses mirror the phone framebuffer 1:1, so screen space IS what the user sees." That premise is **only true if the phone is not letterboxing**. A 20:9 phone panel mirrored to a 16:10 glasses display gets pillarboxed, and normalized screen coordinates then refer to the phone panel, not to the visible area in the glasses.

The fix is architectural: do not mirror. Use Android's [`Presentation`](https://developer.android.com/reference/android/app/Presentation) API to render directly to the secondary display at its native 1920x1200, so the app owns every pixel the user sees and normalized coordinates mean exactly what the calibration assumes.

### DP lane count: unpublished

VITURE does not publish whether the glasses negotiate 2-lane or 4-lane DP Alt Mode, and it is not in the product pages, the dock spec, or the compatibility page. Searching did not surface a teardown that answers it.

Bandwidth arithmetic says **2-lane is plausible**: 1920x1200 @ 120 Hz at 24 bpp is about 6.6 Gbps of pixel data, roughly 8 Gbps with 8b/10b encoding. Two HBR3 lanes carry 12.96 Gbps effective, which fits comfortably. If VITURE negotiates 2-lane, USB 3.x survives alongside video and Gate 1 is easy.

This stays an empirical question. It is exactly what [Gate 1](gate-1-usb-enumeration-test.md) tests.

---

## 3. USB-C topology

### DP Alt Mode lane assignment

| Pin assignment | DP lanes | USB lanes | Result | Source |
| --- | --- | --- | --- | --- |
| C / E | 4 | 0 | USB data falls back to USB 2.0 (480 Mbps) | [TotalPhase](https://www.totalphase.com/blog/2019/11/how-displayport-alt-mode-is-enabled-over-a-usb-type-c-cable/) |
| D / F | 2 | 2 | USB 3.2 (to 10 Gbps) coexists with video | [Newnex](https://newnex.com/usb-c-dp-alt-mode.php) |

Rule of thumb from Newnex: if a port does USB 3.2 while outputting DisplayPort, it is running 2-lane DP Alt Mode.

### The real risk is not raw bandwidth, it is isochronous over-reservation

This is the single most important finding of this research pass, and it is the most likely way Gate 1 fails.

UVC video streams over **isochronous** transfers, which reserve guaranteed bus bandwidth up front. The host reads `dwMaxPayloadTransferSize` from the device's interface descriptor and picks an alternate setting with at least that much bandwidth. **Many cameras massively overstate this number.** The Good Penguin measured cameras requesting 3060 bytes per microframe (about 195 Mbps) to stream 320x240 MJPEG at 25 fps, which genuinely needs about 46 Mbps. Two such cameras cannot coexist.

Constraints that stack up:

- USB 2.0 Hi-Speed: 480 Mbps theoretical, **80% cap on periodic transfers, leaving ~384 Mbps**, and roughly 196 Mbps available for isochronous per device.
- The kernel cannot estimate bandwidth for **compressed** formats, so the `UVC_QUIRK_FIX_BANDWIDTH` workaround (which recomputes it for uncompressed formats) does not help MJPEG cameras. ([The Good Penguin](https://www.thegoodpenguin.co.uk/blog/multiple-uvc-cameras-on-linux/))

**Pupil Core hits this in practice.** Pupil Labs' own Vive add-on documentation says that to run dual 200 Hz eye cameras you must either disable the Vive's built-in camera or drop it to 30 Hz, and recommends running "a separate USB lane along the tether" for full performance. ([Vive add-on docs](https://docs.pupil-labs.com/core/vr-ar/vive/))

Mitigations available to this project:

- Android UVC libraries expose a **bandwidth factor** to override the requested reservation ([UVCCamera](https://github.com/saki4510t/UVCCamera)). This is the userspace equivalent of the `bandwidth_cap` patch and it is the main lever.
- 400x400 @ 120 Hz may reserve *less* than 192x192 @ 200 Hz depending on how the firmware computes it. Test both; do not assume the lower-resolution mode is the safer one.
- Actual payload is modest either way: 192x192 @ 200 Hz is about 59 Mbps per eye uncompressed and well under that in MJPEG; 400x400 @ 120 Hz is about 154 Mbps per eye uncompressed. Both fit 480 Mbps for two eyes. The failure, if it comes, is reservation, not throughput.

### Existence proof, partial

DeX-style docks routinely deliver DP video plus USB peripherals from one phone port ([DeX docks](https://www.samsung.com/)). That proves the topology works. It does not prove it works for **two isochronous-hungry UVC cameras**, which is a categorically harder ask than a keyboard and mouse.

---

## 4. Android capture path

### Android's Java USB host API cannot do isochronous transfers

**Isochronous endpoints are unsupported in `UsbDeviceConnection`.** ([Android USB host docs](https://developer.android.com/develop/connectivity/usb/host), [Embedded.com](https://www.embedded.com/the-basics-of-usb-device-development-using-the-android-framework/)) The Java API handles control, bulk, and interrupt only. UVC video streaming is isochronous. So the Java USB API alone **cannot** stream from a webcam, at any resolution.

Every working Android UVC library resolves this the same way: take the file descriptor from `UsbDeviceConnection`, hand it to a native libusb built against Android's usbfs, and run libuvc on top. This is userspace, needs **no root and no kernel UVC driver**.

That last point corrects a project assumption. The repo said the pipeline "requires UVC kernel support, which LineageOS provides." It does not require it. The value of LineageOS here is unrestricted USB host access and control over the ROM, not a `uvcvideo` kernel module.

### AOSP's built-in external camera support is not usable here

Android does support UVC webcams through Camera2 and the external camera HAL, but the AOSP documentation caps the reference config at **30 fps at 640x480, 15 fps at 720p, 10 fps at 1080p**, and states the feature is "not designed to support performance-intensive, complex tasks involving high-resolution and high-speed streaming," targeting "lightweight use cases such as video chatting and photo kiosks." ([AOSP external USB cameras](https://source.android.com/docs/core/camera/external-usb-cameras))

At 200 Hz, that path is out. Direct libuvc it is.

### Library options

| Library | Status | Notes |
| --- | --- | --- |
| [ernestp/AndroidUSBCamera](https://github.com/ernestp/AndroidUSBCamera) | **Maintained.** Android 16 and 16 KB page size support, permission and reliability fixes. | The active continuation of the jiangdongguo lineage. Current best default. |
| [shiyinghan/UVCAndroid](https://github.com/shiyinghan/UVCAndroid) | Maintained, on Maven Central (1.0.11) | Clean modern packaging. |
| [jiangdongguo/AndroidUSBCamera](https://github.com/jiangdongguo/AndroidUSBCamera) | Unmaintained (last release Feb 2023) | Superseded by the ernestp fork. |
| [saki4510t/UVCCamera](https://github.com/saki4510t/UVCCamera) | **Dormant since Jan 2017** | The original. Apache-2.0, except `jni/libjpeg`, `jni/libusb`, `jni/libuvc` which carry their own licenses. Multi-camera demonstrated in `USBCameraTest7`; exposes the bandwidth factor. Still the reference implementation everyone forked. |
| [pupil-labs/libuvc](https://github.com/pupil-labs/libuvc) | Maintained by Pupil Labs | Their fork, with turbojpeg. Worth reading for Pupil-camera-specific handling even if not used directly. |

This corrects the repo's earlier recommendation, which named the dormant 2017 library.

### OpenCV

OpenCV 4.14.0 and 5.0.0 are released; Android SDK ships as `opencv-<version>-android-sdk.zip`. **Use the `16kb-page-fix` variant**: the standard SDK was built with an older NDK and its C++ runtime is not aligned for 16 KB page devices, which is a Google Play requirement now. Apache-2.0, so the licensing premise holds. ([Android release notes](https://github.com/opencv/opencv/wiki/Android_Release_Notes))

### Stock Android is sufficient, and is the better target

Nothing in this pipeline needs root or a custom ROM:

- **UVC capture**: the libusb-over-usbfs path works on non-rooted devices by design; that is the entire premise of the UVCCamera family ("access to UVC web camera on **non-rooted** Android device").
- **Persistent USB permission**: granted by declaring a `USB_DEVICE_ATTACHED` intent filter with a `device_filter.xml` in the manifest. When the user picks the app as default for that device, the system grants permission automatically on every subsequent attach, with no per-connect dialog. ([UVCCamera wiki](https://github.com/saki4510t/UVCCamera/wiki/howto_hold_permanent_permission))
- **`CAMERA` permission is still required** on Android 9 and later for UVC access, even though the platform camera stack is not being used. ([AOSP](https://source.android.com/docs/core/camera/external-usb-cameras))
- **`Presentation` rendering, loopback sockets, foreground services**: all public API.

**A custom ROM is, if anything, a liability here.** DP Alt Mode video output depends on vendor display HAL code, and it is a known casualty of custom ROMs: LineageOS carries open issues for USB-C video out not working on devices including the OnePlus 9 Pro ([#6769](https://gitlab.com/LineageOS/issues/android/-/issues/6769)) and Samsung S10e ([#4658](https://gitlab.com/LineageOS/issues/android/-/issues/4658)). Samsung DeX, the most reliable external-display implementation on Android, is proprietary and does not survive the switch either.

Since working video out is the scarcest capability in the whole design, the correct default is **stock OEM firmware**.

### Host phone requirement

The phone needs DP Alt Mode, which is **not common**: mostly Samsung Galaxy S/Note flagships, some Sony, Huawei, and gaming phones. Budget and mid-range USB-C phones usually lack it, and the spec sheet often does not mention it either way. Pixels through Pixel 8 required root or were disabled. ([UPERFECT list](https://uperfect.com/blogs/wikimonitor/list-of-smartphones-with-displayport-alt-mode))

The binding constraint is the intersection of: has DP Alt Mode **that actually works in the firmware you will run**, has USB host, and has the compute headroom. Confirm on the specific handset before buying anything, and confirm it on the firmware you intend to keep.

---

## 5. Mount interface

Pupil Labs publishes camera mount geometry at [pupil-labs/pupil-geometry](https://github.com/pupil-labs/pupil-geometry): the DIY set, the headset triangle mount, the ball-joint arm, and the arm extender, as STL and STP. Their stated intent is that "by releasing the mounts as example geometry we automatically document the interface," and that you should take measurements from them to build your own mounts. They recommend SLS or HPSLS printing for durability and fit, and note tolerances need adjusting per process.

The Pupil Core **frame** CAD is not open source; only the mounts are.

**License caution:** pupil-geometry is **LGPL-3.0**. Measuring their geometry to determine an interface is fine. Copying or adapting their STL into this repo's mount would make the result a derivative work under LGPL-3.0, which conflicts with the CERN-OHL-S license chosen for `mount/`. Keep the VITURE mount an independent design that mates with a measured interface.

The Core headset itself mounts eye cameras on a **sliding arm with a 6-DOF ball joint**, tensioned by a set screw so the camera can be moved by hand but not by head motion ([hardware docs](https://docs.pupil-labs.com/core/hardware/)). That is a useful reference point, though this project deliberately wants a *rigid* mount rather than an adjustable one, since adjustability and calibration stability are in direct tension.

---

## 6. Accuracy context

| System | Figure | Source |
| --- | --- | --- |
| Pupil Core, full 3D pipeline, calibrated | **0.60 deg accuracy, 0.02 deg precision** | [tech specs](https://pupil-labs.com/products/core/tech-specs) |
| Pupil Core calibration | 5-point, multiple methods | [tech specs](https://pupil-labs.com/products/core/tech-specs) |
| Neon VR/AR add-on, uncalibrated | 1.8 deg | [VR/AR tech specs](https://pupil-labs.com/products/vr-ar/tech-specs) |
| Neon with offset correction | 1.3 deg | [VR/AR tech specs](https://pupil-labs.com/products/vr-ar/tech-specs) |

This project's **1 to 2 degree target for a 2D polynomial remains reasonable and appropriately conservative**: below Pupil's own 0.60 deg for a full 3D pipeline with better software, comparable to a calibration-free deep-learning tracker with offset correction.

Note also that Pupil Core calibrates with **5 points** where this project specifies 9 to 25. That is not a contradiction: their 3D model needs fewer points because the model carries more structure. A 6-coefficient polynomial per axis genuinely needs at least 6.

---

## 7. Prior art

- [OpenEye (KAIST, ETRA 2026)](https://github.com/witlab-kaist/OpenEye): open framework putting a **Pupil Labs Neon** on Quest 3, Apple Vision Pro, and **XREAL Air 2 Ultra**, with 3D-printable mounts and calibration/mapping pipelines. Runs on a PC (pip-installed), not on-device. The closest published work to this project, and the difference is precisely the interesting part: OpenEye keeps the desktop host, Gaze on Glass removes it.
- Pupil Labs' own [VR/AR add-ons](https://pupil-labs.com/products/vr-ar) for Quest 3, Pico 4, Vive, HoloLens, and Epson Moverio: clip-on rings with IR illuminators and a USB connector clip. Commercial validation of the mount-cameras-to-someone-else's-headset approach. Quest 3 module mount is H30 x W39 x D19 mm at 10 g, which is a rough scale reference for what this project's mount must carry.

---

## Still unknown

Three things this research could not settle. Each is listed where it bites, but they are collected here because together they are the project's remaining risk surface.

| Unknown | Why it matters | How to settle it |
| --- | --- | --- |
| **VITURE DP lane count** (2-lane or 4-lane) | Decides whether USB 3.x survives alongside video, and therefore how much bandwidth headroom the cameras have | [Gate 1](gate-1-usb-enumeration-test.md). Not published by VITURE, not in any teardown found. |
| **Pupil eye camera dimensions** | The mount cannot be parameterised correctly without them | Calipers, once the cameras are in hand. Pupil's [published mount geometry](https://github.com/pupil-labs/pupil-geometry) is the interim reference (LGPL-3.0, measure but do not copy). |
| **Whether standalone eye cameras connect without the Core frame** | Decides whether the camera cost is EUR 1,370 or EUR 3,615 | One email to Pupil Labs. Cheapest unknown to close, and worth closing first. |

Nothing else in this document is speculative: every other figure traces to a cited primary source.

## Corrections this research forced

| Was | Now | Where it bites |
| --- | --- | --- |
| Eye cameras 800x600 @ 30 Hz | **192x192 @ 200 Hz or 400x400 @ 120 Hz** | Gate 2 budget, bandwidth math, latency, and a new resolution-vs-rate decision |
| "Requires UVC kernel support, which LineageOS provides" | Kernel UVC driver **not needed**; Java USB API **cannot** do isochronous, so native libusb/libuvc is mandatory | Gate 2 architecture |
| LineageOS required for unsandboxed hardware access | **Stock Android is sufficient and safer.** No root needed anywhere, and custom ROMs are a documented cause of DP video-out breaking | Host phone choice, Gate 1 setup |
| Recommend saki4510t/UVCCamera | Dormant since 2017; use **ernestp/AndroidUSBCamera** or shiyinghan/UVCAndroid | android-app plan |
| Bandwidth is the Gate 1 risk | **Isochronous over-reservation** is the Gate 1 risk; raw throughput is comfortable | Gate 1 procedure and mitigations |
| IR illuminator placement is a design task | Illumination is **integrated into the camera module** | ir-illuminator-placement.md scope |
| "Glasses mirror the phone 1:1" | True only if not letterboxed; use the **`Presentation` API** on the secondary display | Core premise, calibration validity |
| FOV as a single number | Published FOV is **diagonal**; the calibration module needs horizontal and vertical | Angular error reporting |
| Cost unstated | **EUR 1,370** for a binocular camera pair | Feasibility |

# Hardware summary

One-page overview of the hardware for a Gaze on Glass rig. Every figure here comes from [hardware-reference.md](hardware-reference.md) (specs, with citations) or [bill-of-materials.md](bill-of-materials.md) (prices and purchase order). Those two documents are authoritative; if this page ever disagrees with them, they win.

Specs and prices as researched 2026-07-25. Prices are planning figures, excluding VAT, duty, and shipping.

---

## Pupil Core eye cameras

| Property | Value |
| --- | --- |
| Resolution / rate | 192x192 @ 200 Hz, or 400x400 @ 120 Hz |
| Shutter / latency | Global, 4.5 ms |
| IR illumination | Integrated in the module, dark-pupil. Wavelength unpublished; 850nm is standard |
| Focus | 200 Hz fixed (lens glued); 120 Hz manual |
| Interface | UVC, MJPEG, USB-C. `Pupil Cam 3 ID0` (right), `ID1` (left) |
| Price | EUR 685 each, EUR 1,370 per binocular pair |
| Dimensions | Unpublished. Measure with calipers |
| Pupil's own accuracy (full 3D pipeline) | 0.60 deg accuracy, 0.02 deg precision, 5-point calibration |

- **400x400 @ 120 Hz is the likely operating point.** 120 Hz is plenty for screen pointing, and at 192x192 a 1-pixel centroid error is a large fraction of the image.
- **Standalone connectivity is unverified.** The individual cameras are sold "for upgrading existing 120Hz headsets", which implies they depend on the Core frame's internal wiring and hub. One email to Pupil Labs settles it.

### Camera paths

| Path | Cost | Tradeoff |
| --- | --- | --- |
| A. New Pupil eye cameras | EUR 1,370 | Best hardware; connectivity without the frame unverified |
| B. Complete Pupil Core headset | EUR 3,615 (EUR 2,995 academic) | USB path known to work; most of the headset is discarded |
| C. DIY webcams | ~$60 to $100 | Modified Logitech C525/C512 or Microsoft HD-6000 per the [DIY guide](https://docs.pupil-labs.com/core/diy/). Rolling shutter, lower rate, manual focus. The right way to prototype the software first |

## VITURE glasses

| Model | Price | Per eye | Refresh | FOV diag / H / V |
| --- | --- | --- | --- | --- |
| Luma | $399 | 1920x1200 | 120 Hz | 50 / ~45 / ~29 deg |
| Luma Pro | $499 | 1920x1200 | 120 Hz | 52 / ~45 / ~29 deg |
| Luma Ultra | $599 | 1920x1200 | 120 Hz | 52 / ~45 / ~29 deg |
| Pro (discontinued) | | 1920x1080 | 120 Hz | ~46 / ~41 / ~23 deg |
| One (discontinued) | | 1920x1080 | 60 Hz | 43 / ~38 / ~22 deg |

- **Luma at $399 is the rational pick.** Display geometry is identical across the Luma line; brightness and dimming do nothing for tracking.
- No battery: budget ~5 W from the host.
- Published FOV is diagonal. Pass horizontal and vertical to calibration.
- Do not mirror the phone. Render with the `Presentation` API at the glasses' native resolution, or letterboxing breaks the screen-space premise.
- DP Alt Mode lane count (2 or 4) is unpublished. [Gate 1](gate-1-usb-enumeration-test.md) finds out.

## Phone and hub

- **Phone:** DP Alt Mode that works on the firmware you will run. Uncommon: mostly Samsung Galaxy S/Note flagships, some Sony and gaming phones. Stock OEM firmware; no root or custom ROM needed, and custom ROMs are a documented cause of broken video out. A Samsung flagship on One UI is the safest choice.
- **Hub:** specified by behaviour, not part number. It must pass DP video through, keep downstream USB data working while video is active, and accept PD input. Spec sheets are unreliable here; expect to try more than one.
- **The Gate 1 risk is isochronous over-reservation, not throughput.** Actual payload is ~59 Mbps per eye at 192x192 @ 200 Hz and ~154 Mbps at 400x400 @ 120 Hz uncompressed, well within 480 Mbps for two eyes. The lever is the bandwidth factor exposed by Android UVC libraries.

## Android capture path

- Java `UsbDeviceConnection` cannot do isochronous transfers. Native libusb + libuvc over usbfs is mandatory; no kernel UVC driver needed.
- AOSP's external camera HAL caps at 30 fps @ 640x480. Not usable.
- Libraries: **ernestp/AndroidUSBCamera** (maintained, default) or shiyinghan/UVCAndroid. saki4510t/UVCCamera is dormant but is the bandwidth-factor reference. pupil-labs/libuvc is worth reading.
- OpenCV 4.14 / 5.0, `16kb-page-fix` Android SDK variant.
- `CAMERA` permission still required on Android 9+. A `USB_DEVICE_ATTACHED` filter removes the per-connect permission dialog.
- 200 Hz binocular leaves a 5 ms budget for two MJPEG decodes plus detection. [Gate 2](gate-2-on-device-detection.md) measures it.

## Mount

Details in [../mount/README.md](../mount/README.md). Geometry is untested; every dimension is a starting guess.

- Rigid clamp, deliberately unlike Pupil's 6-DOF ball-joint arm. Slippage is the one real weakness of 2D calibration, and the mount is what prevents it.
- Defaults: `cam_elevation` 38 deg (30 to 45 useful), `cam_yaw` 12 deg, `clamp_gap` 0.25 mm. `arm_drop` and `arm_forward` need iteration.
- PETG or ABS, not PLA. 4 perimeters, 40%+ infill, layer lines across the arm. M3 screw and nut per side, ~100 g filament.
- pupil-geometry is LGPL-3.0: measure it, do not copy it, since `mount/` is CERN-OHL-S.
- Scale reference: Pupil's Quest 3 add-on module mount is 30 x 39 x 19 mm, 10 g.

## IR and birdbath optics

Details in [ir-illumination-and-optics.md](ir-illumination-and-optics.md).

- Integrated illumination means camera aim is illumination aim: one lever, three constraints.
- The birdbath combiner reflects near-IR. Failure modes: direct reflection into the lens, ghost glints, uneven illumination at corner gaze.
- Mitigations: camera below the combiner angled up, rotate empirically while watching the feed, add a small printed baffle.
- Before printing, hand-hold the camera and check all nine calibration targets: pupil darkest, glint on the iris, no combiner reflection.
- DIY builds: lowest power that thresholds cleanly, diffused, several weak emitters over one bright one.

## Purchase order

1. Hub, two cheap UVC webcams, PD charger (~$80). Run Gate 1. If two cameras will not stream alongside video, **stop**.
2. Glasses, if not owned ($399 to $599).
3. Optional DIY/cheap IR cameras (~$60 to $100). Pass Gate 2 before buying the good cameras.
4. Email Pupil Labs about standalone camera connectivity.
5. Pupil Core eye cameras (EUR 1,370).
6. Calipers, filament, fasteners (~$35). Measure, then iterate the mount.

| Scenario | Approximate cost |
| --- | --- |
| Testing only, glasses and phone owned | ~$80 |
| Path A, glasses owned | EUR 1,370 + ~$115 |
| Path A, buying Luma | EUR 1,370 + ~$515 |
| Path C, buying Luma | ~$615 |
| Path B, buying Luma | EUR 3,615 + ~$515 |

## Still unknown

1. VITURE DP lane count. Settled by Gate 1.
2. Pupil eye camera dimensions. Calipers, once in hand.
3. Whether standalone eye cameras connect without the Core frame. One email to Pupil Labs.

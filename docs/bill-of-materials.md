# Bill of materials

Everything needed to build one binocular Gaze on Glass rig, with prices, sources, and the order to buy them in.

Prices checked 2026-07-25 and quoted in the vendor's own currency. They move, and they exclude VAT, duty, and shipping. Treat them as planning figures, not quotes.

**Do not buy this list top to bottom.** The purchase order at the end exists because two of the largest line items are only worth buying after cheap tests have passed. Skipping that sequence risks spending four figures on a design that fails at the USB layer.

---

## Decisions to make first

### Which VITURE model

All of them work as a display. The choice affects calibration geometry and nothing else architecturally.

| Model | Price | Per-eye | Refresh | Diagonal FOV | Notes |
| --- | --- | --- | --- | --- | --- |
| [Luma](https://www.viture.com/luma) | $399 | 1920x1200 | 120 Hz | 50 deg | Cheapest current model |
| [Luma Pro](https://www.viture.com/luma) | $499 | 1920x1200 | 120 Hz | 52 deg | 1000 nits, electrochromic dimming |
| [Luma Ultra](https://www.viture.com/luma) | $599 | 1920x1200 | 120 Hz | 52 deg | 1500 nits |
| VITURE One / Pro | discontinued / used | 1920x1080 | 60 / 120 Hz | 43 to 46 deg | Fine if you already own one |

Any of these is adequate. If buying new for this project specifically, **Luma at $399 is the rational pick**: the Ultra's extra brightness and the Pro's dimming do not improve gaze tracking, and the display geometry is identical across the three. Spend the difference on the mount iterations you will actually need.

Whichever you pick, record the model in the calibration profile `metadata`. The FOV differs and the calibration is display-specific.

### Which eye camera path

This is the expensive decision, and the three paths differ by more than an order of magnitude.

| Path | Cost | What you get | Risk |
| --- | --- | --- | --- |
| **A. New Pupil Core eye cameras** | **EUR 685 each, EUR 1,370 pair** | 192x192 @ 200 Hz or 400x400 @ 120 Hz, global shutter, integrated IR, 4.5 ms latency | **Connection is unverified. See the warning below.** |
| **B. Complete Pupil Core headset** | EUR 3,615 (EUR 2,995 academic) | Same cameras, plus frame, world camera, internal USB hub, connector clip | Expensive, and you discard most of it. But the USB path is known to work. |
| **C. DIY webcams** | ~$60 to $100 | Modified Logitech C525/C512 or Microsoft HD-6000 per the [Pupil DIY guide](https://docs.pupil-labs.com/core/diy/) | Rolling shutter, lower rate, manual focus, you solder IR LEDs and replace the IR-cut filter yourself |

> **Verify before ordering path A.** Pupil Labs list the individual eye cameras as being "for upgrading existing 120Hz headsets", and no tools are required to fit them. That strongly implies they are designed to plug into the Pupil Core frame's **internal wiring and USB hub**, which this project does not have. Whether a standalone camera ships with a cable that reaches a host directly is not documented anywhere I could find.
>
> **Ask Pupil Labs directly before spending EUR 1,370.** The specific question: does the individually-sold eye camera include a USB connection usable without the Pupil Core headset frame, and if not, what is needed. This single email is the highest-value thing on this page.

If path A turns out to require the frame, the honest options are path B, path C, or a used Pupil Core headset. Path C is also the sane way to prototype the software before committing to either.

---

## The list

### Core

| # | Item | Spec that matters | Qty | Unit | Source |
| --- | --- | --- | --- | --- | --- |
| 1 | VITURE XR glasses | DP Alt Mode video in, any Luma-series | 1 | $399 to $599 | [viture.com](https://www.viture.com/luma) |
| 2 | Pupil Core eye camera, left | 192x192 @200Hz / 400x400 @120Hz, integrated IR | 1 | EUR 685 | [Pupil Labs](https://pupil-labs.com/products/core/accessories) |
| 3 | Pupil Core eye camera, right | as above | 1 | EUR 685 | [Pupil Labs](https://pupil-labs.com/products/core/accessories) |
| 4 | Android phone | **DP Alt Mode**, USB host, stock firmware | 1 | owned, or varies | see below |
| 5 | USB-C hub | DP Alt Mode passthrough **and** downstream USB data **and** PD input | 1 | ~$30 to $60 | see below |

### Mount

| # | Item | Spec that matters | Qty | Unit |
| --- | --- | --- | --- | --- |
| 6 | Filament | **PETG or ABS.** Not PLA: it creeps near a warm face, and creep is calibration drift with a 20-minute time constant. | ~100 g | ~$5 |
| 7 | M3 socket screws | 10 to 16 mm, clamp closure | 2 | ~$1 |
| 8 | M3 nuts | captive in the clamp pocket | 2 | ~$1 |

Print at 4 perimeters, 40%+ infill, with layer lines running **across** the arm rather than along it. Budget several iterations: `cam_elevation`, `cam_yaw`, and `arm_drop` will not be right first time. See [../mount/README.md](../mount/README.md).

### Test equipment (buy first, see sequencing)

| # | Item | Why | Qty | Unit |
| --- | --- | --- | --- | --- |
| 9 | Cheap UVC webcams | **Two.** Gate 1 is about whether a *second* camera can open, so one proves nothing. Do not risk the Pupil cameras on the first test. | 2 | ~$15 each |
| 10 | USB-C PD charger | The glasses draw ~5 W with no battery of their own, on top of cameras and phone | 1 | ~$20 |
| 11 | Calipers | Camera and frame dimensions are unpublished; the mount cannot be parameterised without measuring | 1 | ~$25 |

---

## Notes on the two items with no fixed part number

### The phone

The binding requirement is **DP Alt Mode that works in the firmware you will run**. This is uncommon and frequently unlisted on spec sheets: mostly Samsung Galaxy S/Note flagships, some Sony, Huawei, and gaming phones. Budget and mid-range handsets usually lack it.

Stock OEM firmware. Nothing here needs root or a custom ROM, and custom ROMs are a documented cause of DP video out breaking (open LineageOS issues exist for the OnePlus 9 Pro and Samsung S10e). A Samsung flagship on One UI is the safest choice, since DeX means the external-display path is well travelled.

Also needs enough compute headroom for two MJPEG decodes plus detection inside a 5 to 8 ms budget. Any recent flagship should manage; this is what Gate 2 measures.

### The hub

Specified by behaviour, not by part number, and deliberately so: **hub spec sheets are unreliable for exactly this scenario**, and which hubs pass is the substance of [Gate 1](gate-1-usb-enumeration-test.md). Naming a product here that I have not tested would be worse than naming none.

What it must do:
- Pass DP Alt Mode video through to the glasses
- Expose downstream USB data ports **that still work while video is active**
- Accept PD input for charging, since the phone is powering glasses and cameras

Buy one that claims all three, from somewhere with a returns policy, and expect to try more than one. If several fail identically, the constraint is the phone's USB controller rather than the hubs.

---

## Purchase order

Each step gates the next. The point is to spend the cheap money before the expensive money.

1. **Hub + two cheap webcams + PD charger** (~$80). You may already own the glasses and phone. Run [Gate 1](gate-1-usb-enumeration-test.md).
   - If two webcams will not stream alongside video, and no hub or bandwidth-factor setting fixes it, **stop**. The single-device design does not work on your hardware, and no later purchase rescues it.
2. **Glasses**, if not already owned ($399 to $599). Needed to complete Gate 1 properly.
3. **DIY or cheap IR-capable cameras** (~$60 to $100), optional but recommended. Prove the detection pipeline and [Gate 2](gate-2-on-device-detection.md) before buying the good cameras. The calibration module and detector do not care where the pupil centroid came from.
4. **Email Pupil Labs** about standalone camera connectivity. Free, and it is the difference between path A and path B.
5. **Pupil Core eye cameras** (EUR 1,370). Only after 1 to 4.
6. **Calipers, filament, fasteners** (~$35). Measure the cameras once they arrive, then iterate the mount.

## Rough totals

| Scenario | Approximate cost |
| --- | --- |
| Testing only, glasses and phone already owned | **~$80** |
| Full build, path A, glasses owned | **EUR 1,370 + ~$115** |
| Full build, path A, buying Luma | **EUR 1,370 + ~$515** |
| Full build, path C (DIY cameras), buying Luma | **~$615** |
| Full build, path B (complete headset), buying Luma | **EUR 3,615 + ~$515** |

Mixed currencies are left unconverted on purpose; apply your own rate and add VAT, duty, and shipping, which on the Pupil order will not be trivial.

The honest summary: **the eye cameras are the project**, at roughly three times the cost of everything else combined. Every step of the purchase order above exists to make sure that money is spent only after the design is known to work.

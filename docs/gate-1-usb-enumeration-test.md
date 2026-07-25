# Gate 1: USB enumeration test

**Question:** can the phone drive DP Alt Mode video out to the VITURE glasses and stream two UVC cameras in, through one USB-C port, at the same time?

This is the first thing to do and it needs no code. If it fails, the single-device design fails at the hardware layer and everything else in this repo is premature.

Component specs and citations behind the numbers here: [hardware-reference.md](hardware-reference.md).

## Two separate things can go wrong

### 1. Lane split (probably fine)

DP Alt Mode and USB data share the four high-speed lane pairs in a USB-C connector:

- **2-lane DP** (pin assignment D/F): two pairs for video, two left for USB 3.x. Both survive.
- **4-lane DP** (pin assignment C/E): all four go to video, USB data falls back to the USB 2.0 pins, capping at 480 Mbps.

VITURE does not publish which their glasses negotiate. Arithmetic suggests 2-lane is enough for them: 1920x1200 @ 120Hz at 24bpp is about 6.6 Gbps of pixel data, roughly 8 Gbps encoded, and two HBR3 lanes carry about 13 Gbps effective. A vendor that wanted to keep USB 3 alive would choose 2-lane. Whether they did is what you are measuring.

Even 4-lane is survivable on paper. Two eye streams at 192x192 @ 200Hz are about 59 Mbps per eye uncompressed, well under that in MJPEG. Two at 400x400 @ 120Hz are about 154 Mbps per eye uncompressed. Both fit inside 480 Mbps.

### 2. Isochronous bandwidth over-reservation (the real risk)

This is what actually breaks multi-camera USB setups, and it is not about how much data the cameras send.

UVC video streams over **isochronous** transfers, which reserve guaranteed bus bandwidth in advance. The host reads `dwMaxPayloadTransferSize` from the camera's interface descriptor and selects an alternate setting with at least that much bandwidth. **Cameras routinely overstate this figure by 4x or more.** Measured example: cameras requesting 3060 bytes per microframe, about 195 Mbps, to stream 320x240 MJPEG at 25fps, which genuinely needs about 46 Mbps. Two of those cannot coexist on one bus.

Stacking constraints:

- USB 2.0 Hi-Speed reserves at most 80% of the bus for periodic transfers: about **384 Mbps**, not 480.
- The kernel cannot estimate bandwidth for **compressed** formats, so the `UVC_QUIRK_FIX_BANDWIDTH` workaround (which recomputes it for uncompressed video) does not help MJPEG cameras. Pupil cameras stream MJPEG.

**Pupil Core is known to hit this.** Pupil Labs' own Vive add-on documentation says that running dual 200Hz eye cameras requires disabling the headset's built-in camera or dropping it to 30Hz, and recommends running a separate USB lane to the host for full performance.

The symptom is not a slow stream. It is the second camera failing to open, typically ENOSPC / "No space left on device", or one camera working perfectly and the other refusing.

## What you need

- Android phone with USB host **and working DP Alt Mode video out**. Stock firmware; root and custom ROMs are not needed and custom ROMs frequently break DP output. Verify video out actually works on your handset before anything else: most phones lack DP Alt Mode entirely, and many spec sheets do not mention it either way.
- USB-C hub claiming DP Alt Mode passthrough **and** downstream USB data ports
- VITURE XR glasses
- **Two** cheap UVC webcams. Two is the test. One camera proves almost nothing, because over-reservation only bites on the second. Do not risk the EUR 685-each Pupil cameras on the first attempt, and do not let a Pupil-specific quirk get mistaken for a topology failure.
- Powered hub or PD passthrough plus a charger. The glasses alone draw about 5W (VITURE's own dock supplies 5V/1A per glasses port), before the cameras and the phone's own load.
- ADB over Wi-Fi, since the USB port is occupied

## Setup ADB over Wi-Fi first

```bash
# with the phone on USB, before plugging in the hub
adb tcpip 5555
adb shell ip route            # find the phone's IP
# unplug, then
adb connect <phone-ip>:5555
```

## Procedure

1. Hub into the phone. Glasses into the hub's DP/video output. Confirm the glasses show a display.

2. Note whether the image is **letterboxed**. If the phone is mirroring a 20:9 panel onto a 16:10 display, you will see bars. That is expected and it is why the app renders through the `Presentation` API rather than relying on mirroring. Record what you see; it tells you the negotiated display mode.

3. With video confirmed working, plug in the **first** webcam. Check enumeration:

```bash
adb shell dmesg -w                              # watch live while plugging in
adb shell lsusb                                 # if present on the ROM
adb shell ls -l /dev/video*                     # UVC device nodes
adb shell cat /sys/kernel/debug/usb/devices     # detailed, incl. negotiated speed
```

4. Record the negotiated speed. In `dmesg`:

```
usb 1-1: new high-speed USB device number 4 using xhci-hcd      <- USB 2.0, 480 Mbps, 4-lane DP
usb 2-1: new SuperSpeed USB device number 3 using xhci-hcd      <- USB 3.x, 2-lane DP
```

5. Confirm frames actually flow, not just enumeration. Enumeration without streaming is a common and distinct failure. Any UVC viewer that opens the device will do; a USB camera app from F-Droid is the quickest route.

6. **Plug in the second webcam and stream both at once.** This is the actual gate. If the second fails to open while the first is streaming, you have hit over-reservation, not a bandwidth wall.

7. Repeat with PD charging attached and without. Current draw is a plausible failure mode that presents as a data failure.

## Record the results

Fill this in and keep it. It is the single most useful artifact for anyone else attempting this build, and it is the thing no vendor publishes.

| Item | Value |
| --- | --- |
| Phone / SoC | |
| Android version / firmware | |
| Hub make and model | |
| VITURE model | |
| Glasses show a display | yes / no |
| Display letterboxed | yes / no |
| Reported external display resolution | |
| One webcam enumerates with video active | yes / no |
| Negotiated USB speed | high-speed / SuperSpeed |
| One webcam streams | yes / no |
| **Two webcams stream simultaneously** | yes / no |
| Error if the second fails | |
| Behaviour with PD charging attached | |

## Interpreting the outcome

**Two cameras stream, SuperSpeed.** Best case, 2-lane DP. Proceed to Gate 2 with no bandwidth concerns.

**Two cameras stream, high-speed.** Expected case, 4-lane DP. Proceed, but MJPEG is mandatory rather than optional, and re-verify once the real Pupil cameras are attached, since their declared reservation may differ from a cheap webcam's.

**One camera streams, the second fails to open.** Over-reservation, most likely. This is recoverable, and it is why the app uses a libuvc-based library rather than the platform camera stack: those libraries expose a **bandwidth factor** that overrides the requested reservation. Before concluding failure, try: a lower bandwidth factor, a lower resolution or framerate, MJPEG rather than uncompressed, and the two cameras on different ports of the hub. Note that 400x400 @ 120Hz may reserve *less* than 192x192 @ 200Hz depending on how the firmware computes it, so test both rather than assuming the smaller mode is safer.

**Nothing enumerates.** Try a different hub before concluding anything. Hub behaviour in this specific scenario (DP Alt Mode plus downstream data) varies enormously and spec sheets are unreliable. If several hubs fail identically, the phone's USB controller or the ROM's host-mode configuration is the constraint.

**If it cannot be made to work:** the fallback is a second USB source for the cameras, which sacrifices the single-device property that motivates this design. That is a different project, and worth knowing now rather than after building an app.

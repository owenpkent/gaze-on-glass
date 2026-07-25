# Gate 1: USB enumeration test

**Question:** can the phone drive DP Alt Mode video out to the VITURE glasses and enumerate a UVC camera in, through one USB-C port, at the same time?

This is the first thing to do and it needs no code. If it fails, the single-device design fails at the hardware layer and everything else in this repo is premature.

## Why it might not work

DP Alt Mode and USB data share the four high-speed lane pairs in a USB-C connector. The split depends on what the display sink negotiates:

- **2-lane DP**: two pairs for video, two left for USB 3.x. Both video and full-speed data survive. Comfortable.
- **4-lane DP**: all four pairs go to video, and USB data falls back to the USB 2.0 pins (D+/D-), capping at 480 Mbps.

4-lane is the more likely case for a display device and is still probably fine. Two 800x600 MJPEG streams at 30Hz are on the order of 20 to 60 Mbps combined, comfortably inside 480 Mbps. The risk is not raw bandwidth, it is whether the hub and the phone's USB controller expose a working downstream data path *at all* while DP is active, and whether the phone can supply enough current for glasses plus cameras.

## What you need

- LineageOS phone with USB host support
- USB-C hub that claims DP Alt Mode passthrough **and** downstream USB data ports
- VITURE XR glasses
- Any cheap UVC webcam (this is the point: do not risk the Pupil Core cameras on the first test, and do not let a Pupil-specific quirk get mistaken for a topology failure)
- Powered hub or a hub with PD passthrough, plus a charger. Try unpowered too, but expect current to matter.
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

1. Hub into the phone. Glasses into the hub's DP/video output. Confirm the glasses show a mirrored display.
2. With video confirmed working, plug the webcam into a downstream data port on the hub.
3. Check enumeration:

```bash
adb shell dmesg -w              # watch live while plugging in
adb shell lsusb                 # if present on the ROM
adb shell ls -l /dev/video*     # UVC device nodes
adb shell cat /sys/kernel/debug/usb/devices   # detailed, incl. negotiated speed
```

4. Record the negotiated speed. In `dmesg`, look for lines like:

```
usb 1-1: new high-speed USB device number 4 using xhci-hcd      <- USB 2.0, 480 Mbps
usb 2-1: new SuperSpeed USB device number 3 using xhci-hcd      <- USB 3.x
```

5. Confirm frames actually flow, not just enumeration. Enumeration without streaming is a real and common failure. Any UVC viewer app that opens `/dev/video*` will do, or use a USB Camera app from F-Droid.

6. Repeat with **two** webcams if you have them. Two cameras is the real configuration and it stresses bandwidth and current in a way one camera does not.

7. Repeat the whole test with the phone charging through the hub's PD input, and without. Current draw is a plausible failure mode that looks like a data failure.

## Record the results

Fill this in and keep it. It is the single most useful artifact for anyone else attempting this build.

| Item | Value |
| --- | --- |
| Phone / SoC | |
| LineageOS version, kernel | |
| Hub make and model | |
| Glasses show mirrored display | yes / no |
| Webcam enumerates with video active | yes / no |
| Negotiated USB speed | high-speed / SuperSpeed |
| Frames stream | yes / no |
| Two cameras simultaneously | yes / no |
| Behaviour with PD charging attached | |

## Interpreting the outcome

**Enumerates at SuperSpeed and streams.** Best case, 2-lane DP. Proceed to Gate 2 with no bandwidth concerns.

**Enumerates at high-speed and streams.** Expected case, 4-lane DP. Proceed to Gate 2, but plan on MJPEG rather than uncompressed YUV, and re-check total bandwidth once both real cameras are attached. Uncompressed 800x600 YUY2 at 30Hz is roughly 230 Mbps per eye, so two eyes uncompressed will not fit and MJPEG becomes mandatory, not optional.

**Enumerates but does not stream.** Usually bandwidth, current, or a hub that advertises more than it delivers. Try: a powered hub, a lower camera resolution, one camera instead of two, a different hub.

**Does not enumerate at all.** Try a different hub before concluding anything. Hub quality in this specific scenario (DP Alt Mode plus downstream data) varies enormously and the spec sheet is not reliable. If several hubs fail identically, the phone's USB controller or the ROM's host-mode configuration is the constraint.

**If it cannot be made to work:** the fallback is a second USB source for the cameras, which sacrifices the single-device property that motivates this design. That is a different project, and worth knowing early rather than after building an app.

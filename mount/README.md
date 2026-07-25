# Rigid eye-camera mount

Parametric OpenSCAD source for clamping Pupil Core eye cameras to a VITURE XR frame.

Status: **untested geometry**. Every dimension in `eye_camera_mount.scad` is a starting guess, not a measurement. Nothing here has been printed against real hardware yet. Treat it as a parameterized shape to correct, not a part to trust.

## Why this is load-bearing

2D calibration has exactly one real weakness: slippage. If the camera moves relative to the eye after calibration, the polynomial maps the wrong pupil position to the wrong screen point, and nothing downstream can detect that it happened. pye3d exists largely to model this away in software. This project chooses instead to prevent it in hardware, which means the mount is not an accessory, it is the mechanism that makes the whole 2D approach valid.

So: rigidity over elegance, clamped over friction-fit, thicker arm over lighter part.

## Build

```bash
openscad -D 'side="left"'  -o mount_left.stl  eye_camera_mount.scad
openscad -D 'side="right"' -o mount_right.stl eye_camera_mount.scad
```

Open the file directly in the OpenSCAD GUI to preview both sides with a ghosted frame rail for clearance checking.

STLs are not committed. They are derived artifacts and they would be wrong for anyone whose frame differs, which is everyone until the parameters are validated.

## Parameters that matter

Grouped as customizer sections in the source.

**Frame interface.** `frame_width`, `frame_height`, `frame_corner_r` are the cross-section of the rail the clamp grips. Measure with calipers at the exact point you intend to clamp; the VITURE arm is not a constant section. `clamp_gap` (default 0.25mm) is the slide-on clearance: reduce it before you reduce anything else if the clamp feels loose, since a loose clamp is drift.

**Camera pocket.** `cam_body_w/h/d` are the Pupil Core module body. `cam_lens_d` is the lens bore. `cam_cable_w` is the cable exit slot.

Pupil Labs do not publish eye camera dimensions, so these must be measured. They do publish mount geometry at [pupil-labs/pupil-geometry](https://github.com/pupil-labs/pupil-geometry) (DIY set, headset triangle mount, ball-joint arm, arm extender), stating that "by releasing the mounts as example geometry we automatically document the interface" and that you should take measurements from them for your own mounts. That is the best available reference for the camera-side interface.

**License caution:** pupil-geometry is **LGPL-3.0**. Measuring their geometry to determine an interface is fine. Copying or adapting their model into this repo would make the result a derivative work under LGPL-3.0, which conflicts with the CERN-OHL-S license this directory uses. Keep this mount an independent design that mates with a measured interface.

For scale, Pupil Labs' own Quest 3 add-on module mount is 30 x 39 x 19 mm at 10 g including the module, which is roughly what this mount has to carry per side.

**Aim geometry, the part that needs iteration.** `cam_elevation` (default 38 degrees) is the up-tilt from horizontal; 30 to 45 is the useful band. `cam_yaw` (default 12 degrees) angles the camera inward toward the nose. `arm_drop` and `arm_forward` place the camera in space relative to the clamp. These four are what you will actually spend prints on.

**Rigidity.** `arm_thickness` and `arm_width` set the arm cross-section. Under-sizing these is the single most likely way to produce a mount that looks fine and tracks badly.

## Printing

- PETG or ABS over PLA. The mount sits next to a face, in a warm room, sometimes in a car. PLA creeps, and creep in this part is calibration drift with a long time constant, which is the most annoying failure mode to diagnose.
- Print the arm so layer lines run across its length, not along it. A part that delaminates at the arm root fails in exactly the direction that matters.
- 4 perimeters, 40%+ infill. This part is small; the material cost of over-building it is negligible against the cost of a recalibration every twenty minutes.
- No supports needed if the camera pocket opens upward on the plate.
- M3 screw and nut per side for the clamp. Full parts list: [../docs/bill-of-materials.md](../docs/bill-of-materials.md).

## The clearance problem

Birdbath optics sit close to the eye, and that is the hard constraint. The camera must see the pupil from below the combiner without appearing in the display path or touching the user's cheek. Expect several iterations of `cam_elevation` and `arm_drop` before you get a view that contains the whole pupil across the full range of gaze angles, including the extreme corners of the screen where the eyelid starts to occlude.

A useful shortcut: before printing anything, hold the bare camera by hand at the intended position and watch the raw feed while looking around the display. If you cannot find a hand-held position that keeps the pupil in frame at all nine calibration targets, no amount of printing will fix it, and the geometry needs rethinking.

Two things make the aim harder than it looks. The camera is **fixed focus** at 200Hz (the lens is glued; only the 120Hz cameras focus manually), so working distance is a hard constraint rather than something you tune afterwards. And the module's IR illumination is integrated, so the same angle that frames the pupil also determines whether the birdbath combiner reflects the illuminator back into its own lens.

Note the deliberate divergence from Pupil's own design here: the Core headset mounts eye cameras on a sliding arm with a 6-DOF ball joint, tensioned so the camera can be moved by hand. That is right for a research device used across many faces, and wrong for this one. Adjustability and calibration stability are in direct tension, and this project has already traded slippage robustness away in software, so it cannot afford to give any back in hardware. Set the angle parametrically, print it, and let it be rigid.

## IR illumination

See [../docs/ir-illumination-and-optics.md](../docs/ir-illumination-and-optics.md). Pupil Core cameras have **IR illumination integrated into the module**, so the mount's camera angle is also the illumination angle: one lever, three constraints. The birdbath coating is reflective in near-IR and will happily bounce the module's own illumination back into its own lens. A small baffle shielding the module from throwing light forward is cheap to add here and does more than any amount of software.

## License

CERN-OHL-S v2 ([LICENSE](LICENSE)), which is the strongly-reciprocal open hardware license: if you distribute a modified mount, or hardware made from one, publish the modified source. Code elsewhere in the repo is Apache-2.0; the difference is deliberate.

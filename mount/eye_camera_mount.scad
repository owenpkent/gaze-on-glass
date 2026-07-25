// Gaze on Glass: rigid eye-camera mount for VITURE XR glasses.
//
// Parametric on purpose. Every dimension below is a guess until measured against
// your own frame and camera, and the whole point of shipping source rather than
// an STL is that you can correct them. Measure, adjust, print, repeat.
//
// Licensed CERN-OHL-S v2. See LICENSE in this directory.
//
// Render one side:   openscad -D 'side="left"'  -o mount_left.stl  eye_camera_mount.scad
//                    openscad -D 'side="right"' -o mount_right.stl eye_camera_mount.scad
// Preview both:      openscad eye_camera_mount.scad   (with show_both = true)

/* [Which part] */
// "left", "right", or "both" for a side-by-side preview
side = "both";
show_glasses_stub = true;   // ghost the frame rail, to eyeball clearance

/* [Frame interface - MEASURE THESE] */
// Cross-section of the VITURE frame rail the clamp grips.
frame_width      = 6.0;   // mm, horizontal thickness of the rail
frame_height     = 9.0;   // mm, vertical height of the rail
frame_corner_r   = 1.5;   // mm, rail corner radius
clamp_length     = 18.0;  // mm, how far along the rail the clamp grips
clamp_wall       = 2.4;   // mm, clamp wall thickness
clamp_gap        = 0.25;  // mm, clearance so it slides on. Reduce for a tighter grip.
clamp_opening    = 3.0;   // mm, width of the split the screw closes

/* [Camera - MEASURE THESE] */
// Pupil Core eye camera module body. Rectangular pocket, camera looks along +Z.
cam_body_w       = 12.0;  // mm
cam_body_h       = 12.0;  // mm
cam_body_d       = 8.0;   // mm, depth of the pocket
cam_lens_d       = 6.5;   // mm, lens clearance bore
cam_wall         = 2.0;   // mm, pocket wall thickness
cam_cable_w      = 6.0;   // mm, cable exit slot width
cam_retain_lip   = 0.8;   // mm, lip that stops the module falling forward

/* [Aim geometry - THE PART THAT NEEDS ITERATION] */
// Camera sits below the birdbath combiner and looks up at the eye.
cam_elevation    = 38;    // deg, up-tilt from horizontal. 30 to 45 is the useful band.
cam_yaw          = 12;    // deg, inward toward the nose. Positive = toward the eye.
arm_drop         = 22.0;  // mm, how far below the frame rail the camera sits
arm_forward      = 6.0;   // mm, offset toward the face (+) or away (-)
arm_thickness    = 4.5;   // mm, arm cross-section. Rigidity lives here.
arm_width        = 7.0;   // mm

/* [Fasteners] */
screw_d          = 3.0;   // mm, M3 clamp screw
screw_head_d     = 6.0;   // mm
nut_af           = 5.5;   // mm, M3 nut across flats
nut_t            = 2.5;   // mm, nut pocket depth

/* [Print] */
$fn = 48;
eps = 0.01;

// ---------------------------------------------------------------------------
// Modules
// ---------------------------------------------------------------------------

// Rounded rectangular prism, centered in X and Y, extruded along Z.
module rrect(w, h, d, r) {
    linear_extrude(height = d)
        offset(r = r) offset(r = -r)
            square([w, h], center = true);
}

// C-clamp that grips the frame rail. Split on the outboard side, closed by a screw.
module frame_clamp() {
    inner_w = frame_width + 2 * clamp_gap;
    inner_h = frame_height + 2 * clamp_gap;
    outer_w = inner_w + 2 * clamp_wall;
    outer_h = inner_h + 2 * clamp_wall;

    difference() {
        rrect(outer_w, outer_h, clamp_length, 1.5);

        // Rail pocket.
        translate([0, 0, -eps])
            rrect(inner_w, inner_h, clamp_length + 2 * eps, frame_corner_r);

        // Split, so the clamp can actually close.
        translate([outer_w / 2 - clamp_wall / 2, 0, -eps])
            cube([clamp_wall * 2, clamp_opening, clamp_length + 2 * eps], center = false);

        // Screw across the split.
        translate([outer_w / 2 + clamp_wall / 2, -outer_h, clamp_length / 2])
            rotate([-90, 0, 0]) {
                cylinder(d = screw_d, h = outer_h * 2);
                // Head counterbore.
                translate([0, 0, 0])
                    cylinder(d = screw_head_d, h = outer_h - clamp_opening / 2);
            }

        // Captive nut on the far side.
        translate([outer_w / 2 + clamp_wall / 2, outer_h / 2 - nut_t, clamp_length / 2])
            rotate([-90, 0, 0])
                cylinder(d = nut_af / cos(30), h = nut_t, $fn = 6);
    }
}

// Camera pocket. Lens bore along +Z, cable slot out the back.
module camera_pocket() {
    outer_w = cam_body_w + 2 * cam_wall;
    outer_h = cam_body_h + 2 * cam_wall;
    outer_d = cam_body_d + cam_wall;

    difference() {
        rrect(outer_w, outer_h, outer_d, 1.5);

        // Module cavity, open at the back.
        translate([0, 0, -eps])
            rrect(cam_body_w, cam_body_h, cam_body_d + eps, 0.5);

        // Lens bore through the front face.
        translate([0, 0, cam_body_d - eps])
            cylinder(d = cam_lens_d, h = cam_wall + 2 * eps);

        // Cable exit, out the bottom.
        translate([0, -outer_h / 2 - eps, cam_body_d / 2])
            cube([cam_cable_w, cam_wall * 3, cam_body_d], center = true);
    }

    // Retaining lip at the mouth of the pocket, so the module cannot drop out.
    translate([0, 0, -cam_retain_lip])
        difference() {
            rrect(outer_w, outer_h, cam_retain_lip, 1.5);
            translate([0, 0, -eps])
                rrect(cam_body_w - 1.2, cam_body_h - 1.2, cam_retain_lip + 2 * eps, 0.5);
        }
}

// The arm from clamp to camera. Everything about calibration stability is here:
// any flex in this member is drift the software cannot see or correct.
module arm(len) {
    hull() {
        rrect(arm_width, arm_thickness, eps, 1.0);
        translate([0, 0, len])
            rrect(arm_width, arm_thickness, eps, 1.0);
    }
}

// One complete side. mirror_side = -1 flips it for the other eye.
module mount(mirror_side = 1) {
    mirror([mirror_side < 0 ? 1 : 0, 0, 0]) {
        // Clamp, lying along the rail (rail runs along X).
        rotate([0, 90, 0]) frame_clamp();

        // Arm down and forward to the camera.
        arm_len = sqrt(arm_drop * arm_drop + arm_forward * arm_forward);
        arm_angle = atan2(arm_forward, arm_drop);

        translate([0, 0, -frame_height / 2])
            rotate([arm_angle, 0, 0])
                rotate([180, 0, 0])
                    arm(arm_len);

        // Camera at the end of the arm, aimed up and inward at the eye.
        translate([0, arm_forward, -arm_drop - frame_height / 2])
            rotate([0, 0, cam_yaw])
                rotate([90 - cam_elevation, 0, 0])
                    camera_pocket();
    }
}

// Ghost of the frame rail, for clearance checking only. Never printed.
module glasses_stub() {
    %translate([-40, 0, 0])
        rotate([0, 90, 0])
            rrect(frame_width, frame_height, 80, frame_corner_r);
}

// ---------------------------------------------------------------------------
// Output
// ---------------------------------------------------------------------------

if (show_glasses_stub && side == "both") glasses_stub();

if (side == "left")       mount(1);
else if (side == "right") mount(-1);
else {
    translate([-30, 0, 0]) mount(1);
    translate([ 30, 0, 0]) mount(-1);
}

"""Tests for the 2D calibration module.

The synthetic eye model here is deliberately nonlinear: a real pupil moves on a
sphere, so its projection into the camera image is roughly sinusoidal in gaze
angle. A 2nd-order polynomial should absorb that over a display-sized FOV, which
is the entire premise of the design. If these tests fail, the premise is wrong.
"""

from __future__ import annotations

import numpy as np
import pytest

from gaze_calibration import (
    CalibrationProfile,
    Eye,
    FixationCollector,
    PolynomialMapper,
    default_target_grid,
    fit_polynomial_mapper,
    fit_profile,
    load_profile,
    save_profile,
    validate_mapper,
    validate_profile,
)

IMAGE_SIZE = (800, 600)
SCREEN_SIZE = (1920, 1080)
FOV = (36.0, 20.0)


def synthetic_pupil(screen: np.ndarray, eye: Eye = Eye.LEFT) -> np.ndarray:
    """Project normalized screen targets to normalized pupil positions.

    Spherical eye, camera below and off-axis: sinusoidal in gaze angle plus a
    mild cross-axis term from the oblique camera mount.
    """
    sx = np.asarray(screen, dtype=float)[:, 0]
    sy = np.asarray(screen, dtype=float)[:, 1]
    ax = np.deg2rad((sx - 0.5) * FOV[0])
    ay = np.deg2rad((sy - 0.5) * FOV[1])
    sign = 1.0 if eye is Eye.LEFT else -1.0
    px = 0.5 + 0.55 * np.sin(ax) * np.cos(ay) + sign * 0.02
    py = 0.5 + 0.42 * np.sin(ay) + 0.05 * np.sin(ax) * np.sin(ay)
    return np.column_stack([px, py])


def offset_grid(cols: int, rows: int) -> np.ndarray:
    """A validation grid deliberately offset from the calibration grid."""
    xs = np.linspace(0.2, 0.8, cols)
    ys = np.linspace(0.2, 0.8, rows)
    return np.array([(x, y) for y in ys for x in xs], dtype=float)


class TestTargetGrid:
    def test_nine_point_grid_shape_and_bounds(self):
        g = default_target_grid()
        assert g.shape == (9, 2)
        assert g.min() >= 0.1 and g.max() <= 0.9
        assert np.allclose(g[4], [0.5, 0.5])

    def test_grid_is_row_major(self):
        g = default_target_grid(3, 3)
        assert g[0][1] == g[1][1] == g[2][1]

    def test_rejects_degenerate_grid(self):
        with pytest.raises(ValueError):
            default_target_grid(1, 3)
        with pytest.raises(ValueError):
            default_target_grid(3, 3, margin=0.6)


class TestPolynomialFit:
    def test_recovers_a_known_polynomial_exactly(self):
        rng = np.random.default_rng(0)
        pupil = rng.uniform(0.2, 0.8, size=(40, 2))
        cx = np.array([0.1, 1.2, -0.3, 0.4, -0.2, 0.05])
        cy = np.array([-0.05, 0.2, 0.9, -0.1, 0.3, 0.25])
        px, py = pupil[:, 0], pupil[:, 1]
        A = np.column_stack(
            [np.ones_like(px), px, py, px * px, px * py, py * py]
        )
        screen = np.column_stack([A @ cx, A @ cy])

        m = fit_polynomial_mapper(pupil, screen, IMAGE_SIZE)

        assert np.allclose(m.coeffs_x, cx)
        assert np.allclose(m.coeffs_y, cy)
        assert m.residual_rms < 1e-12

    def test_nine_points_generalize_to_held_out_targets(self):
        cal = default_target_grid(3, 3)
        m = fit_polynomial_mapper(synthetic_pupil(cal), cal, IMAGE_SIZE)

        val = offset_grid(4, 4)
        report = validate_mapper(
            m, synthetic_pupil(val), val, screen_size=SCREEN_SIZE, fov_degrees=FOV
        )

        # Under 1 degree on held-out points is the bar the README claims.
        assert report.mean_error_deg < 1.0
        assert report.p95_error_deg < 1.5

    def test_more_points_do_not_hurt(self):
        val = offset_grid(4, 4)
        errs = []
        for n in (3, 4, 5):
            cal = default_target_grid(n, n)
            m = fit_polynomial_mapper(synthetic_pupil(cal), cal, IMAGE_SIZE)
            errs.append(
                validate_mapper(m, synthetic_pupil(val), val, fov_degrees=FOV
                                ).mean_error_deg
            )
        assert errs[-1] <= errs[0] * 1.5

    def test_fit_is_noise_tolerant(self):
        rng = np.random.default_rng(7)
        cal = default_target_grid(5, 5)
        noisy = synthetic_pupil(cal) + rng.normal(0, 0.002, size=(25, 2))
        m = fit_polynomial_mapper(noisy, cal, IMAGE_SIZE)

        val = offset_grid(4, 4)
        report = validate_mapper(m, synthetic_pupil(val), val, fov_degrees=FOV)
        assert report.mean_error_deg < 1.5

    def test_rejects_underdetermined_fit(self):
        cal = default_target_grid(2, 2)
        with pytest.raises(ValueError, match="at least 6"):
            fit_polynomial_mapper(synthetic_pupil(cal), cal, IMAGE_SIZE)

    def test_rejects_shape_mismatch(self):
        with pytest.raises(ValueError):
            fit_polynomial_mapper(np.zeros((9, 2)), np.zeros((8, 2)), IMAGE_SIZE)

    def test_map_accepts_single_point(self):
        cal = default_target_grid(3, 3)
        m = fit_polynomial_mapper(synthetic_pupil(cal), cal, IMAGE_SIZE)
        one = m.map(np.array([0.5, 0.5]))
        assert one.shape == (2,)
        assert np.allclose(one, m.map(np.array([[0.5, 0.5]]))[0])

    def test_pixel_input_matches_normalized_input(self):
        cal = default_target_grid(3, 3)
        pupil = synthetic_pupil(cal)
        pupil_px = pupil * np.array(IMAGE_SIZE, dtype=float)

        m_norm = fit_polynomial_mapper(pupil, cal, IMAGE_SIZE)
        m_px = fit_polynomial_mapper(
            pupil_px, cal, IMAGE_SIZE, normalize_input=True
        )

        assert np.allclose(m_norm.coeffs_x, m_px.coeffs_x)
        assert np.allclose(
            m_px.map_pixels(pupil_px[0]), m_norm.map(pupil[0])
        )


class TestProfile:
    def build(self) -> tuple[CalibrationProfile, np.ndarray]:
        cal = default_target_grid(3, 3)
        return (
            fit_profile(
                {
                    Eye.LEFT: (synthetic_pupil(cal, Eye.LEFT), cal),
                    Eye.RIGHT: (synthetic_pupil(cal, Eye.RIGHT), cal),
                },
                image_size=IMAGE_SIZE,
                screen_size=SCREEN_SIZE,
                fov_degrees=FOV,
                metadata={"mount": "rev-a"},
            ),
            cal,
        )

    def test_binocular_validation_beats_the_bar(self):
        profile, _ = self.build()
        val = offset_grid(4, 4)
        reports = validate_profile(
            profile,
            {
                Eye.LEFT: synthetic_pupil(val, Eye.LEFT),
                Eye.RIGHT: synthetic_pupil(val, Eye.RIGHT),
            },
            val,
        )
        assert set(reports) == {"left", "right", "binocular"}
        assert reports["binocular"].mean_error_deg < 1.0

    def test_binocular_average_beats_a_biased_single_eye(self):
        """Averaging cancels independent per-eye error, which is why we do it."""
        profile, _ = self.build()
        val = offset_grid(4, 4)
        rng = np.random.default_rng(3)
        left = synthetic_pupil(val, Eye.LEFT) + rng.normal(0, 0.004, (16, 2))
        right = synthetic_pupil(val, Eye.RIGHT) + rng.normal(0, 0.004, (16, 2))

        reports = validate_profile(profile, {Eye.LEFT: left, Eye.RIGHT: right}, val)
        worst_eye = max(
            reports["left"].mean_error_norm, reports["right"].mean_error_norm
        )
        assert reports["binocular"].mean_error_norm <= worst_eye

    def test_zero_confidence_eye_is_dropped(self):
        profile, _ = self.build()
        pupil = {
            Eye.LEFT: np.array([0.5, 0.5]),
            Eye.RIGHT: np.array([0.9, 0.9]),
        }
        combined = profile.map_binocular(pupil, confidence={Eye.LEFT: 1.0, Eye.RIGHT: 0.0})
        assert np.allclose(combined, profile.map_eye(Eye.LEFT, pupil[Eye.LEFT]))

    def test_all_eyes_lost_raises(self):
        profile, _ = self.build()
        with pytest.raises(ValueError, match="no eye"):
            profile.map_binocular(
                {Eye.LEFT: np.array([0.5, 0.5])}, confidence={Eye.LEFT: 0.0}
            )

    def test_monocular_profile_is_valid(self):
        cal = default_target_grid(3, 3)
        profile = fit_profile(
            {Eye.RIGHT: (synthetic_pupil(cal, Eye.RIGHT), cal)},
            image_size=IMAGE_SIZE,
        )
        assert profile.eyes == [Eye.RIGHT]
        out = profile.map_binocular({Eye.RIGHT: np.array([0.5, 0.5])})
        assert out.shape == (2,)

    def test_empty_profile_rejected(self):
        with pytest.raises(ValueError, match="at least one eye"):
            CalibrationProfile(mappers={})

    def test_to_pixels(self):
        profile, _ = self.build()
        assert np.allclose(profile.to_pixels([0.5, 0.5]), [960.0, 540.0])

    def test_roundtrip_through_json(self, tmp_path):
        profile, _ = self.build()
        path = save_profile(profile, tmp_path / "profile.json")
        loaded = load_profile(path)

        assert loaded.screen_size == profile.screen_size
        assert loaded.fov_degrees == profile.fov_degrees
        assert loaded.metadata == {"mount": "rev-a"}
        probe = np.array([0.42, 0.61])
        assert np.allclose(
            loaded.map_eye(Eye.LEFT, probe), profile.map_eye(Eye.LEFT, probe)
        )

    def test_rejects_foreign_json(self, tmp_path):
        path = tmp_path / "bad.json"
        path.write_text('{"format": "something-else"}', encoding="utf-8")
        with pytest.raises(ValueError, match="not a gaze-on-glass profile"):
            load_profile(path)

    def test_rejects_future_version(self):
        profile, _ = self.build()
        d = profile.to_dict()
        d["version"] = 99
        with pytest.raises(ValueError, match="newer than supported"):
            CalibrationProfile.from_dict(d)

    def test_rejects_unknown_polynomial_basis(self):
        profile, _ = self.build()
        d = profile.to_dict()
        d["eyes"]["left"]["terms"] = ["1", "px", "py"]
        with pytest.raises(ValueError, match="unsupported polynomial basis"):
            CalibrationProfile.from_dict(d)


class TestFixationCollector:
    def test_accepts_a_settled_burst(self):
        c = FixationCollector()
        for _ in range(8):  # saccade, wild
            c.add([0.9, 0.2])
        for _ in range(12):  # settled
            c.add([0.500, 0.400])
        r = c.result()
        assert r.accepted
        assert np.allclose(r.pupil, [0.5, 0.4])
        assert r.n_used == 12
        assert r.n_total == 20

    def test_rejects_a_wandering_eye(self):
        rng = np.random.default_rng(1)
        c = FixationCollector()
        for _ in range(30):
            c.add(rng.uniform(0.3, 0.7, 2))
        r = c.result()
        assert not r.accepted
        assert "dispersion" in r.reason

    def test_rejects_when_detector_confidence_is_low(self):
        c = FixationCollector()
        for _ in range(30):
            c.add([0.5, 0.4], confidence=0.2)
        r = c.result()
        assert not r.accepted
        assert "usable samples" in r.reason

    def test_rejects_empty(self):
        assert FixationCollector().result().reason == "no samples"

    def test_reset_clears(self):
        c = FixationCollector()
        c.add([0.5, 0.5])
        c.reset()
        assert len(c) == 0

    def test_rejects_malformed_sample(self):
        with pytest.raises(ValueError):
            FixationCollector().add([0.5, 0.5, 0.5])

    def test_end_to_end_from_collected_bursts(self):
        """Collect noisy bursts per target, fit, and still hit the accuracy bar."""
        rng = np.random.default_rng(11)
        cal = default_target_grid(3, 3)
        truth = synthetic_pupil(cal)

        pupil_samples = []
        for target_pupil in truth:
            c = FixationCollector()
            for _ in range(6):
                c.add(rng.uniform(0, 1, 2))  # saccade
            for _ in range(14):
                c.add(target_pupil + rng.normal(0, 0.003, 2))
            r = c.result()
            assert r.accepted, r.reason
            pupil_samples.append(r.pupil)

        m = fit_polynomial_mapper(np.array(pupil_samples), cal, IMAGE_SIZE)
        val = offset_grid(4, 4)
        assert validate_mapper(
            m, synthetic_pupil(val), val, fov_degrees=FOV
        ).mean_error_deg < 1.5


class TestValidationReport:
    def test_units_are_consistent(self):
        cal = default_target_grid(3, 3)
        m = fit_polynomial_mapper(synthetic_pupil(cal), cal, IMAGE_SIZE)
        val = offset_grid(3, 3)
        r = validate_mapper(
            m, synthetic_pupil(val), val, screen_size=SCREEN_SIZE, fov_degrees=FOV
        )
        assert r.n_points == 9
        assert r.mean_error_norm <= r.p95_error_norm <= r.max_error_norm
        assert r.mean_error_px is not None and r.mean_error_deg is not None
        assert "deg" in r.summary()

    def test_optional_units_omitted_when_unknown(self):
        cal = default_target_grid(3, 3)
        m = fit_polynomial_mapper(synthetic_pupil(cal), cal, IMAGE_SIZE)
        r = validate_mapper(m, synthetic_pupil(cal), cal)
        assert r.mean_error_px is None and r.mean_error_deg is None
        assert "deg" not in r.summary()

    def test_rejects_no_points(self):
        cal = default_target_grid(3, 3)
        m = fit_polynomial_mapper(synthetic_pupil(cal), cal, IMAGE_SIZE)
        with pytest.raises(ValueError, match="no validation points"):
            validate_mapper(m, np.zeros((0, 2)), np.zeros((0, 2)))


def test_mapper_dict_roundtrip():
    cal = default_target_grid(3, 3)
    m = fit_polynomial_mapper(synthetic_pupil(cal), cal, IMAGE_SIZE)
    m2 = PolynomialMapper.from_dict(m.to_dict())
    assert np.allclose(m.map(np.array([0.5, 0.5])), m2.map(np.array([0.5, 0.5])))
    assert m2.image_size == IMAGE_SIZE
    assert m2.n_samples == 9

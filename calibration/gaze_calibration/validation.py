"""Held-out validation of a fitted mapping.

Accuracy claims are only worth anything on points the fit never saw. Fit on the
calibration grid, validate on a second, offset grid.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

import numpy as np

from .polynomial import PolynomialMapper
from .profile import CalibrationProfile, Eye


@dataclass(frozen=True)
class ValidationReport:
    """Error of a mapping against held-out targets.

    Normalized units are fractions of the screen. Pixel and degree figures are
    derived from screen_size and fov_degrees and are None when those are unknown.
    """

    n_points: int
    mean_error_norm: float
    rms_error_norm: float
    p95_error_norm: float
    max_error_norm: float
    mean_error_px: tuple[float, float] | None = None
    mean_error_deg: float | None = None
    p95_error_deg: float | None = None

    def summary(self) -> str:
        parts = [
            f"n={self.n_points}",
            f"mean={self.mean_error_norm:.4f} rms={self.rms_error_norm:.4f} "
            f"p95={self.p95_error_norm:.4f} max={self.max_error_norm:.4f} (norm)",
        ]
        if self.mean_error_px is not None:
            parts.append(
                f"mean=({self.mean_error_px[0]:.1f}, {self.mean_error_px[1]:.1f}) px"
            )
        if self.mean_error_deg is not None:
            parts.append(
                f"mean={self.mean_error_deg:.2f} deg p95={self.p95_error_deg:.2f} deg"
            )
        return " | ".join(parts)


def _report(
    errors_xy: np.ndarray,
    screen_size: tuple[int, int] | None,
    fov_degrees: tuple[float, float] | None,
) -> ValidationReport:
    """Build a report from (N, 2) signed errors in normalized screen units."""
    dist = np.linalg.norm(errors_xy, axis=1)

    mean_px = None
    if screen_size is not None:
        abs_mean = np.mean(np.abs(errors_xy), axis=0)
        mean_px = (
            float(abs_mean[0] * screen_size[0]),
            float(abs_mean[1] * screen_size[1]),
        )

    mean_deg = p95_deg = None
    if fov_degrees is not None:
        # Small-angle approximation across the FOV: normalized error times the
        # angular extent of that axis. Accurate to well under the noise floor of
        # a 1 to 2 degree tracker.
        deg = np.linalg.norm(
            errors_xy * np.asarray(fov_degrees, dtype=float), axis=1
        )
        mean_deg = float(np.mean(deg))
        p95_deg = float(np.percentile(deg, 95))

    return ValidationReport(
        n_points=len(dist),
        mean_error_norm=float(np.mean(dist)),
        rms_error_norm=float(np.sqrt(np.mean(dist**2))),
        p95_error_norm=float(np.percentile(dist, 95)),
        max_error_norm=float(np.max(dist)),
        mean_error_px=mean_px,
        mean_error_deg=mean_deg,
        p95_error_deg=p95_deg,
    )


def validate_mapper(
    mapper: PolynomialMapper,
    pupil: Sequence[Sequence[float]] | np.ndarray,
    screen: Sequence[Sequence[float]] | np.ndarray,
    screen_size: tuple[int, int] | None = None,
    fov_degrees: tuple[float, float] | None = None,
) -> ValidationReport:
    """Validate one eye's mapper against held-out (pupil, screen) pairs."""
    pupil = np.asarray(pupil, dtype=float)
    screen = np.asarray(screen, dtype=float)
    if pupil.shape != screen.shape:
        raise ValueError("pupil and screen must have the same shape")
    if len(pupil) == 0:
        raise ValueError("no validation points")
    return _report(mapper.map(pupil) - screen, screen_size, fov_degrees)


def validate_profile(
    profile: CalibrationProfile,
    pupil: Mapping[Eye | str, np.ndarray],
    screen: Sequence[Sequence[float]] | np.ndarray,
    confidence: Mapping[Eye | str, Sequence[float]] | None = None,
) -> dict[str, ValidationReport]:
    """Validate a whole profile against held-out targets.

    Args:
        profile: the fitted profile.
        pupil: {eye: (N, 2)} normalized pupil positions, same N and ordering for
            every eye and matching `screen`.
        screen: (N, 2) normalized ground-truth target positions.
        confidence: optional {eye: (N,)} per-sample weights for the binocular
            combination.

    Returns:
        {"left": report, "right": report, "binocular": report} for whichever
        eyes are present. "binocular" is only included for two-eye profiles.
    """
    screen = np.asarray(screen, dtype=float)
    reports: dict[str, ValidationReport] = {}

    for eye in profile.eyes:
        if eye.value not in {Eye(k).value for k in pupil}:
            continue
        eye_pupil = np.asarray(
            next(v for k, v in pupil.items() if Eye(k) is eye), dtype=float
        )
        reports[eye.value] = validate_mapper(
            profile.mappers[eye],
            eye_pupil,
            screen,
            screen_size=profile.screen_size,
            fov_degrees=profile.fov_degrees,
        )

    if len(reports) > 1:
        combined = np.vstack(
            [
                profile.map_binocular(
                    {k: np.asarray(v, dtype=float)[i] for k, v in pupil.items()},
                    confidence=(
                        None
                        if confidence is None
                        else {k: float(np.asarray(v)[i]) for k, v in confidence.items()}
                    ),
                )
                for i in range(len(screen))
            ]
        )
        reports["binocular"] = _report(
            combined - screen, profile.screen_size, profile.fov_degrees
        )

    return reports

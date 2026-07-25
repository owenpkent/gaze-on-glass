"""Second-order polynomial mapping from pupil image coordinates to screen.

The mapping is the standard 2D eye-tracking form: two independent least-squares
polynomials per eye, one predicting normalized screen x and one predicting
normalized screen y, each over the six 2nd-order terms of the pupil position.

    sx = a0 + a1*px + a2*py + a3*px^2 + a4*px*py + a5*py^2
    sy = b0 + b1*px + b2*py + b3*px^2 + b4*px*py + b5*py^2

Pupil coordinates are normalized to the eye image (0..1) before fitting so the
coefficients stay numerically well scaled and stay meaningful if the capture
resolution changes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np

POLY_TERMS = ("1", "px", "py", "px^2", "px*py", "py^2")
N_TERMS = len(POLY_TERMS)


def design_matrix(pupil: np.ndarray) -> np.ndarray:
    """Build the 2nd-order design matrix for normalized pupil positions.

    Args:
        pupil: (N, 2) array of normalized pupil positions.

    Returns:
        (N, 6) design matrix in POLY_TERMS order.
    """
    pupil = np.asarray(pupil, dtype=float)
    if pupil.ndim != 2 or pupil.shape[1] != 2:
        raise ValueError(f"pupil must be (N, 2), got {pupil.shape}")
    px = pupil[:, 0]
    py = pupil[:, 1]
    return np.column_stack(
        [np.ones_like(px), px, py, px * px, px * py, py * py]
    )


@dataclass(frozen=True)
class PolynomialMapper:
    """A fitted pupil-to-screen mapping for one eye.

    Attributes:
        coeffs_x: (6,) coefficients predicting normalized screen x.
        coeffs_y: (6,) coefficients predicting normalized screen y.
        image_size: (width, height) of the eye image the fit was done against,
            used to normalize raw pixel pupil positions on the way in.
        n_samples: number of fixation points used in the fit.
        residual_rms: RMS residual on the fitting set, in normalized screen units.
    """

    coeffs_x: np.ndarray
    coeffs_y: np.ndarray
    image_size: tuple[int, int]
    n_samples: int
    residual_rms: float

    def map(self, pupil: np.ndarray) -> np.ndarray:
        """Map normalized pupil positions to normalized screen positions.

        Args:
            pupil: (N, 2) or (2,) normalized pupil positions.

        Returns:
            (N, 2) or (2,) normalized screen positions, same shape as input.
        """
        pupil = np.asarray(pupil, dtype=float)
        single = pupil.ndim == 1
        if single:
            pupil = pupil[None, :]
        A = design_matrix(pupil)
        screen = np.column_stack([A @ self.coeffs_x, A @ self.coeffs_y])
        return screen[0] if single else screen

    def map_pixels(self, pupil_px: np.ndarray) -> np.ndarray:
        """Map raw eye-image pixel positions to normalized screen positions."""
        pupil_px = np.asarray(pupil_px, dtype=float)
        w, h = self.image_size
        return self.map(pupil_px / np.array([float(w), float(h)]))

    def to_dict(self) -> dict:
        return {
            "coeffs_x": [float(c) for c in self.coeffs_x],
            "coeffs_y": [float(c) for c in self.coeffs_y],
            "terms": list(POLY_TERMS),
            "image_size": [int(self.image_size[0]), int(self.image_size[1])],
            "n_samples": int(self.n_samples),
            "residual_rms": float(self.residual_rms),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "PolynomialMapper":
        terms = tuple(d.get("terms", POLY_TERMS))
        if terms != POLY_TERMS:
            raise ValueError(
                f"unsupported polynomial basis {terms}, expected {POLY_TERMS}"
            )
        return cls(
            coeffs_x=np.asarray(d["coeffs_x"], dtype=float),
            coeffs_y=np.asarray(d["coeffs_y"], dtype=float),
            image_size=(int(d["image_size"][0]), int(d["image_size"][1])),
            n_samples=int(d["n_samples"]),
            residual_rms=float(d["residual_rms"]),
        )


def fit_polynomial_mapper(
    pupil: Sequence[Sequence[float]] | np.ndarray,
    screen: Sequence[Sequence[float]] | np.ndarray,
    image_size: tuple[int, int],
    normalize_input: bool = False,
) -> PolynomialMapper:
    """Least-squares fit of the 2nd-order mapping for one eye.

    Args:
        pupil: (N, 2) pupil positions, normalized 0..1 unless normalize_input.
        screen: (N, 2) normalized screen positions of the fixation targets.
        image_size: (width, height) of the eye image.
        normalize_input: if True, `pupil` is in raw pixels and is divided by
            image_size before fitting.

    Returns:
        A fitted PolynomialMapper.

    Raises:
        ValueError: on shape mismatch or fewer than 6 samples (the fit would be
            underdetermined; a 9-point grid is the practical minimum).
    """
    pupil = np.asarray(pupil, dtype=float)
    screen = np.asarray(screen, dtype=float)
    if pupil.shape != screen.shape:
        raise ValueError(
            f"pupil {pupil.shape} and screen {screen.shape} must have the same shape"
        )
    if pupil.ndim != 2 or pupil.shape[1] != 2:
        raise ValueError(f"expected (N, 2) arrays, got {pupil.shape}")
    if len(pupil) < N_TERMS:
        raise ValueError(
            f"need at least {N_TERMS} fixation points to fit a 2nd-order "
            f"polynomial, got {len(pupil)}"
        )
    if normalize_input:
        pupil = pupil / np.array([float(image_size[0]), float(image_size[1])])

    A = design_matrix(pupil)
    coeffs_x, *_ = np.linalg.lstsq(A, screen[:, 0], rcond=None)
    coeffs_y, *_ = np.linalg.lstsq(A, screen[:, 1], rcond=None)

    predicted = np.column_stack([A @ coeffs_x, A @ coeffs_y])
    err = np.linalg.norm(predicted - screen, axis=1)
    residual_rms = float(np.sqrt(np.mean(err**2)))

    return PolynomialMapper(
        coeffs_x=coeffs_x,
        coeffs_y=coeffs_y,
        image_size=(int(image_size[0]), int(image_size[1])),
        n_samples=len(pupil),
        residual_rms=residual_rms,
    )

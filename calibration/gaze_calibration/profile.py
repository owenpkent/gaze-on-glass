"""Binocular calibration profile: fit, combine, save, load."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Mapping, Sequence

import numpy as np

from .polynomial import PolynomialMapper, fit_polynomial_mapper

PROFILE_FORMAT = "gaze-on-glass/calibration-profile"
PROFILE_VERSION = 1


class Eye(str, Enum):
    LEFT = "left"
    RIGHT = "right"


@dataclass
class CalibrationProfile:
    """A fitted mapping for one or both eyes, plus the metadata to reproduce it.

    A profile is only valid for the physical setup it was captured on. Any
    change to camera position, mount, or eye-image resolution invalidates it.
    """

    mappers: dict[Eye, PolynomialMapper]
    screen_size: tuple[int, int] = (1920, 1080)
    fov_degrees: tuple[float, float] | None = None
    metadata: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.mappers:
            raise ValueError("a profile needs at least one eye")
        self.mappers = {Eye(k): v for k, v in self.mappers.items()}

    @property
    def eyes(self) -> list[Eye]:
        return sorted(self.mappers.keys(), key=lambda e: e.value)

    def map_eye(self, eye: Eye, pupil: np.ndarray) -> np.ndarray:
        """Map one eye's normalized pupil position to normalized screen."""
        return self.mappers[Eye(eye)].map(pupil)

    def map_binocular(
        self,
        pupil: Mapping[Eye | str, Sequence[float] | np.ndarray],
        confidence: Mapping[Eye | str, float] | None = None,
    ) -> np.ndarray:
        """Combine per-eye mappings into a single normalized screen position.

        Eyes present in `pupil` but missing from the profile are ignored, so a
        binocular profile degrades gracefully to monocular when one detector
        loses the pupil (pass that eye a confidence of 0, or omit it).

        Args:
            pupil: per-eye normalized pupil positions.
            confidence: optional per-eye weights in 0..1. Eyes at exactly 0 are
                dropped. Omitted means equal weight.

        Returns:
            (2,) normalized screen position.

        Raises:
            ValueError: if no eye survives weighting.
        """
        points: list[np.ndarray] = []
        weights: list[float] = []
        for raw_eye, p in pupil.items():
            eye = Eye(raw_eye)
            if eye not in self.mappers:
                continue
            w = 1.0 if confidence is None else float(confidence.get(raw_eye, 1.0))
            if w <= 0.0:
                continue
            points.append(self.mappers[eye].map(np.asarray(p, dtype=float)))
            weights.append(w)

        if not points:
            raise ValueError("no eye with positive confidence and a fitted mapper")

        return np.average(np.vstack(points), axis=0, weights=np.asarray(weights))

    def to_pixels(self, screen_norm: np.ndarray) -> np.ndarray:
        """Convert normalized screen coordinates to display pixels."""
        return np.asarray(screen_norm, dtype=float) * np.asarray(
            self.screen_size, dtype=float
        )

    def to_dict(self) -> dict:
        return {
            "format": PROFILE_FORMAT,
            "version": PROFILE_VERSION,
            "screen_size": [int(self.screen_size[0]), int(self.screen_size[1])],
            "fov_degrees": (
                None if self.fov_degrees is None else list(map(float, self.fov_degrees))
            ),
            "metadata": self.metadata,
            "eyes": {e.value: m.to_dict() for e, m in self.mappers.items()},
        }

    @classmethod
    def from_dict(cls, d: dict) -> "CalibrationProfile":
        fmt = d.get("format")
        if fmt != PROFILE_FORMAT:
            raise ValueError(f"not a gaze-on-glass profile (format={fmt!r})")
        version = int(d.get("version", 0))
        if version > PROFILE_VERSION:
            raise ValueError(
                f"profile version {version} is newer than supported "
                f"{PROFILE_VERSION}"
            )
        fov = d.get("fov_degrees")
        return cls(
            mappers={
                Eye(k): PolynomialMapper.from_dict(v) for k, v in d["eyes"].items()
            },
            screen_size=(int(d["screen_size"][0]), int(d["screen_size"][1])),
            fov_degrees=None if fov is None else (float(fov[0]), float(fov[1])),
            metadata=dict(d.get("metadata", {})),
        )


def fit_profile(
    samples: Mapping[Eye | str, tuple[np.ndarray, np.ndarray]],
    image_size: tuple[int, int],
    screen_size: tuple[int, int] = (1920, 1080),
    fov_degrees: tuple[float, float] | None = None,
    metadata: dict | None = None,
    normalize_input: bool = False,
) -> CalibrationProfile:
    """Fit a profile from per-eye (pupil, screen) sample pairs.

    Args:
        samples: {eye: (pupil (N, 2), screen (N, 2))}. N may differ per eye:
            each eye is fitted independently, so a dropped frame on one eye does
            not cost you the sample on the other.
        image_size: (width, height) of the eye camera image.
        screen_size: (width, height) of the mirrored display in pixels.
        fov_degrees: optional (horizontal, vertical) display FOV, needed only to
            report validation error in degrees.
        metadata: free-form provenance (device, mount revision, date).
        normalize_input: pupil samples are raw pixels rather than 0..1.

    Returns:
        A fitted CalibrationProfile.
    """
    mappers: dict[Eye, PolynomialMapper] = {}
    for raw_eye, (pupil, screen) in samples.items():
        mappers[Eye(raw_eye)] = fit_polynomial_mapper(
            pupil, screen, image_size=image_size, normalize_input=normalize_input
        )
    return CalibrationProfile(
        mappers=mappers,
        screen_size=screen_size,
        fov_degrees=fov_degrees,
        metadata=dict(metadata or {}),
    )


def save_profile(profile: CalibrationProfile, path: str | Path) -> Path:
    """Write a profile to JSON. Returns the path written."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(profile.to_dict(), indent=2) + "\n", encoding="utf-8"
    )
    return path


def load_profile(path: str | Path) -> CalibrationProfile:
    """Read a profile from JSON."""
    return CalibrationProfile.from_dict(
        json.loads(Path(path).read_text(encoding="utf-8"))
    )

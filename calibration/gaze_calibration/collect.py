"""Fixation sample collection.

A calibration point is not one frame, it is a short burst of frames taken after
the eye has settled on the target. This module handles the boring but
consequential part: discard the saccade, require the remaining samples to be
tight, and reject the point if they are not.

It is deliberately free of timers and UI. The caller pushes frames in; this
decides what is usable.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


def default_target_grid(cols: int = 3, rows: int = 3, margin: float = 0.1) -> np.ndarray:
    """Evenly spaced fixation targets in normalized screen coordinates.

    Args:
        cols: number of columns (3 gives the classic 9-point grid).
        rows: number of rows.
        margin: fraction of the screen kept clear at each edge. Targets pushed
            fully into the corners sit where the polynomial extrapolates worst
            and where the eye camera may lose the pupil to the eyelid.

    Returns:
        (cols * rows, 2) targets in row-major order.
    """
    if cols < 2 or rows < 2:
        raise ValueError("need at least a 2x2 grid")
    if not 0.0 <= margin < 0.5:
        raise ValueError("margin must be in [0, 0.5)")
    xs = np.linspace(margin, 1.0 - margin, cols)
    ys = np.linspace(margin, 1.0 - margin, rows)
    return np.array([(x, y) for y in ys for x in xs], dtype=float)


@dataclass(frozen=True)
class FixationResult:
    """The outcome of collecting one calibration point.

    Attributes:
        accepted: whether the burst is usable as a calibration sample.
        pupil: (2,) mean normalized pupil position, or None if rejected.
        dispersion: RMS spread of the kept samples, normalized pupil units.
        n_used: samples that survived settling and confidence filtering.
        n_total: samples pushed in.
        reason: why it was rejected, empty when accepted.
    """

    accepted: bool
    pupil: np.ndarray | None
    dispersion: float
    n_used: int
    n_total: int
    reason: str = ""


@dataclass
class FixationCollector:
    """Accumulates pupil samples for a single fixation target.

    Typical use, per target:

        c = FixationCollector()
        while showing_target:
            c.add(pupil_xy, confidence)
        result = c.result()
        if result.accepted:
            samples.append((result.pupil, target_xy))

    Args:
        settle_fraction: leading fraction of samples discarded as the saccade
            and its overshoot. 0.4 of a 500ms dwell leaves 300ms of fixation.
        min_confidence: detector confidence below which a sample is dropped.
        min_samples: fewest usable samples for an accepted point.
        max_dispersion: largest RMS spread accepted, in normalized pupil units.
            Above this the user was not actually fixating, or the detector was
            flickering between the pupil and something else.
    """

    settle_fraction: float = 0.4
    min_confidence: float = 0.6
    min_samples: int = 5
    max_dispersion: float = 0.02

    _samples: list[tuple[float, float, float]] = field(
        default_factory=list, repr=False
    )

    def add(self, pupil: object, confidence: float = 1.0) -> None:
        """Push one detected pupil position (normalized) and its confidence."""
        p = np.asarray(pupil, dtype=float).reshape(-1)
        if p.size != 2:
            raise ValueError(f"pupil must be 2 values, got {p.size}")
        self._samples.append((float(p[0]), float(p[1]), float(confidence)))

    def reset(self) -> None:
        self._samples.clear()

    def __len__(self) -> int:
        return len(self._samples)

    def result(self) -> FixationResult:
        """Evaluate the accumulated burst."""
        n_total = len(self._samples)
        if n_total == 0:
            return FixationResult(False, None, 0.0, 0, 0, "no samples")

        start = int(round(n_total * self.settle_fraction))
        kept = [s for s in self._samples[start:] if s[2] >= self.min_confidence]
        if len(kept) < self.min_samples:
            return FixationResult(
                False,
                None,
                0.0,
                len(kept),
                n_total,
                f"only {len(kept)} usable samples, need {self.min_samples}",
            )

        pts = np.array([(x, y) for x, y, _ in kept], dtype=float)
        mean = pts.mean(axis=0)
        dispersion = float(
            np.sqrt(np.mean(np.sum((pts - mean) ** 2, axis=1)))
        )
        if dispersion > self.max_dispersion:
            return FixationResult(
                False,
                None,
                dispersion,
                len(kept),
                n_total,
                f"dispersion {dispersion:.4f} exceeds {self.max_dispersion:.4f}",
            )

        return FixationResult(True, mean, dispersion, len(kept), n_total)

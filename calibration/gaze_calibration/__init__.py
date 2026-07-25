"""Framework-agnostic 2D pupil-to-screen gaze calibration.

Pure numpy. No OpenCV, no Android, no camera, no UI. Feed it pupil samples and
target positions, get back a mapping you can evaluate anywhere.
"""

from .polynomial import (
    PolynomialMapper,
    fit_polynomial_mapper,
    design_matrix,
    POLY_TERMS,
)
from .profile import (
    CalibrationProfile,
    Eye,
    fit_profile,
    load_profile,
    save_profile,
)
from .validation import ValidationReport, validate_profile, validate_mapper
from .collect import FixationCollector, FixationResult, default_target_grid

__all__ = [
    "PolynomialMapper",
    "fit_polynomial_mapper",
    "design_matrix",
    "POLY_TERMS",
    "CalibrationProfile",
    "Eye",
    "fit_profile",
    "load_profile",
    "save_profile",
    "ValidationReport",
    "validate_profile",
    "validate_mapper",
    "FixationCollector",
    "FixationResult",
    "default_target_grid",
]

__version__ = "0.1.0"

"""Make `gaze_calibration` importable without an install.

Without this, `pytest` works from inside `calibration/` but not from the repo
root, which is a confusing way for a contributor's first test run to fail.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

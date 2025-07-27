
try:
    import unimelb_phd_phase_1  # noqa: F401
except ModuleNotFoundError:
    import sys
    from pathlib import Path
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root))

import sys
from pathlib import Path

# Ensure the package root is on the path when running tests without installation
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))
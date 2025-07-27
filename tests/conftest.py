
try:
    import unimelb_phd_phase_1  # noqa: F401
except ModuleNotFoundError:
    import sys
    from pathlib import Path
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root))

import sys
from pathlib import Path

# Ensure the project root is on sys.path so tests can import the package without installation
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Ensure the package root is on the path when running tests without installation
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))
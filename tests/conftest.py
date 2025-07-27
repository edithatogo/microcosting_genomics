import sys
from pathlib import Path

# Ensure the package root is on the path when running tests without installation
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

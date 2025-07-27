import sys
from pathlib import Path
import pandas as pd
import warnings

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Silence noisy PerformanceWarnings from pandas during tests
warnings.simplefilter("ignore", pd.errors.PerformanceWarning)

# Ensure the package root is on the path when running tests without installation
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

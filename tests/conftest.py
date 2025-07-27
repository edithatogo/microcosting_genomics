import sys
from pathlib import Path
import pandas as pd
import warnings

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Also include the src directory for the src/ layout
SRC_DIR = PROJECT_ROOT / "src"
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# Silence noisy PerformanceWarnings from pandas during tests
warnings.simplefilter("ignore", pd.errors.PerformanceWarning)

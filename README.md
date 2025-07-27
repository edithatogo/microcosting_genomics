# unimelb-phd-phase_1
University of Melbourne PhD (Economics of Rare Disease Genomics) - Phase 1 Microcosting Genomics

## Data Directory

All input files used by the helper scripts live in the `data/` directory at the
root of the repository. Each script resolves this path dynamically using a
snippet similar to:

```python
from pathlib import Path
DATA_DIR = Path(__file__).resolve().parents[0] / 'data'
```

The processed and extracted files referenced in the notebooks and scripts should
be placed inside this directory.

"""List all sheet names in the microcosting workbook.

Data files are stored in the repository ``data`` directory located at
``Path(__file__).resolve().parents[0] / 'data'``.
"""

from pathlib import Path
import openpyxl

DATA_DIR = Path(__file__).resolve().parents[0] / 'data'
workbook = openpyxl.load_workbook(DATA_DIR / 'Microcosting - Study 1 - Utilisation and Microcosts v15 (20230902).xlsm')
print(workbook.sheetnames)

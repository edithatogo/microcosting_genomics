from io import StringIO

import numpy_financial as npf
import pandas as pd
import pytest


def test_equipment_cost_replication():
    csv = (
        "Equipment,Description,Brand,Model,Useful Life,List Price (USD),List Price (EUR),List Price (AUD),"
        "Date Accessed,Source,Annualised cost,Present value,Workflows WES/Panel,Workflows WGS,"
        "Initial Estimate Total Samples per Year,Initial Estimate 0.7,Initial Estimate Max,"
        "Theoretical 50x WES,Theoretical 0.8,Theoretical 0.4,Theoretical Comment,50x WES Max,"
        "50x WES 0.7,50x WES Comment,80x WES Max,80x WES 0.7,30x Genomes Estimate,30x Genomes Source,"
        "30x Genomes Comment,30x Genomes Max,30x Genomes 70%,Cost per sample LL,Cost per sample MP,Cost per sample UL\n"
        "MachineA,descA,BrandA,ModelA,5,0,0,2000,2024,src,0,0,0,0,0,0,0,0,0,0,,0,0,,0,0,0,0,,0,0,0,0"
    )
    df = pd.read_csv(StringIO(csv))

    df["Calculated Annualised cost"] = df["List Price (AUD)"] / df["Useful Life"]
    rate = 0.0452
    df["Calculated Present value"] = df.apply(
        lambda row: npf.pmt(rate, row["Useful Life"], -row["List Price (AUD)"]), axis=1
    )

    row = df.iloc[0]
    assert row["Calculated Annualised cost"] == pytest.approx(400.0)
    assert row["Calculated Present value"] == pytest.approx(455.83721824500924)

# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Check replication of the equipment cost table."""

from io import StringIO

import numpy_financial as npf
import polars as pl
import pytest


def test_equipment_cost_replication() -> None:
    """Check equipment cost replication."""
    csv = (
        "Equipment,Description,Brand,Model,Useful Life,List Price "
        "(USD),List Price (EUR),List Price (AUD),"
        "Date Accessed,Source,Annualised cost,Present value,Workflows "
        "WES/Panel,Workflows WGS,"
        "Initial Estimate Total Samples per Year,Initial Estimate "
        "0.7,Initial Estimate Max,"
        "Theoretical 50x WES,Theoretical 0.8,Theoretical "
        "0.4,Theoretical Comment,50x WES Max,"
        "50x WES 0.7,50x WES Comment,80x WES Max,80x WES 0.7,30x "
        "Genomes Estimate,30x Genomes Source,"
        "30x Genomes Comment,30x Genomes Max,30x Genomes 70%,Cost per "
        "sample LL,Cost per sample MP,Cost per sample UL\n"
        "MachineA,descA,BrandA,ModelA,5,0,0,2000,2024,src,0,0,0,0,0,0,0,0,0,0,,0,0,,0,0,0,0,,0,0,0,0"
    )
    df = pl.read_csv(
        StringIO(csv),
        infer_schema=False,
        schema_overrides={"Useful Life": pl.Float64, "List Price (AUD)": pl.Float64},
    )

    df = df.with_columns(
        (df["List Price (AUD)"] / df["Useful Life"]).alias(
            "Calculated Annualised cost",
        ),
    )
    rate = 0.0452
    df = df.with_columns(
        pl.Series(
            "Calculated Present value",
            npf.pmt(
                rate,
                df["Useful Life"].to_numpy(),
                -df["List Price (AUD)"].to_numpy(),
            ),
        ),
    )

    row = df.row(0, named=True)
    if not (row["Calculated Annualised cost"] == pytest.approx(400.0)):
        raise AssertionError
    if not (row["Calculated Present value"] == pytest.approx(455.83721824500924)):
        raise AssertionError

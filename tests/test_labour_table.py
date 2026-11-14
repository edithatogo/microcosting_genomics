# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Check replication of the labour cost table."""

from io import StringIO

import polars as pl
import pytest


def test_labour_cost_replication() -> None:
    """Check labour cost replication."""
    csv = (
        "Jurisdiction,Personnel type,Label,Award,Grade(s),Distribution "
        "desc,References,Year,"
        "Superannuation Rate (%),Hours per week,Average productive time"
        " (%),Average Penalties %,"
        "Public Holiday Penalty Percentage,Private Practice "
        "Loading,Attraction and Retention Allowance,"
        "Sick Leave Percentage,Professional Development "
        "Allowance,Annual Leave Entitlement (Weeks),"
        "Annual Leave Loading (%),Indexation per annum (%),Base Salary "
        "LL,Base Salary Mid-point,"
        "Base Salary UL,Base Salary + Costs LL,Base Salary + Costs "
        "Mid-point,Base Salary + Costs UL,"
        "Base Salary + Costs (hourly) LL,Base Salary + Costs (hourly) "
        "Mid-point,Base Salary + Costs (hourly) UL\n"
        "VIC,Scientist,Registration,Test Award,Grade1,,Ref,2023,0.1,38,"
        "0.8,0.05,0.02,0.03,0.01,0.04,500,4,0.1,0.02,1000,0,1200,0,0,0,0,"
        "0,0"
    )
    df = pl.read_csv(
        StringIO(csv),
        infer_schema=False,
        schema_overrides={
            "Base Salary LL": pl.Float64,
            "Base Salary UL": pl.Float64,
            "Superannuation Rate (%)": pl.Float64,
            "Average Penalties %": pl.Float64,
            "Public Holiday Penalty Percentage": pl.Float64,
            "Private Practice Loading": pl.Float64,
            "Attraction and Retention Allowance": pl.Float64,
            "Sick Leave Percentage": pl.Float64,
            "Professional Development Allowance": pl.Float64,
            "Annual Leave Entitlement (Weeks)": pl.Float64,
            "Annual Leave Loading (%)": pl.Float64,
            "Average productive time (%)": pl.Float64,
            "Hours per week": pl.Float64,
        },
    )

    df = df.with_columns(
        (
            df["Base Salary LL"] + ((df["Base Salary UL"] - df["Base Salary LL"]) / 2)
        ).alias("Calculated Base Salary Mid-point"),
    )
    df = df.with_columns(
        (
            (
                df["Base Salary LL"]
                + df["Base Salary LL"] * df["Superannuation Rate (%)"]
                + df["Base Salary LL"] * df["Average Penalties %"]
                + df["Base Salary LL"] * df["Public Holiday Penalty Percentage"]
                + df["Base Salary LL"] * df["Private Practice Loading"]
                + df["Base Salary LL"] * df["Attraction and Retention Allowance"]
                + df["Base Salary LL"] * df["Sick Leave Percentage"]
                + df["Professional Development Allowance"]
                + (
                    df["Base Salary LL"]
                    * ((52 + df["Annual Leave Entitlement (Weeks)"]) / 52)
                )
                * (1 + df["Annual Leave Loading (%)"])
            )
            * (1 / df["Average productive time (%)"])
        ).alias("Calculated Base Salary + Costs LL"),
    )
    df = df.with_columns(
        (df["Calculated Base Salary + Costs LL"] / 52 / df["Hours per week"]).alias(
            "Calculated Base Salary + Costs (hourly) LL",
        ),
    )

    row = df.row(0, named=True)
    if not (row["Calculated Base Salary Mid-point"] == pytest.approx(1100.0)):
        raise AssertionError
    if not (
        row["Calculated Base Salary + Costs LL"] == pytest.approx(3668.269230769231)
    ):
        raise AssertionError
    if not (
        row["Calculated Base Salary + Costs (hourly) LL"]
        == pytest.approx(
            1.8564115540330115,
        )
    ):
        raise AssertionError

from io import StringIO

import pandas as pd
import pytest


def test_labour_cost_replication():
    csv = (
        "Jurisdiction,Personnel type,Label,Award,Grade(s),Distribution desc,References,Year,"
        "Superannuation Rate (%),Hours per week,Average productive time (%),Average Penalties %,"
        "Public Holiday Penalty Percentage,Private Practice Loading,Attraction and Retention Allowance,"
        "Sick Leave Percentage,Professional Development Allowance,Annual Leave Entitlement (Weeks),"
        "Annual Leave Loading (%),Indexation per annum (%),Base Salary LL,Base Salary Mid-point,"
        "Base Salary UL,Base Salary + Costs LL,Base Salary + Costs Mid-point,Base Salary + Costs UL,"
        "Base Salary + Costs (hourly) LL,Base Salary + Costs (hourly) Mid-point,Base Salary + Costs (hourly) UL\n"
        "VIC,Scientist,Registration,Test Award,Grade1,,Ref,2023,0.1,38,0.8,0.05,0.02,0.03,0.01,0.04,500,4,0.1,0.02,1000,0,1200,0,0,0,0,0,0"
    )
    df = pd.read_csv(StringIO(csv))

    df["Calculated Base Salary Mid-point"] = df["Base Salary LL"] + (
        (df["Base Salary UL"] - df["Base Salary LL"]) / 2
    )
    df["Calculated Base Salary + Costs LL"] = (
        df["Base Salary LL"]
        + df["Base Salary LL"] * df["Superannuation Rate (%)"]
        + df["Base Salary LL"] * df["Average Penalties %"]
        + df["Base Salary LL"] * df["Public Holiday Penalty Percentage"]
        + df["Base Salary LL"] * df["Private Practice Loading"]
        + df["Base Salary LL"] * df["Attraction and Retention Allowance"]
        + df["Base Salary LL"] * df["Sick Leave Percentage"]
        + df["Professional Development Allowance"]
        + (df["Base Salary LL"] * ((52 + df["Annual Leave Entitlement (Weeks)"]) / 52))
        * (1 + df["Annual Leave Loading (%)"])
    ) * (1 / df["Average productive time (%)"])
    df["Calculated Base Salary + Costs (hourly) LL"] = (
        df["Calculated Base Salary + Costs LL"] / 52 / df["Hours per week"]
    )

    row = df.iloc[0]
    assert row["Calculated Base Salary Mid-point"] == pytest.approx(1100.0)
    assert row["Calculated Base Salary + Costs LL"] == pytest.approx(3668.269230769231)
    assert row["Calculated Base Salary + Costs (hourly) LL"] == pytest.approx(
        1.8564115540330115
    )

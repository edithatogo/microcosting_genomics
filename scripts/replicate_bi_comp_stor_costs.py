"""
Replicates the calculations from the 'BI - Comp+Stor Costs - VCGS' sheet.
"""

from pathlib import Path

import pandas as pd


def replicate_bi_comp_stor_costs():
    """
    Replicates the calculations from the 'BI - Comp+Stor Costs - VCGS' sheet.
    """
    # Define the data as a dictionary of lists, similar to the Excel sheet
    server_data = {
        "Description": [
            "PowerEdge R760 Server",
            "Xenon NItro GPU Server, 2U, X12, A30 GPU",
        ],
        "CPUs": [2, 2],
        "Cores/CPU": [16, 16],
        "Threads/CPU": [32, 32],
        "Memory": [1024, 1024],
        "ex-GST": [54321.28, 49380.00],
    }

    # Create a DataFrame for server costs
    df_server = pd.DataFrame(server_data)

    # --- Server Cost Calculations ---
    df_server["Total Cores"] = df_server["CPUs"] * df_server["Cores/CPU"]
    df_server["Total Threads"] = df_server["CPUs"] * df_server["Threads/CPU"]
    df_server["inc. GST"] = df_server["ex-GST"] * 1.1
    df_server["3-yr"] = df_server["ex-GST"] / 3
    df_server["5-yr"] = df_server["ex-GST"] / 5
    df_server["Cost/CPU"] = df_server["ex-GST"] / df_server["CPUs"]
    df_server["Cost/Core"] = df_server["ex-GST"] / df_server["Total Cores"]
    df_server["Cost/Thread"] = df_server["inc. GST"] / df_server["Total Threads"]
    df_server["Cost/GB"] = df_server["ex-GST"] / df_server["Memory"]

    ul_total_hours = 5 * 365 * 24
    ll_total_hours = ul_total_hours * 0.7

    df_server["UL Total Hours"] = ul_total_hours
    df_server["LL Total Hours"] = ll_total_hours

    df_server["Cost/CPU/hr - 70%"] = df_server["Cost/CPU"] / df_server["LL Total Hours"]
    df_server["Cost/Core/hr - 70%"] = (
        df_server["Cost/Core"] / df_server["LL Total Hours"]
    )
    df_server["Cost/thread/hr - 70%"] = (
        df_server["Cost/Thread"] / df_server["LL Total Hours"]
    )
    df_server["cost/gb/hr - 70%"] = df_server["Cost/GB"] / df_server["LL Total Hours"]
    df_server["Cost/CPU/hr - 100%"] = (
        df_server["Cost/CPU"] / df_server["UL Total Hours"]
    )
    df_server["Cost/Core/hr - 100%"] = (
        df_server["Cost/Core"] / df_server["UL Total Hours"]
    )
    df_server["Cost/thread/hr - 100%"] = (
        df_server["Cost/Thread"] / df_server["UL Total Hours"]
    )
    df_server["cost/gb/hr - 100%"] = df_server["Cost/GB"] / df_server["UL Total Hours"]

    # --- Equipment Cost Calculations ---
    equipment_data = {
        "Equipment": ["Dragan Hardware", "Dragan Software"],
        "List Price (AUD)": [40165, 21450],
        "Useful Life": [5, 1],
        "WES/Panel": ["n", "n"],
        "WGS": ["y", "y"],
        "Initial Estimate": [2000, 2000],
        "Max": [50000, 50000],
    }
    df_equipment = pd.DataFrame(equipment_data)
    df_equipment["Annualised cost"] = (
        df_equipment["List Price (AUD)"] / df_equipment["Useful Life"]
    )
    df_equipment["Actual (0.7)"] = df_equipment["Max"] * 0.7
    df_equipment["Unit Cost ($/sample) - Initial"] = (
        df_equipment["Annualised cost"] / df_equipment["Initial Estimate"]
    )
    df_equipment["Unit Cost ($/sample) - Actual (0.7)"] = (
        df_equipment["Annualised cost"] / df_equipment["Actual (0.7)"]
    )
    df_equipment["Unit Cost ($/sample) - Max"] = (
        df_equipment["Annualised cost"] / df_equipment["Max"]
    )

    # --- Storage Cost Calculations ---
    storage_data = {
        "Description": [
            "2U R-Series with integrateed controller (96TB, 50.8 TB Useable in RAID-6)",
            "LTO-7 or LTO-8 Tape Drive Module",
            "LTO 7 Tape (uncompressed)",
            "LTO 8 Tape (uncompressed)",
        ],
        "Total Space (GB)": [50800, None, 6000, 12000],
        "ex-GST": [23800, 21000, 75, 115],
        "Useable life (years)": [5, 5, 5, 5],
    }
    df_storage = pd.DataFrame(storage_data)
    df_storage["Cost/GB"] = df_storage["ex-GST"] / df_storage["Total Space (GB)"]
    df_storage["Cost/GB/year"] = (
        df_storage["Cost/GB"] / df_storage["Useable life (years)"]
    )

    # Special case for 'LTO-7 or LTO-8 Tape Drive Module'
    lto_module_cost = 21000 / 5 / 20000
    df_storage.loc[1, "Cost/test"] = lto_module_cost

    # --- Save outputs ---
    output_dir = Path("data/replicated")
    output_dir.mkdir(exist_ok=True)
    df_server.to_csv(output_dir / "server_costs.csv", index=False)
    df_equipment.to_csv(output_dir / "equipment_costs.csv", index=False)
    df_storage.to_csv(output_dir / "storage_costs.csv", index=False)

    print("Replicated BI Comp+Stor Costs and saved to data/replicated/")


if __name__ == "__main__":
    replicate_bi_comp_stor_costs()

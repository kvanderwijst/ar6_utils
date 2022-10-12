import os
import numpy as np

import pandas as pd

from .constants import IP_SCENARIOS, SSP_SCENARIOS, YEARS

from .generalutils import linearInterp, variables
from .data import (
    add_variable_range,
    add_variable_year,
    calc_netzero,
    create_scenarios,
    create_variable,
    prepare_data,
)

VETTING_COL = "Vetting_historical"


def import_data(
    snapshot_folder, data_filename, meta_filename=None, dt=5, extra=True, onlyworld=True
):
    # Import the normal data file
    print("Importing data...")
    data = prepare_data(
        os.path.join(snapshot_folder, data_filename), dt=dt, onlyworld=onlyworld
    )

    if extra:
        print("Creating extra variables...")
        data = _create_extra_variables(data)

    print("Converting to standard units...")
    # Convert units to GtCO2 etc
    _convert_units(data)

    # Create scenarios dataframe
    if meta_filename is not None:
        print("Creating metadata...")
        scenarios = _create_metadata_df(
            data, snapshot_folder, meta_filename, fast=not extra
        )

        print("Finished.")
        return data, scenarios
    print("Finished.")
    return data


def _create_extra_variables(data):

    # Energy supply = 'Emissions|CO2|Energy|Supply' +  'Carbon Sequestration|CCS|Biomass'
    # data = create_variable(data, 'Emissions|CO2|Energy|Supply', 'Carbon Sequestration|CCS|Biomass', 'Energy Supply', '+')

    # Industry = 'Emissions|CO2|Energy|Demand|Industry' +  'Emissions|CO2|Industrial Processes'
    try:
        data = create_variable(
            data,
            "Emissions|CO2|Energy|Demand|Industry",
            "Emissions|CO2|Industrial Processes",
            "Industry",
            "+",
            default_var1=0.0,
            default_var2=0.0,
        )
    except KeyError:
        pass

    # Other Energy Demand = 'Emissions|CO2|Energy|Demand|AFOFI' +  'Emissions|CO2|Energy|Demand|Other Sector'
    try:
        data = create_variable(
            data,
            "Emissions|CO2|Energy|Demand|AFOFI",
            "Emissions|CO2|Energy|Demand|Other Sector",
            "Other Energy Demand",
            "+",
            default_var1=0.0,
            default_var2=0.0,
        )
    except KeyError:
        pass
    # Energy supply -- negative
    try:
        data = create_variable(
            data,
            "Carbon Sequestration|CCS|Biomass",
            "Carbon Sequestration|Direct Air Capture",
            "Carbon Sequestration|BECCS+DAC",
            "+",
            default_var1=0.0,
            default_var2=0.0,
        )
    except KeyError:
        pass
    # Energy supply -- positive
    try:
        data = create_variable(
            data,
            "Emissions|CO2|Energy|Supply",
            "Carbon Sequestration|BECCS+DAC",
            "Emissions|CO2|Energy|Supply Gross Positive",
            "+",
            default_var1=0.0,
            default_var2=0.0,
        )
    except KeyError:
        pass
    # Non-CO2 emissions
    try:
        data = create_variable(
            data,
            variables.KYOTO,
            "Emissions|CO2",
            "Emissions|Non-CO2",
            "-",
            overwrite_unit="Mt CO2-equiv/yr",
        )
    except KeyError:
        pass
    # Other = 'Emissions|CO2|Other' +  'Emissions|CO2|Waste'
    # data = create_variable(data, 'Emissions|CO2|Other', 'Emissions|CO2|Waste', 'Other', '+')
    # Make CCS variables minus
    data.loc[data["Variable"].str.contains("CCS"), YEARS] *= -1

    # Rename existing variables to something simpler
    var_rename = {
        "Carbon Sequestration|CCS|Biomass": "BECCS",
        "Emissions|CO2|Energy|Supply": "Energy Supply",
        "Carbon Sequestration|BECCS+DAC": "Energy Supply (neg.)",
        "Emissions|CO2|Energy|Supply Gross Positive": "Energy Supply (pos.)",
        "Emissions|CO2|AFOLU": "LULUCF",
        "Emissions|CO2|Energy|Demand|Transportation": "Transport",
        "Emissions|CO2|Energy|Demand|Residential and Commercial": "Buildings",
        "Emissions|CO2|Other": "Other",
    }
    for k, v in var_rename.items():
        data.loc[data["Variable"] == k, "Variable"] = v

    return data


def _convert_units(data):

    for df, columns in [(data, YEARS)]:
        # Convert unit Mt CO2/yr to Gt CO2/yr
        df.loc[df["Unit"] == "Mt CO2/yr", columns] *= 0.001
        df.loc[df["Unit"] == "Mt CO2/yr", "Unit"] = "Gt CO2/yr"

        # Convert unit Mt CH4/yr to Gt CH4/yr
        # df.loc[df['Unit'] == 'Mt CH4/yr', columns] *= 0.001
        # df.loc[df['Unit'] == 'Mt CH4/yr', 'Unit'] = 'Gt CH4/yr'

        # Convert unit Kt N2O/yr to Mt N2O/yr
        df.loc[df["Unit"] == "kt N2O/yr", columns] *= 0.001
        df.loc[df["Unit"] == "kt N2O/yr", "Unit"] = "Mt N2O/yr"

        # Convert unit Mt CO2-equiv/yr to Gt CO2-equiv/yr
        df.loc[df["Unit"] == "Mt CO2-equiv/yr", columns] *= 0.001
        df.loc[df["Unit"] == "Mt CO2-equiv/yr", "Unit"] = "Gt CO2-equiv/yr"


def _create_metadata_df(data, folder, meta_filename, fast=False):
    print("   Importing vetting...")
    vetting_df = _get_vetting(folder, meta_filename)

    meta = create_scenarios(data)

    # Merge with temperature category and vetting flags
    meta = meta.merge(
        vetting_df[[c for c in vetting_df.columns if c not in meta.columns]],
        left_index=True,
        right_index=True,
        how="left",
    )
    meta["Vetted"] = meta[VETTING_COL] == "PASS"

    # Add IP column (should be the same as IMP_marker, but this one depends on IP_SCENARIOS variable)
    meta["IP"] = np.nan
    for ip in IP_SCENARIOS.values():
        meta.loc[ip.scenario, "IP"] = ip.name
    # Add SSP column
    meta["SSP"] = np.nan
    for ssp in SSP_SCENARIOS.values():
        meta.loc[ssp.scenario, "SSP"] = ssp.name

    # CO2 emissions
    if not fast:
        print("   Calculating cumulative and peak emissions...")
        add_variable_range(meta, data, "Cum. CO2", variables.CO2, linearInterp)
        add_variable_year(meta, data, "GHG 2030", variables.KYOTO, year=2030)
        add_variable_range(
            meta, data, "Total net negative", variables.CO2, linearInterp, clip_upper=0
        )
        meta["Total net negative"] = -meta["Total net negative"]  # Make positive
        meta["Peak cum. CO2"] = meta["Cum. CO2"] - meta["Total net negative"]

    # Calculate net-zero
    # print("   Calculating net-zero years...")
    # calc_netzero(scenarios, data, variables.CO2, "Net zero CO2", limit=0.05)
    # calc_netzero(scenarios, data, variables.KYOTO, "Net zero Kyoto")
    # calc_netzero(
    #     scenarios,
    #     data,
    #     "Emissions|CO2|Energy|Demand",
    #     "Net zero Emissions|CO2|Energy|Demand",
    # )

    return meta


def _get_vetting(folder, meta_filename):
    vetting_df = pd.read_excel(
        os.path.join(folder, meta_filename), sheet_name="meta", engine="openpyxl"
    ).rename({"model": "Model", "scenario": "Scenario"}, axis="columns")
    # Add column Name, equal to Model + Scenario
    vetting_df.insert(
        2, "Name", vetting_df["Model"] + " " + vetting_df["Scenario"].astype(str)
    )
    vetting_df = vetting_df.set_index("Name")

    vetting_df[VETTING_COL] = vetting_df[VETTING_COL].str.upper()
    return vetting_df

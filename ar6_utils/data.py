import operator
import numpy as np
import pandas as pd

from .constants import NO_NET_ZERO, YEARS


def prepare_data(database, startyear=2010, endyear=2100, dt=5, onlyworld=True):
    if ".xls" in database:
        data_raw = pd.read_excel(database)
    else:
        data_raw = pd.read_csv(database)
    data_raw.columns = [str(c).capitalize() for c in data_raw.columns]

    # Choose only decadal data
    data = data_raw.loc[
        :,
        ["Model", "Scenario", "Region", "Variable", "Unit"]
        + [str(y) for y in np.arange(startyear, endyear + 1, dt)],
    ]

    # Choose only region == World
    if onlyworld:
        data = data[data["Region"] == "World"]

    # Add column Name, equal to Model + Scenario
    data.insert(2, "Name", data["Model"] + " " + data["Scenario"])

    # Interpolating missing 5 years columns
    interpolate_missing_5years(data, startyear=startyear + 5, endyear=endyear + 5)

    years = [str(y) for y in np.arange(startyear, endyear + 1, 5)]
    return data[
        ["Name", "Model", "Scenario", "Region", "Variable", "Unit"] + years
    ].rename(columns={y: int(y) for y in years})


def interpolate_missing_5years(data, startyear, endyear):
    for year in range(startyear, endyear, 10):
        if str(year) not in data.columns:
            data[str(year)] = np.nan
        data.loc[data[str(year)].isna(), str(year)] = data.loc[
            data[str(year)].isna(), [str(year - 5), str(year + 5)]
        ].mean(axis=1)


def create_scenarios(data):
    return data[["Model", "Scenario", "Name"]].groupby("Name").first()


def add_variable_year(scenarios, data, name, variable, year=2100):
    scenarios[name] = data[data["Variable"] == variable].set_index("Name")[year]


def add_variable_range(
    scenarios,
    data,
    name,
    variable,
    reduce_fct,
    clip_lower=None,
    clip_upper=None,
    year_low=2010,
    year_high=2100,
):
    scenarios[name] = (
        data[data["Variable"] == variable]
        .set_index("Name")
        .loc[:, year_low:year_high]
        .clip(lower=clip_lower, upper=clip_upper)
        .apply(reduce_fct, axis=1)
    )


# Simpler variables
def create_variable(
    df,
    var1,
    var2,
    new_name,
    opfunc,
    default_var1=None,
    default_var2=None,
    overwrite_unit=None,
    append=True,
):
    ops = {
        "+": operator.add,
        "-": operator.sub,
        "/": operator.truediv,
        "*": operator.mul,
    }

    td_both = df.loc[df["Variable"].isin([var1, var2])].copy()
    if overwrite_unit is not None:
        td_both["Unit"] = overwrite_unit
    join_keys = ["Model", "Scenario", "Name", "Region", "Variable", "Unit"]
    stacked = td_both.set_index(join_keys).rename_axis(columns="Year").stack()
    unstacked = stacked.unstack("Variable")
    if default_var1 is not None:
        unstacked.loc[unstacked[var1].isna(), var1] = default_var1
    if default_var2 is not None:
        unstacked.loc[unstacked[var2].isna(), var2] = default_var2

    combined = ops[opfunc](unstacked[var1], unstacked[var2])

    combined = combined.unstack("Year").reset_index()

    # Add variable name
    combined.insert(4, "Variable", new_name)

    if append:
        return pd.concat([df, combined])
    return combined


def add_variables(
    df,
    vars,
    new_name,
    default=None,
    overwrite_unit=None,
    append=True,
):
    td_all = df.loc[df["Variable"].isin(vars)].copy()
    if overwrite_unit is not None:
        td_all["Unit"] = overwrite_unit
    join_keys = ["Model", "Scenario", "Name", "Region", "Variable", "Unit"]
    stacked = td_all.set_index(join_keys).rename_axis(columns="Year").stack()
    unstacked = stacked.unstack("Variable")
    if default is not None:
        unstacked = unstacked.fillna(default)

    combined = unstacked.sum(axis=1).unstack("Year").reset_index()

    # Add variable name
    combined.insert(4, "Variable", new_name)

    if append:
        return df.append(combined)
    return combined


# Net-zero calculations
def calc_netzero(scenarios, data, variable, col_name, limit=0):
    scenarios[col_name] = np.nan

    _selection = data[data["Variable"] == variable]

    # If the 2100 value is larger than the limit, set it to NO_NET_ZERO
    above_limit = _selection.loc[_selection[2100] > limit, "Name"]
    scenarios.loc[scenarios.index.isin(above_limit), col_name] = NO_NET_ZERO

    _selection_has_negative_year = (_selection.loc[:, 2020:2100] <= limit).any(axis=1)
    _selection = _selection[_selection_has_negative_year].set_index("Name")
    for name, row in _selection.iterrows():
        if row.loc[2020:2100].isnull().any():
            continue
        index = row.loc[2020:2100].index
        first_negative_i = np.argmin(np.maximum(limit, row.loc[2020:2100].values))
        if first_negative_i == 0:
            net_zero = 2020
        else:
            year_0 = index[first_negative_i - 1]
            year_1 = index[first_negative_i]
            dy = row[year_1] - row[year_0]
            if dy == 0:
                if row[year_0] == 0:
                    net_zero = int(year_0)
                else:
                    net_zero = np.nan
                    print(name)
            else:
                net_zero = -row[year_0] * (int(year_1) - int(year_0)) / dy + int(year_0)
            #                 if net_zero > 2110 or net_zero < 2010:
            #                     net_zero = np.nan

            if name in scenarios.index:
                scenarios.loc[name, col_name] = net_zero
            else:
                print(name, "not in global scenarios")


def get_interp(data, name, variables, year, index_columns=None):
    if index_columns is None:
        index_columns = ["Name"]
        if len(variables) > 1:
            index_columns = index_columns + ["Variable"]
    if name is None:
        selection = data
    else:
        if isinstance(name, str):
            name = [name]
        selection = data[data["Name"].isin(name)]
    row = selection[selection["Variable"].isin(variables)].set_index(index_columns)
    year0 = int((year // 5) * 5)
    year1 = year0 + 5
    v0 = row[year0]
    v1 = row[year1]
    p = (year - year0) / (year1 - year0)
    interp = v0 * (1 - p) + v1 * p  # .unstack(index_columns)
    if name is not None and len(name) == 1:
        interp = interp.iloc[:, 0]
    return interp, year0, year1


def get_interp_indexed(series, year):
    if isinstance(series, pd.Series):
        index = series.index
        last = series.iloc[-1]
    else:
        index = series.columns
        last = series.iloc[:, -1]
    if year >= int(index[-1]):
        return last, int(index[-1]), int(index[-1])
    year0 = int((year // 5) * 5)
    year1 = year0 + 5
    v0 = series[year0]
    v1 = series[year1]
    p = (year - year0) / (year1 - year0)
    return v0 * (1 - p) + v1 * p, year0, year1


def NBZ_names(vetted_scenarios, categories, is_nbz=True, threshold=50e3):
    selection = vetted_scenarios[vetted_scenarios["Category"].isin(categories)]
    if is_nbz is True:
        selection = selection[selection["Total net negative"] < threshold]
    elif is_nbz is False:
        selection = selection[selection["Total net negative"] >= threshold]
    return selection.index


def get_single(data, name, variable):
    selection = data[(data["Name"] == name) & (data["Variable"] == variable)]
    if len(selection) != 1:
        return None

    return selection.set_index(["Name", "Variable"]).iloc[0].loc[YEARS]

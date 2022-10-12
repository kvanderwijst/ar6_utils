from typing import Dict
import numpy as np
import pandas as pd

from .constants import SSP_SCENARIOS, YEARS, IP_SCENARIOS
from .data import get_interp, get_interp_indexed


class Var:
 
    index_columns = ["Name"]

    def __init__(
        self,
        data,
        scenarios,
        vetted_scenarios,
        variable=None,
        year=None,
        region=None,
        values=None,
        default=None,
        select_unit=None,
        unit="",
        make_positive=False, # Take absolute value of all values
    ):
        self.data = data
        self.scenarios = scenarios
        self.vetted_scenarios = vetted_scenarios
        self.unit = unit

        if variable is None and values is None:
            raise Exception("variable and values cannot both be None")
        if variable is not None and values is not None:
            raise Exception("variable and values cannot both be defined")

        if variable is not None:
            self._variable = variable
            if year is None:
                year = YEARS
            to_series = not isinstance(year, (tuple, list))
            year = _to_list(year, to_str=False)
            self._year = year[0] if to_series else year

            # `year` is a list that can contain different types:
            # - Numbers (years)
            #    - Existing years
            #    - Years that need to be interpolated
            # - Strings, corresponding to meta columns containing a year value for each scenario
            years_numbers = [y for y in year if isinstance(y, (int, float))]
            existing_years = list(set(years_numbers).intersection(set(YEARS)))
            interp_years = list(set(years_numbers) - set(YEARS))
            years_meta_columns = list(set(year) - set(years_numbers))

            # First get years that already exist
            selection_data = data[data["Variable"].isin(_to_list(variable))]
            if isinstance(variable, (tuple, list)):
                # Add "Variable" to the index columns
                self.index_columns = list(self.index_columns) + ["Variable"]

            if region is not None:
                selection_data = selection_data[
                    selection_data["Region"].isin(_to_list(region))
                ]
                if not isinstance(region, (tuple, list)):
                    # Remove "Region" from the index columns
                    self.index_columns = [
                        c for c in self.index_columns if c != "Region"
                    ]
            if select_unit is not None:
                selection_data = selection_data[
                    selection_data["Unit"].isin(_to_list(select_unit))
                ]
                if isinstance(select_unit, (tuple, list)):
                    # Add "Unit" to the index columns
                    self.index_columns = list(self.index_columns) + ["Unit"]

            selection = selection_data.set_index(self.index_columns)
            self._values = selection[existing_years].rename_axis(columns="Year")
            # Then interpolate all other years:
            for y in interp_years:
                self._values[y] = get_interp(
                    selection_data, None, [variable], float(y), self.index_columns
                )[0].T.iloc[:, 0]

            # Then interpolate year values from meta columns (e.g. net-zero columns)
            for column in years_meta_columns:
                self._values[column] = self._interp_value_year_from_meta_column(
                    selection[YEARS], column
                )

            self._values = self._values[self._year]
            if isinstance(self._values, pd.Series):
                self._values.name = "Value"

        if values is not None:
            if isinstance(values, pd.Series):
                self._year = values.name
                values.name = "Value"
            else:
                self._year = list(values.columns)
            self._values = values

        self.default = default
        if self.default is not None:
            self._values = self._values.fillna(self.default)

        if make_positive:
            self._values = abs(self._values)

    def select(
        self, meta: Dict = None, value=None, ip=None, ssp=None, long_format=True,
    ):
        """
        Filter the resulting values dataframe

        (a) Use `meta` to pass a dictionary with meta-columns as keys. The values can be "all" or any/subset of the values of that column.
            
            Example: datavar("Emissions|CO2").select({"Category": ["C1", "C2"]})
            
            ## Selects the CO2 emission paths of all scenarios with climate category C1 or C2


        (b) Choose between the following filters:
        - value:    a list of values or a range using pd.Interval

            Example: datavar("Emissions|CO2", 2050).select(value=pd.Interval(0, 20))
            
            ## Selects all scenarios with CO2 emissions in 2050 between 0 and 20 GtCO2
            
        - ip:       None, "all" or any/subset of [CurPol, ModAct, GS, Neg, Ren, LD, SP]
        - ssp:      None, "all" or any/subset of [SSP1-19, SSP1-26, SSP4-34, SSP2-45, SSP4-60, SSP3-70, SSP5-85]

        """

        selection = self.vetted_scenarios.copy()
        extra_columns = []

        # Meta
        if meta is None:
            meta = {}
        for column, _value in meta.items():
            if column == selection.index.name:
                values = _to_list(_value)
                selection = selection[selection.index.isin(values)]

            else:

                # Check if column exists
                if column not in selection.columns:
                    raise KeyError(
                        f"{column} is not an existing column in the metadata"
                    )

                if _value != "all":
                    mask = (selection[column] == True) & False  # Start with empty mask
                    values = _to_list(_value)
                    # Check for ranges:
                    ranges = [v for v in values if isinstance(v, pd.Interval)]
                    for v in ranges:
                        mask = mask | selection[column].between(v.left, v.right)

                    # All other values:
                    mask = mask | selection[column].isin(values)
                else:
                    mask = ~selection[column].isna()
                selection = selection[mask]
                extra_columns.append(column)

        # Value selection
        if value is not None and value != "all":
            values = _to_list(value)
            selection_names = set()

            # Check for ranges:
            ranges = [v for v in values if isinstance(v, pd.Interval)]
            for v in ranges:
                _names = self._values[
                    _all_row(self._values >= v.left) & _all_row(self._values <= v.right)
                ].index
                selection_names = selection_names.union(set(_names))

            # All other values:
            for v in values:
                if v not in ranges:
                    _names = self._values[_all_row(self._values == v)].index
                    selection_names = selection_names.union(set(_names))

            selection = selection[selection.index.isin(selection_names)]

        # Illustrative Pathways
        if ip is not None:
            if ip == "all":
                ip = list(IP_SCENARIOS.keys())
            ip = _to_list(ip)
            for v in ip:
                if v not in IP_SCENARIOS:
                    raise KeyError(
                        f"{v} is not a valid IP [{', '.join(IP_SCENARIOS.keys())}]"
                    )
            selection = selection[
                selection.index.isin([IP_SCENARIOS[v].scenario for v in ip])
            ]
            extra_columns.append("IP")

        # SSP
        if ssp is not None:
            if ssp == "all":
                ssp = list(SSP_SCENARIOS.keys())
            # Add SSPs from unvetted scenarios, since
            # SSP1-19, SSP4-34, SSP4-60 and SSP3-70 do not pass vetting
            ssp = _to_list(ssp)
            for v in ssp:
                if v not in SSP_SCENARIOS:
                    raise KeyError(
                        f"{v} is not a valid SSP [{', '.join(SSP_SCENARIOS.keys())}]"
                    )
            selection = selection[
                selection.index.isin([SSP_SCENARIOS[v].scenario for v in ssp])
            ]
            for v in ssp:
                if SSP_SCENARIOS[v].scenario not in selection.index:
                    # Add unvetted ssp
                    selection = selection.append(
                        self.scenarios.loc[SSP_SCENARIOS[v].scenario]
                    )
            extra_columns.append("SSP")

        subset_values = self._values[
            self._values.index.get_level_values("Name").isin(selection.index)
        ]
        is_series = isinstance(subset_values, pd.Series)
        if is_series:
            subset_values = subset_values.to_frame()

        index_columns = list(subset_values.index.names)
        # Merge with extra columns
        subset_values = subset_values.merge(
            selection[extra_columns], left_index=True, right_index=True, how="left"
        ).reset_index()
        if len(extra_columns) > 0:
            subset_values = subset_values.sort_values(extra_columns)
        subset_values = subset_values.set_index(
            extra_columns + index_columns
        ).rename_axis(columns="Year")
        if is_series:
            if long_format:
                return subset_values.reset_index().rename_axis(columns=None)

            # Change back to Series
            return subset_values.iloc[:, 0]

        if long_format:
            if str in [type(col) for col in subset_values.columns]:
                return subset_values.reset_index().rename_axis(columns=None)
            return subset_values.stack().to_frame("Value").reset_index()
        return subset_values

    def _repr_html_(self):
        n = len(self._values)
        print(
            f"Data object with {n} scenarios.\nUnit: {self.unit}.\nUse obj.select(...) to access values dataframe."
        )
        try:
            return self._values._repr_html_()
        except AttributeError:
            print(self._values.__repr__())

    def _check_and_harmonise_inputs(self, other):
        if isinstance(other, (int, float)):
            return self._values, other
        return self._check_and_harmonise_inputs_columns(other)

    def _check_and_harmonise_inputs_columns(self, other):

        y1, y2 = self._year, other._year

        self_values = self._values
        other_values = other._values

        # Case 1: both are multiple years
        if isinstance(y1, list) and isinstance(y2, list):
            if set(y1) != set(y2):
                raise Exception(f"Years of left var ({y1}) not compatible with ({y2})")

        # Case 2: self multiple years, other single year
        elif isinstance(y1, list) and not isinstance(y2, list):
            # Duplicate values of other to have the same value
            # at every year of self
            harmonised_values2 = pd.DataFrame({year: other._values for year in y1})
            other_values = harmonised_values2

        # Case 3: inverse of case 2
        elif not isinstance(y1, list) and isinstance(y2, list):
            harmonised_values1 = pd.DataFrame({year: self._values for year in y2})
            self_values = harmonised_values1

        # Case 4: var1 and var2 are single year: do nothing

        return self._check_and_harmonise_inputs_indices(self_values, other_values)

    def _check_and_harmonise_inputs_indices(self, self_values, other_values):
        names_self = set(self_values.index.names)
        names_other = set(other_values.index.names)
        # Case 1: names_self and names_other are equal: nothing needs to happen
        if names_self == names_other:
            return self_values, other_values

        # Case 2: names_self is a subset of names_other: broadcast of names_self to names_other
        if names_self.issubset(names_other):
            self_values = other_values * 0 + self_values
        # Case 3: names_other is a subset of names_self: broadcast of names_other to names_self
        elif names_other.issubset(names_self):
            other_values = self_values * 0 + other_values
        else:
            raise Exception(
                f"Index levels {names_self} not compatible with {names_other}."
            )
        return self_values, other_values

    def _interp_value_year_from_meta_column(self, data, column):
        def _get_value_fct(row):
            try:
                year = min(2101, self.scenarios.loc[row.name, column])
                if year <= 2100:
                    return get_interp_indexed(row, year)[0]
                else:
                    return np.nan
            except KeyError:
                return np.nan

        return data.apply(lambda row: _get_value_fct(row), axis=1)

    def __add__(self, other):
        self_values, other_values = Var._check_and_harmonise_inputs(self, other)
        new_values = self_values.add(other_values, fill_value=getattr(other, "default", None))
        other_unit = getattr(other, "unit", "[?]")
        if isinstance(other, (int, float)) or other_unit == self.unit:
            new_unit = self.unit
        else:
            new_unit = f"({self.unit} + {other_unit})"
        return Var(
            self.data,
            self.scenarios,
            self.vetted_scenarios,
            values=new_values,
            default=self.default,
            unit=new_unit,
        )

    def __radd__(self, other):
        return self.__add__(other)

    def __sub__(self, other):
        self_values, other_values = Var._check_and_harmonise_inputs(self, other)
        new_values = self_values.sub(other_values, fill_value=getattr(other, "default", None))
        other_unit = getattr(other, "unit", "[?]")
        if isinstance(other, (int, float)) or other_unit == self.unit:
            new_unit = self.unit
        else:
            new_unit = f"({self.unit} - {other_unit})"
        if other_unit == self.unit:
            new_unit = self.unit
        else:
            new_unit = f"({self.unit} - {other_unit})"
        return Var(
            self.data,
            self.scenarios,
            self.vetted_scenarios,
            values=new_values,
            default=self.default,
            unit=new_unit,
        )

    def __neg__(self):
        return self.__rsub__(0)

    def __rsub__(self, other):
        self_values, other_values = Var._check_and_harmonise_inputs(self, other)
        new_values = self_values.rsub(other_values, fill_value=getattr(other, "default", None))
        other_unit = getattr(other, "unit", "[?]")
        if isinstance(other, (int, float)) or other_unit == self.unit:
            new_unit = self.unit
        else:
            new_unit = f"({other_unit} - {self.unit})"
        if other_unit == self.unit:
            new_unit = self.unit
        else:
            new_unit = f"({other_unit} - {self.unit})"
        return Var(
            self.data,
            self.scenarios,
            self.vetted_scenarios,
            values=new_values,
            default=self.default,
            unit=new_unit,
        )

    def __mul__(self, other):
        self_values, other_values = Var._check_and_harmonise_inputs(self, other)
        new_values = self_values.mul(other_values, fill_value=getattr(other, "default", None))
        other_unit = getattr(other, "unit", "[?]")
        if isinstance(other, (int, float)):
            new_unit = self.unit
        else:
            new_unit = f"({self.unit} * {other_unit})"
        return Var(
            self.data,
            self.scenarios,
            self.vetted_scenarios,
            values=new_values,
            default=self.default,
            unit=new_unit,
        )

    __rmul__ = __mul__

    def __pow__(self, other):
        self_values, other_values = Var._check_and_harmonise_inputs(self, other)
        new_values = self_values ** other_values
        other_unit = getattr(other, "unit", "[?]")
        if isinstance(other, (int, float)):
            new_unit = f"({self.unit} ** {other})"
        else:
            new_unit = f"({self.unit} ** {other_unit})"
        return Var(
            self.data,
            self.scenarios,
            self.vetted_scenarios,
            values=new_values,
            default=self.default,
            unit=new_unit,
        )

    def __truediv__(self, other):
        self_values, other_values = Var._check_and_harmonise_inputs(self, other)
        new_values = self_values.truediv(other_values, fill_value=getattr(other, "default", None))
        other_unit = getattr(other, "unit", "[?]")
        if isinstance(other, (int, float)):
            new_unit = self.unit
        elif self.unit == other_unit:
            new_unit = "[dimensionless]"
        else:
            new_unit = f"({self.unit} / {other_unit})"
        return Var(
            self.data,
            self.scenarios,
            self.vetted_scenarios,
            values=new_values,
            default=self.default,
            unit=new_unit,
        )

    def __rtruediv__(self, other):
        self_values, other_values = Var._check_and_harmonise_inputs(self, other)
        new_values = self_values.rtruediv(other_values, fill_value=getattr(other, "default", None))
        other_unit = getattr(other, "unit", "[?]")
        if isinstance(other, (int, float)):
            new_unit = self.unit
        elif self.unit == other_unit:
            new_unit = "[dimensionless]"
        else:
            new_unit = f"({other_unit}) / ({self.unit})"
        return Var(
            self.data,
            self.scenarios,
            self.vetted_scenarios,
            values=new_values,
            default=self.default,
            unit=new_unit,
        )


class RegionalVar(Var):
    index_columns = ["Name", "Region"]


class MetaVar(Var):
    def __init__(
        self,
        data,
        scenarios,
        vetted_scenarios,
        metacolumn=None,
        values=None,
        default=None,
    ):
        self.data = data
        self.scenarios = scenarios
        self.vetted_scenarios = vetted_scenarios

        self.unit = "[meta]"

        if metacolumn is None and values is None:
            raise Exception("variable and values cannot both be None")
        if metacolumn is not None and values is not None:
            raise Exception("variable and values cannot both be defined")

        if metacolumn is not None:
            self._variable = "meta"
            to_series = not isinstance(metacolumn, (tuple, list))
            metacolumn = _to_list(metacolumn, to_str=False)
            self._year = metacolumn[0] if to_series else metacolumn

            # First get years that already exist
            self._values = self.scenarios[self._year]

        if values is not None:
            if isinstance(values, pd.Series):
                self._year = values.name
            else:
                self._year = list(values.columns)
            self._values = values

        self.default = default
        if self.default is not None:
            self._values = self._values.fillna(self.default)


class DataVar:
    def __init__(self, data, scenarios=None, vetted_scenarios=None, is_regional=False):
        if scenarios is None:
            # If no metadata is provided, make an empty metadata dataframe
            scenarios = data.groupby("Name").first()[["Model", "Scenario"]]
        if vetted_scenarios is None:
            vetted_scenarios = scenarios
        self.data = data
        self.scenarios = scenarios
        self.meta = self.scenarios  # Two names for same thing
        self.vetted_scenarios = vetted_scenarios

        # Check if there are multiple regions present in data:
        if is_regional:
            self.var_obj = RegionalVar
        else:
            self.var_obj = Var

        # Create unit-dictionary
        self.units = self._create_unit_map()

    def __call__(
        self, variable=None, year=None, meta=None, region=None, unit=None, **kwargs
    ):
        if meta is not None:
            if variable is not None:
                raise Exception(
                    "The arguments `variable` and `meta` cannot be both set."
                )
            return MetaVar(
                self.data, self.scenarios, self.vetted_scenarios, meta, **kwargs
            )

        select_unit = unit
        if unit is None:
            if isinstance(variable, (tuple, list)):
                unit = " or ".join({self.units.get(var, "") for var in variable})
            else:
                unit = self.units.get(variable, "")
        return self.var_obj(
            self.data,
            self.scenarios,
            self.vetted_scenarios,
            variable,
            year,
            region=region,
            select_unit=select_unit,
            unit=unit,
            **kwargs,
        )

    def _create_unit_map(self):
        # Check if variables all map to one unit. If not, take the unit which occurs most often
        units = (
            self.data.groupby(["Variable", "Unit"])
            .count()
            .iloc[:, 0]
            .sort_values(ascending=False)
            .reset_index()
            .groupby("Variable")
            .first()["Unit"]
            .to_dict()
        )
        return units


def _to_list(value, to_str=False):
    if isinstance(value, (tuple, list, pd.Series)):
        return [str(v) for v in value] if to_str else value
    return [str(value)] if to_str else [value]


def _all_row(mask):
    """
    Returns mask.all(axis=1) if mask is a dataframe.
    If mask is a series returns mask
    """
    if isinstance(mask, pd.DataFrame):
        return mask.all(axis=1)
    return mask

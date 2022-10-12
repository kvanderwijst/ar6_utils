import colorsys

import numpy as np


class variables:
    DELTA_T = 10
    TEMPERATURE_P50 = "AR6 climate diagnostics|Surface Temperature (GSAT)|MAGICCv7.5.3|50.0th Percentile"
    TEMPERATURE_P66 = "AR6 climate diagnostics|Surface Temperature (GSAT)|MAGICCv7.5.3|67.0th Percentile"
    RF_P50 = "AR6 climate diagnostics|Effective Radiative Forcing|MAGICCv7.5.3|50.0th Percentile"
    RF_P66 = "AR6 climate diagnostics|Effective Radiative Forcing|MAGICCv7.5.3|67.0th Percentile"
    CO2 = "Emissions|CO2"
    CH4 = "Emissions|CH4"
    N2O = "Emissions|N2O"
    # KYOTO = "Emissions|Kyoto Gases"
    KYOTO = "AR6 climate diagnostics|Native-with-Infilled|Emissions|Kyoto Gases (AR6-GWP100)"
    CCS = "Carbon Sequestration|CCS"
    PRIMARY_ENERGY = "Primary Energy"
    PRIMARY_ENERGY_FOSSIL = "Primary Energy|Fossil"
    PRIMARY_ENERGY_NUCLEAR = "Primary Energy|Nuclear"
    PRIMARY_ENERGY_BIOMASS = "Primary Energy|Biomass"
    FINAL_ENERGY = "Final Energy"
    FOODDEMAND_LIVESTOCK = "Food Demand|Livestock"


def hex_to_rgb(hex, normalise=False):
    h = hex.lstrip("#")
    rgb = [int(h[i : i + 2], 16) for i in (0, 2, 4)]
    if normalise:
        return [x / 255.0 for x in rgb]
    else:
        return rgb


def rgb_to_hex(rgb):
    return "#%02x%02x%02x" % tuple(rgb)


def hex_to_hls(hex):
    return colorsys.rgb_to_hls(*hex_to_rgb(hex, True))


def hls_to_hex(hls):
    return rgb_to_hex([int(np.round(x * 255)) for x in colorsys.hls_to_rgb(*hls)])


def hex_to_rgba(value, alpha):
    value = value.lstrip("#")
    lv = len(value)
    lst = [int(value[i : i + lv // 3], 16) for i in range(0, lv, lv // 3)] + [alpha]
    return list_to_rgba(lst)


def list_to_rgba(lst):
    return "rgba({0},{1},{2},{3})".format(*lst)


def lighten_hex(hex, extra_lightness=0.1, extra_saturation=0.0):
    hls = list(hex_to_hls(hex))
    hls[1] += extra_lightness
    hls[2] += extra_saturation
    return hls_to_hex(hls)


def linearInterp(row):
    years = row.index.astype(float)
    return np.trapz(row, x=years)

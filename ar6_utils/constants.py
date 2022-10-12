from dataclasses import dataclass


NO_NET_ZERO = 2110

YEARS = list(range(2010, 2105, 5))

COLORS_CATEGORIES = {
    # "C0": "#649B1C",
    "C1": "#00B593",
    "C2": "#4e84d4",
    "C3": "#f4a506",
    "C4": "#e8663b",
    "C5": "#9b2270",
    "C6": "#231123",
    "C7": "#E3063A",
    "no-climate-assessment": "#999999",
    "": "#999999",
}

SEQUENTIAL_COLORS = [
    "#00c0c7",
    "#5144d3",
    "#e8871a",
    "#da3490",
    "#47e26f",
    "#9089fa",
    "#2780eb",
    "#6f38b1",
    "#dfbf03",
    "#cb6f10",
    "#268d6c",
    "#9bec54",
]


@dataclass
class Ip:
    name: str
    scenario: str
    color: str
    symbol: str
    fullname: str
    dash: str = "solid"


IP_SCENARIOS = {
    "CurPol": Ip(
        "CurPol",
        "GCAM 5.3 NGFS2_Current Policies",
        "#e51f26",
        "triangle-up",
        "Policies implemented until<br>the end of 2020 (CurPol)",
    ),
    "ModAct": Ip(
        "ModAct",
        "IMAGE 3.0 EN_INDCi2030_3000f",
        "#f39121",
        "triangle-down",
        "Moderate Action (ModAct)",
    ),
    "GS": Ip(
        "GS",
        "WITCH 5.0 CO_Bridge",
        "#6f7799",
        "hourglass",
        "Gradual strengthening<br>of policies (IMP-GS)",
    ),
    "Neg": Ip(
        "Neg",
        "COFFEE 1.1 EN_NPi2020_400f_lowBECCS",
        "#8fa66c",
        "circle",
        "Focus on negative<br>emissions (IMP-Neg)",
    ),
    "LD": Ip(
        "LD",
        "MESSAGEix-GLOBIOM 1.0 LowEnergyDemand_1.3_IPCC",
        "#4aa6c3",
        "diamond",
        "Focus on low demand (IMP-LD)",
        "3px,2px",
    ),
    "Ren": Ip(
        "Ren",
        "REMIND-MAgPIE 2.1-4.3 DeepElec_SSP2_ HighRE_Budg900",
        "#2d7c8e",
        "star",
        "Focus on renewables (IMP-Ren)",
        "5px,4px",
    ),
    "SP": Ip(
        "SP",
        "REMIND-MAgPIE 2.1-4.2 SusDev_SDP-PkBudg1000",
        "#134e54",
        "cross",
        "Shifting pathways (IMP-SP)",
        "10px,8px",
    ),
}


@dataclass
class Ssp:
    name: str
    scenario: str
    color: str


SSP_SCENARIOS = {
    "SSP1-19": Ssp("SSP1-19", "IMAGE 3.0.1 SSP1-19", "#00B593"),
    "SSP1-26": Ssp("SSP1-26", "IMAGE 3.0.1 SSP1-26", "#4e84d4"),
    "SSP4-34": Ssp("SSP4-34", "GCAM 4.2 SSP4-34", "#f4a506"),
    "SSP2-45": Ssp("SSP2-45", "MESSAGE-GLOBIOM 1.0 SSP2-45", "#e8663b"),
    "SSP4-60": Ssp("SSP4-60", "GCAM 4.2 SSP4-60", "#9b2270"),
    "SSP3-70": Ssp("SSP3-70", "AIM/CGE 2.0 SSP3-Baseline", "#999"),
    "SSP5-85": Ssp("SSP5-85", "REMIND-MAgPIE 1.5 SSP5-Baseline", "#231123"),
}

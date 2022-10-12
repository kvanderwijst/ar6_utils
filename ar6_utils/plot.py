import json
import plotly.io as pio
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
import importlib.resources as pkg_resources

PLOTLY_WIDTH_PX = 1050
PAGE_WIDTH_MM = 170.65


def mm_to_px(mm, width_mm=PAGE_WIDTH_MM, width_px=PLOTLY_WIDTH_PX):
    return mm / width_mm * width_px


def pt_to_px(pt):
    mm = 0.353 * pt
    return mm_to_px(mm)


SVG_DPI = 96  # This is default from Plotly export, we cannot change that
SVG_SCALE = (PAGE_WIDTH_MM / 25.4) / (
    PLOTLY_WIDTH_PX / SVG_DPI
)  # page width in inch (div. by 25.4)

FRUTIGER = '"Frutiger LT Pro Condensed", "Open Sans", verdana, arial, sans-serif'

IPCC_COLORS = [
    "#5492cd",
    "#ffa900",
    "#003466",
    "#EF550F",
    "#990002",
    "#c47900",
    "#00aad0",
    "#76797b",
]

CATEGORIES_COLORS = [
    "#97CEE4",
    "#778663",
    "#6F7899",
    "#A7C682",
    "#8CA7D0",
    "#FAC182",
    "#F18872",
    "#bd7161",
]

pio.templates["ipcc"] = go.layout.Template(
    {
        "data": dict(
            scatter=[
                go.Scatter(marker_color=color, line_color=color)
                for color in IPCC_COLORS
            ],
            heatmap=[go.Heatmap(colorbar_outlinewidth=0)],
            heatmapgl=[go.Heatmapgl(colorbar_outlinewidth=0)],
        ),
        "layout": dict(
            title={
                "font_family": FRUTIGER,
                "font_size": pt_to_px(11),
                "xanchor": "left",
                "x": 0.01,
            },
            plot_bgcolor="#F5F5F5",
            font={"family": FRUTIGER, "size": pt_to_px(7), "color": "#25292b",},
            legend={
                "font_size": pt_to_px(7),
                "title_font_size": pt_to_px(7),
                "y": 0.5,
                "tracegroupgap": 0,
            },
            colorway=CATEGORIES_COLORS,
            coloraxis={"colorbar": {"outlinewidth": 0, "ticks": ""}},
            barmode="relative",
            xaxis=dict(
                title_font_size=pt_to_px(8),
                title_standoff=0,
                gridcolor="#d0d0d0",
                gridwidth=pt_to_px(0.25),
                zerolinecolor="#8e8e8d",
                zerolinewidth=2,
                ticks="",
                automargin=True,
            ),
            yaxis=dict(
                title_font_size=pt_to_px(8),
                title_standoff=0,
                ticksuffix=" ",
                gridcolor="#d0d0d0",
                gridwidth=pt_to_px(0.25),
                zerolinecolor="#8e8e8d",
                zerolinewidth=2,
                ticks="",
                automargin=True,
            ),
            margin={"t": 60, "r": 50},
        ),
    }
)


def line_continuous_error_bars(
    df, groupby_columns, value_col="Value", q_low=0.05, q_high=0.95, **kwargs
):
    grouped_df = df.groupby(groupby_columns)[value_col]

    low_high = (
        grouped_df.quantile([q_low, q_high])
        .unstack(level=-1)
        .rename_axis(columns="Quantile")
        .stack()
        .to_frame(value_col)
        .reset_index()
    )

    _fig1 = px.line(low_high, line_group="Quantile", **kwargs).for_each_trace(
        lambda t: t.update(fill="tonexty" if str(q_high) in t.hovertemplate else "none")
    )

    _fig2 = px.line(grouped_df.quantile(0.5).reset_index(), **kwargs)

    return go.Figure(
        _fig1.update_traces(line_width=0, showlegend=False).data + _fig2.data,
        layout=_fig2.layout,
    )

def add_funnel(
    fig: go.Figure,
    df: pd.DataFrame,
    col_low=None,
    col_high=None,
    col_median=None,
    col_x=None,
    color="#333",
    row=1,
    col=1,
    showlegend=True,
    **kwargs,
):
    """
    If col_x is None, uses the index as x values
    """
    x_values = df[col_x] if col_x is not None else df.index

    with_range = col_low is not None and col_high is not None

    if with_range:
        y_values_low = df[col_low]
        y_values_high = df[col_high]

        y_values = np.concatenate([y_values_low, y_values_high[::-1]])
        x_values_combined = np.concatenate([x_values, x_values[::-1]])

        trace = go.Scatter(
            x=x_values_combined,
            y=y_values,
            fill="toself",
            line={"width": 0, "color": "rgba(0,0,0,0)"},
            fillcolor=color,
            opacity=0.3,
            showlegend=showlegend,
        ).update(**kwargs)
        fig.add_trace(trace, row=row, col=col)

    if col_median is not None:
        trace = go.Scatter(
            x=x_values,
            y=df[col_median],
            line={"width": 2, "color": color},
            mode="lines",
            showlegend=False if with_range else showlegend,
        ).update(**kwargs)
        fig.add_trace(trace, row=row, col=col)

    return fig



def left_align_subplot_titles(fig):
    """Should be called directly after calling `make_subplots(...)`,
    otherwise new annotations besides the subtitles can be created."""
    for i, ann in enumerate(fig.layout.annotations):
        x = fig.layout[f"xaxis{i+1}"].domain[0]
        ann.update(x=x, xanchor="left", align="left")


from . import geodata

MACROREGIONS_GEO = json.loads(pkg_resources.read_text(geodata, "macroregions.json"))

from typing import List
import plotly.graph_objects as go


# TODO: Make a separate WaterfallItem and WaterfallArrowItem,
# both inheriting from a common GeneralWaterfallItem


class WaterfallItem:
    def __init__(
        self,
        measure,
        label=None,
        median=None,
        p05=None,
        p95=None,
        xshift=None,
        connect_with_previous=True,
        color="#444",
        pattern_shape=None,
        showlegend=False,
        begin_arrow=False,
        arrow_shift=5,
        extra_style=None,
        width=0.8,
    ):
        if measure not in [
            "absolute",
            "total",
            "relative",
            "reset",
            "draw_arrow",
        ]:
            raise NotImplementedError("Bad waterfall measure type provided")

        self.measure = measure
        self.label = label
        self.median = median
        self.p05 = p05
        self.p95 = p95
        self.xshift = (0 if measure == "reset" else 1) if xshift is None else xshift
        self.connect_with_previous = connect_with_previous
        self.color = color
        self.pattern_shape = pattern_shape
        self.showlegend = showlegend
        self.begin_arrow = begin_arrow
        self.arrow_shift = arrow_shift
        self.extra_style = {} if extra_style is None else extra_style
        self.width = width


def add_waterfall(
    fig: go.Figure,
    waterfall_values: List[WaterfallItem],
    row,
    col,
    startx=0,
    xlabels=None,
    connecting_line_color="#000",
):

    output_data = {}

    if xlabels is None:
        xlabels = {}
    previous_median = 0
    i = 0
    arrow_start_x, arrow_start_y = 0, 0
    arrow_max, arrow_min = 0, 0
    for item in waterfall_values:
        measure = item.measure

        if measure == "draw_arrow":
            arrow_end_x = i
            arrow_end_y = previous_median
            draw_arrow(
                fig,
                arrow_start_x,
                arrow_start_y,
                arrow_end_x,
                arrow_end_y,
                arrow_max,
                arrow_min,
                item,
                row,
                col,
            )
            continue

        i += item.xshift

        if item.begin_arrow:
            arrow_start_x = i
            arrow_start_y = previous_median
            arrow_max = arrow_start_y
            arrow_min = arrow_start_y

        if measure == "reset":
            previous_median = item.median
            continue
        x = i + startx
        xlabels[x] = item.label
        if measure == "relative":
            median = item.median
            # Add transparent bar to move the bar up
            y_start = min(previous_median + median, previous_median)
            fig.add_bar(
                x=[x],
                y=[y_start],
                width=[item.width],
                marker_color="rgba(0,0,0,0)",
                marker_line={"color": "rgba(0,0,0,0)"},
                showlegend=False,
                row=row,
                col=col,
            )

            next_median = previous_median + median
        if measure == "absolute":
            median = item.median
            next_median = median
            y_start = 0
        if measure == "total":
            median = previous_median
            next_median = 0
            y_start = 0

        y_height = abs(median) if measure == "relative" else median

        arrow_max = max(arrow_max, next_median)
        arrow_min = min(arrow_min, next_median)

        fig.add_bar(
            x=[x],
            y=[y_height],
            width=[item.width],
            marker_color=item.color,
            marker_line={"color": item.color, "width": 1},
            marker_pattern_shape=item.pattern_shape,
            showlegend=item.showlegend,
            row=row,
            col=col,
            **item.extra_style,
        )

        if item.connect_with_previous:
            x0 = x - item.xshift + item.width / 2
            x1 = x - item.width / 2
            add_waterfall_connecting_line(
                fig,
                x0,
                x1,
                previous_median,
                row,
                col,
                connecting_line_color=connecting_line_color,
            )

        previous_median = next_median

        output_data[item.label] = {
            "type": measure,
            "label": item.label,
            "y_start": y_start,
            "y_height": y_height,
        }

        # Add error bars
        if item.p05 is not None and item.p95 is not None:
            error_bar_up = abs(median - item.p95)
            error_bar_down = abs(item.p05 - median)
            fig.add_scatter(
                x=[x],
                y=[previous_median],
                error_y={
                    "type": "data",
                    "symmetric": False,
                    "array": [error_bar_up],
                    "arrayminus": [error_bar_down],
                },
                line_color="#000",
                mode="lines",
                showlegend=False,
                row=row,
                col=col,
            )
            output_data[item.label]["error_bar"] = {
                "up": error_bar_up,
                "down": error_bar_down,
            }

    fig.update_xaxes(
        col=col,
        row=row,
        tickmode="array",
        tickvals=list(xlabels.keys()),
        ticktext=list(xlabels.values()),
    )

    return xlabels, output_data


def add_waterfall_connecting_line(
    fig, x0, x1, y, row, col, connecting_line_color, **kwargs
):
    fig.add_shape(
        type="line",
        row=row,
        col=col,
        x0=x0,
        x1=x1,
        y0=y,
        y1=y,
        line={"width": 1, "color": connecting_line_color},
        **kwargs,
    )


def draw_arrow(
    fig: go.Figure,
    start_x,
    start_y,
    end_x,
    end_y,
    max_y,
    min_y,
    item: WaterfallItem,
    row,
    col,
):
    # Calculate x and y axis name from (row, col) subplot
    # Note that the anchor of yaxis gives the xaxis and vice versa
    xref = fig.get_subplot(row, col).yaxis.anchor
    yref = fig.get_subplot(row, col).xaxis.anchor

    shift = item.arrow_shift
    yanchor = "bottom" if shift > 0 else "top"

    y_top = (max_y if shift > 0 else min_y) + shift

    common_kwargs = {
        "xref": xref,
        "yref": yref,
        "yanchor": yanchor,
        "arrowcolor": item.color,
        "arrowsize": 1.5,
    }

    # Left part of arrow
    fig.add_annotation(
        ayref=yref, x=start_x, y=start_y, ax=0, ay=y_top, **common_kwargs
    )

    # Horizontal part of arrow
    fig.add_annotation(axref=xref, x=start_x, y=y_top, ax=end_x, ay=0, **common_kwargs)

    # Right part of arrow
    fig.add_annotation(
        ayref=yref, x=end_x, y=end_y, ax=0, ay=y_top, arrowhead=2, **common_kwargs
    )

    # Text for the arrow
    text = "{:+.1f}".format(end_y - start_y)
    fig.add_annotation(
        **common_kwargs, showarrow=False, x=(start_x + end_x) / 2, y=y_top, text=text
    )
    pass

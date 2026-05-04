from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import plotly.express as px
from plotly.graph_objects import Figure

from src.descriptive_stats import _coerce_numeric


def _configure_kaleido_browser() -> None:
    if os.environ.get("BROWSER_PATH"):
        return

    browser_candidates = (
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
    )
    for candidate in browser_candidates:
        if Path(candidate).exists():
            os.environ["BROWSER_PATH"] = candidate
            return


def _clean_for_plot(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    plotted = df[columns].copy()
    for column in columns:
        if plotted[column].dtype == "object":
            plotted[column] = plotted[column].astype("string").fillna("(Perdido)")
    return plotted


def histogram(
    df: pd.DataFrame,
    *,
    x: str,
    color: str | None,
    color_sequence: list[str] | None,
    title: str,
    x_label: str,
    y_label: str,
    bins: int,
    width: int,
    height: int,
    percent: bool,
) -> Figure:
    columns = [x] + ([color] if color else [])
    plotted = _clean_for_plot(df, columns)
    plotted[x] = _coerce_numeric(plotted[x])
    plotted = plotted.dropna(subset=[x])
    fig = px.histogram(
        plotted,
        x=x,
        color=color,
        color_discrete_sequence=color_sequence,
        nbins=bins,
        histnorm="percent" if percent else None,
        title=title,
        width=width,
        height=height,
    )
    fig.update_layout(xaxis_title=x_label, yaxis_title=y_label, bargap=0.05)
    return fig


def bar_chart(
    df: pd.DataFrame,
    *,
    x: str,
    color: str | None,
    facet: str | None,
    color_sequence: list[str] | None,
    title: str,
    x_label: str,
    y_label: str,
    percent: bool,
    percent_denominator: str,
    orientation: str,
    barmode: str,
    show_labels: bool,
    label_decimals: int,
    width: int,
    height: int,
) -> Figure:
    columns = [x] + ([color] if color else []) + ([facet] if facet else [])
    plotted = _clean_for_plot(df, columns)

    group_columns = [x] + ([color] if color else []) + ([facet] if facet else [])
    counts = plotted.groupby(group_columns, dropna=False).size().reset_index(name="frecuencia")
    denominator_columns = {
        "total": [],
        "x": [x],
        "color": [color] if color else [],
        "facet": [facet] if facet else [],
    }.get(percent_denominator, [])
    if denominator_columns:
        denominator = counts.groupby(denominator_columns, dropna=False)["frecuencia"].transform("sum")
    else:
        denominator = counts["frecuencia"].sum()
    counts["porcentaje"] = counts["frecuencia"] / denominator * 100
    value_col = "porcentaje" if percent else "frecuencia"
    label_col = f"{value_col}_etiqueta"
    suffix = "%" if percent else ""
    counts[label_col] = counts[value_col].map(lambda value: f"{value:.{label_decimals}f}{suffix}")

    if orientation == "h":
        fig = px.bar(
            counts,
            y=x,
            x=value_col,
            color=color,
            facet_col=facet,
            color_discrete_sequence=color_sequence,
            orientation="h",
            title=title,
            width=width,
            height=height,
            barmode=barmode,
            text=label_col if show_labels else None,
        )
        fig.update_layout(xaxis_title=y_label, yaxis_title=x_label)
        fig.update_yaxes(showgrid=False)
    else:
        fig = px.bar(
            counts,
            x=x,
            y=value_col,
            color=color,
            facet_col=facet,
            color_discrete_sequence=color_sequence,
            title=title,
            width=width,
            height=height,
            barmode=barmode,
            text=label_col if show_labels else None,
        )
        fig.update_layout(xaxis_title=x_label, yaxis_title=y_label)
        fig.update_xaxes(showgrid=False)
    if show_labels:
        fig.update_traces(
            textposition="inside" if barmode == "stack" else "outside",
            texttemplate="%{text}",
            cliponaxis=False,
        )
    fig.for_each_annotation(lambda annotation: annotation.update(text=annotation.text.replace(f"{facet}=", "")) if facet else None)
    return fig


def scatter_plot(
    df: pd.DataFrame,
    *,
    x: str,
    y: str,
    color: str | None,
    color_sequence: list[str] | None,
    title: str,
    x_label: str,
    y_label: str,
    width: int,
    height: int,
) -> Figure:
    columns = [x, y] + ([color] if color else [])
    plotted = _clean_for_plot(df, columns)
    plotted[x] = _coerce_numeric(plotted[x])
    plotted[y] = _coerce_numeric(plotted[y])
    plotted = plotted.dropna(subset=[x, y])
    fig = px.scatter(
        plotted,
        x=x,
        y=y,
        color=color,
        color_discrete_sequence=color_sequence,
        title=title,
        width=width,
        height=height,
        opacity=0.75,
    )
    fig.update_layout(xaxis_title=x_label, yaxis_title=y_label)
    return fig


def to_png_bytes(fig: Figure) -> bytes | None:
    try:
        _configure_kaleido_browser()
        width = fig.layout.width or 900
        height = fig.layout.height or 520
        return fig.to_image(
            format="png",
            width=int(width),
            height=int(height),
            scale=2,
            validate=True,
        )
    except Exception:
        return None

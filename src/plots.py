from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path
from shutil import which

import pandas as pd
import plotly.express as px
from plotly.graph_objects import Figure

from src.descriptive_stats import _coerce_numeric


def _find_browser_executable() -> str | None:
    browser_path = os.environ.get("BROWSER_PATH")
    if browser_path and Path(browser_path).exists():
        return browser_path

    which_candidates = (
        "chromium",
        "chromium-browser",
        "google-chrome",
        "google-chrome-stable",
        "chrome",
        "msedge",
    )
    for candidate in which_candidates:
        resolved = which(candidate)
        if resolved:
            return resolved

    browser_candidates = (
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    )
    for candidate in browser_candidates:
        if Path(candidate).exists():
            return candidate
    return None


def _configure_kaleido_browser() -> None:
    if os.environ.get("BROWSER_PATH"):
        return
    browser_path = _find_browser_executable()
    if browser_path:
        os.environ["BROWSER_PATH"] = browser_path


def _render_png_with_browser(fig: Figure) -> bytes | None:
    browser_path = _find_browser_executable()
    if not browser_path:
        return None

    width = int(fig.layout.width or 900)
    height = int(fig.layout.height or 520)
    paper_bg = getattr(fig.layout, "paper_bgcolor", None) or "#FFFFFF"

    figure_html = fig.to_html(
        full_html=False,
        include_plotlyjs=True,
        config={"displayModeBar": False, "staticPlot": True, "responsive": False},
    )

    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Geologica:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    html, body {{
      margin: 0;
      padding: 0;
      width: {width}px;
      height: {height}px;
      overflow: hidden;
      background: {paper_bg};
    }}
    #chart-root {{
      width: {width}px;
      height: {height}px;
    }}
    .js-plotly-plot, .plotly-graph-div {{
      width: {width}px !important;
      height: {height}px !important;
    }}
  </style>
</head>
<body>
  <div id="chart-root">
    {figure_html}
  </div>
</body>
</html>
"""

    with tempfile.TemporaryDirectory() as tmpdir:
        html_path = Path(tmpdir) / "plot.html"
        png_path = Path(tmpdir) / "plot.png"
        html_path.write_text(html, encoding="utf-8")
        command = [
            browser_path,
            "--headless=new",
            "--disable-gpu",
            "--hide-scrollbars",
            "--force-device-scale-factor=2",
            "--virtual-time-budget=4000",
            f"--window-size={width},{height}",
            f"--screenshot={png_path}",
            html_path.resolve().as_uri(),
        ]
        try:
            subprocess.run(command, check=True, capture_output=True, timeout=20)
        except Exception:
            return None
        if not png_path.exists():
            return None
        return png_path.read_bytes()


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
    browser_png = _render_png_with_browser(fig)
    if browser_png is not None:
        return browser_png
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

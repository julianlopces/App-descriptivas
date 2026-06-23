from __future__ import annotations

import os
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path
from shutil import which
import socket

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.graph_objects import Figure
from plotly.subplots import make_subplots

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
    body {{
      visibility: hidden;
    }}
    body[data-ready="1"] {{
      visibility: visible;
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
  <div id="chart-root">{figure_html}</div>
  <script>
    const waitFrames = (count) => new Promise((resolve) => {{
      const step = () => {{
        if (count <= 0) {{
          resolve();
          return;
        }}
        count -= 1;
        requestAnimationFrame(step);
      }};
      requestAnimationFrame(step);
    }});

    const ensureGeologica = async () => {{
      if (!document.fonts) return;
      try {{
        await document.fonts.load('400 16px Geologica');
        await document.fonts.load('600 16px Geologica');
        await document.fonts.ready;
      }} catch (error) {{
        console.warn('Font preload failed', error);
      }}
    }};

    const reveal = async () => {{
      await ensureGeologica();
      await waitFrames(10);
      if (window.Plotly && Plotly.Plots && Plotly.Plots.resize) {{
        document.querySelectorAll('.js-plotly-plot').forEach((node) => Plotly.Plots.resize(node));
      }}
      await waitFrames(8);
      document.body.dataset.ready = '1';
      document.title = 'ready';
    }};

    window.addEventListener('load', () => {{
      reveal();
    }});
  </script>
</body>
</html>
"""

    with tempfile.TemporaryDirectory() as tmpdir:
        html_path = Path(tmpdir) / "plot.html"
        html_path.write_text(html, encoding="utf-8")

        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            debug_port = sock.getsockname()[1]

        command = [
            browser_path,
            "--headless=new",
            "--disable-gpu",
            "--hide-scrollbars",
            "--force-device-scale-factor=2",
            f"--remote-debugging-port={debug_port}",
            f"--user-data-dir={Path(tmpdir) / 'chrome-profile'}",
            f"--window-size={width},{height}",
            html_path.resolve().as_uri(),
        ]
        process = subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            return _capture_with_devtools(debug_port, html_path.resolve().as_uri())
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


def _capture_with_devtools(debug_port: int, page_url: str) -> bytes | None:
    try:
        import asyncio
        import base64
        import json
        import websockets
    except Exception:
        return None

    def fetch_ws_url() -> str | None:
        endpoint = f"http://127.0.0.1:{debug_port}/json/list"
        deadline = time.time() + 10
        while time.time() < deadline:
            try:
                with urllib.request.urlopen(endpoint, timeout=1) as response:
                    targets = json.loads(response.read().decode("utf-8"))
                for target in targets:
                    if target.get("type") == "page" and target.get("url") == page_url:
                        return target.get("webSocketDebuggerUrl")
                if targets:
                    return targets[0].get("webSocketDebuggerUrl")
            except Exception:
                time.sleep(0.2)
        return None

    async def run_capture(ws_url: str) -> bytes | None:
        async with websockets.connect(ws_url, max_size=None) as websocket:
            message_id = 0

            async def send(method: str, params: dict | None = None) -> dict | None:
                nonlocal message_id
                message_id += 1
                await websocket.send(json.dumps({"id": message_id, "method": method, "params": params or {}}))
                while True:
                    raw = await websocket.recv()
                    payload = json.loads(raw)
                    if payload.get("id") == message_id:
                        return payload

            await send("Page.enable")
            await send("Runtime.enable")

            deadline = time.time() + 12
            while time.time() < deadline:
                response = await send(
                    "Runtime.evaluate",
                    {
                        "expression": "document.title",
                        "returnByValue": True,
                    },
                )
                title = (
                    response.get("result", {})
                    .get("result", {})
                    .get("value", "")
                    if response
                    else ""
                )
                if title == "ready":
                    break
                await asyncio.sleep(0.25)
            else:
                return None

            screenshot = await send(
                "Page.captureScreenshot",
                {
                    "format": "png",
                    "fromSurface": True,
                    "captureBeyondViewport": True,
                },
            )
            data = screenshot.get("result", {}).get("data") if screenshot else None
            if not data:
                return None
            return base64.b64decode(data)

    ws_url = fetch_ws_url()
    if not ws_url:
        return None
    return asyncio.run(run_capture(ws_url))


def _clean_for_plot(df: pd.DataFrame, columns: list[str], *, exclude_missing: bool = True) -> pd.DataFrame:
    plotted = df[columns].copy()
    if exclude_missing:
        plotted = plotted.dropna(subset=columns)
    for column in columns:
        if plotted[column].dtype == "object":
            plotted[column] = plotted[column].astype("string").fillna("(Perdido)")
    return plotted


def _format_label_value(value: float, decimals: int, suffix: str = "") -> str:
    formatted = f"{value:.{decimals}f}"
    if decimals > 0:
        formatted = formatted.rstrip("0").rstrip(".")
    return f"{formatted}{suffix}"


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
    exclude_missing: bool = True,
) -> Figure:
    columns = [x] + ([color] if color else [])
    plotted = _clean_for_plot(df, columns, exclude_missing=exclude_missing)
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
    exclude_missing: bool = True,
) -> Figure:
    columns = [x] + ([color] if color else []) + ([facet] if facet else [])
    plotted = _clean_for_plot(df, columns, exclude_missing=exclude_missing)

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
    counts[label_col] = counts[value_col].map(lambda value: _format_label_value(value, label_decimals, suffix))

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


def pie_chart(
    df: pd.DataFrame,
    *,
    names: str,
    facet: str | None,
    color_sequence: list[str] | None,
    title: str,
    hole: float,
    label_decimals: int,
    width: int,
    height: int,
    exclude_missing: bool = True,
) -> Figure:
    columns = [names] + ([facet] if facet else [])
    plotted = _clean_for_plot(df, columns, exclude_missing=exclude_missing)

    palette = color_sequence or px.colors.qualitative.Plotly
    categories = list(plotted[names].dropna().unique())
    color_map = {category: palette[index % len(palette)] for index, category in enumerate(categories)}
    texttemplate = f"%{{percent:.{label_decimals}%}}"
    hovertemplate = "%{label}<br>%{percent:.2%}<extra></extra>"

    if not facet:
        counts = plotted.groupby(names, dropna=False).size().reset_index(name="frecuencia")
        labels = counts[names].astype(str).tolist()
        fig = go.Figure(
            data=[
                go.Pie(
                    labels=labels,
                    values=counts["frecuencia"],
                    hole=hole,
                    sort=False,
                    textinfo="percent",
                    texttemplate=texttemplate,
                    hovertemplate=hovertemplate,
                    marker={"colors": [color_map.get(label, palette[0]) for label in labels]},
                )
            ]
        )
        fig.update_layout(title=title, width=width, height=height)
        return fig

    facet_values = list(plotted[facet].dropna().unique())
    fig = make_subplots(
        rows=1,
        cols=len(facet_values),
        specs=[[{"type": "domain"} for _ in facet_values]],
        subplot_titles=[str(value) for value in facet_values],
    )
    for column_index, facet_value in enumerate(facet_values, start=1):
        subset = plotted[plotted[facet] == facet_value]
        counts = subset.groupby(names, dropna=False).size().reset_index(name="frecuencia")
        labels = counts[names].astype(str).tolist()
        fig.add_trace(
            go.Pie(
                labels=labels,
                values=counts["frecuencia"],
                hole=hole,
                sort=False,
                textinfo="percent",
                texttemplate=texttemplate,
                hovertemplate=hovertemplate,
                marker={"colors": [color_map.get(label, palette[0]) for label in labels]},
                showlegend=column_index == 1,
            ),
            row=1,
            col=column_index,
        )
    fig.update_layout(title=title, width=width, height=height)
    return fig


def scatter_plot(
    df: pd.DataFrame,
    *,
    x: str,
    y: str,
    color: str | None,
    color_sequence: list[str] | None,
    show_trendline: bool,
    trendline_method: str,
    trendline_scope: str,
    trendline_color: str,
    title: str,
    x_label: str,
    y_label: str,
    width: int,
    height: int,
    exclude_missing: bool = True,
) -> Figure:
    columns = [x, y] + ([color] if color else [])
    plotted = _clean_for_plot(df, columns, exclude_missing=exclude_missing)
    plotted[x] = _coerce_numeric(plotted[x])
    plotted[y] = _coerce_numeric(plotted[y])
    plotted = plotted.dropna(subset=[x, y])
    fig = px.scatter(
        plotted,
        x=x,
        y=y,
        color=color,
        color_discrete_sequence=color_sequence,
        trendline=trendline_method.lower() if show_trendline else None,
        trendline_color_override=(trendline_color if show_trendline and trendline_scope == "overall" else None),
        trendline_scope=trendline_scope if show_trendline else "trace",
        title=title,
        width=width,
        height=height,
        opacity=0.75,
    )
    if show_trendline and trendline_scope == "overall":
        fig.update_traces(
            selector=lambda trace: getattr(trace, "mode", "") == "lines",
            line={"color": trendline_color, "width": 2.5},
            opacity=1,
        )
    elif show_trendline and trendline_scope == "trace":
        marker_colors_by_group: dict[str, str] = {}
        for trace in fig.data:
            if getattr(trace, "mode", "") == "markers":
                group = str(getattr(trace, "legendgroup", "") or getattr(trace, "name", ""))
                marker_color = getattr(getattr(trace, "marker", None), "color", None)
                if isinstance(marker_color, str):
                    marker_colors_by_group[group] = marker_color

        for trace in fig.data:
            if getattr(trace, "mode", "") == "lines":
                group = str(getattr(trace, "legendgroup", "") or getattr(trace, "name", ""))
                line_color = marker_colors_by_group.get(group)
                if line_color:
                    trace.update(line={"color": line_color, "width": 2.5}, opacity=1)
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


# ---------------------------------------------------------------------------
# Render de respaldo con matplotlib (sin navegador ni Kaleido)
# ---------------------------------------------------------------------------
# Se usa para incrustar graficas en el Word cuando la exportacion PNG de Plotly
# falla (por ejemplo, cuando no hay navegador headless disponible). matplotlib
# funciona de forma headless en cualquier sistema operativo.

# Paleta y estilo institucional (Paleta Equi), iguales a los del modulo de Graficos.
_FALLBACK_COLORS = ["#020F50", "#1955A6", "#7CCCBF", "#F7966B", "#F4B21B", "#788EC7", "#B6C4E5", "#F4D2A4"]
_EQUI_STYLE = {
    "paper_bg": "#FFFFFF",
    "plot_bg": "#FFFFFF",
    "text_color": "#020F50",
    "grid_color": "#B6C4E5",
    "show_grid": True,
}


def _fmt_num(value: float, decimals: int) -> str:
    rounded = round(float(value), decimals)
    if float(rounded).is_integer():
        return str(int(rounded))
    return f"{rounded:.{decimals}f}".rstrip("0").rstrip(".")


def _style_ai_axes(fig, ax, style: dict, effective_type: str) -> None:
    """Aplica el estilo institucional (Paleta Equi) a los ejes de matplotlib."""
    paper_bg = style.get("paper_bg", "#FFFFFF")
    plot_bg = style.get("plot_bg", "#FFFFFF")
    text_color = style.get("text_color", "#020F50")
    grid_color = style.get("grid_color", "#B6C4E5")
    show_grid = bool(style.get("show_grid", True))

    fig.patch.set_facecolor(paper_bg)
    ax.set_facecolor(plot_bg)

    if effective_type == "pie":
        return

    ax.tick_params(colors=text_color, labelsize=9)
    for label in list(ax.get_xticklabels()) + list(ax.get_yticklabels()):
        label.set_color(text_color)
    ax.xaxis.label.set_color(text_color)
    ax.yaxis.label.set_color(text_color)
    ax.xaxis.label.set_fontsize(11)
    ax.yaxis.label.set_fontsize(11)

    for spine_name, spine in ax.spines.items():
        if spine_name in ("top", "right"):
            spine.set_visible(False)
        else:
            spine.set_color(grid_color)

    ax.set_axisbelow(True)
    if show_grid:
        if effective_type == "scatter":
            ax.grid(True, color=grid_color, linewidth=0.6, alpha=0.7)
        elif effective_type == "bar_h":
            ax.grid(True, axis="x", color=grid_color, linewidth=0.6, alpha=0.7)
            ax.grid(False, axis="y")
        else:  # barras verticales, histograma
            ax.grid(True, axis="y", color=grid_color, linewidth=0.6, alpha=0.7)
            ax.grid(False, axis="x")
    else:
        ax.grid(False)

    legend = ax.get_legend()
    if legend is not None:
        legend.get_frame().set_facecolor(paper_bg)
        legend.get_frame().set_edgecolor(grid_color)
        for text in legend.get_texts():
            text.set_color(text_color)
        if legend.get_title() is not None:
            legend.get_title().set_color(text_color)


def ai_chart_to_png(
    df: pd.DataFrame,
    spec: dict,
    *,
    palette: list[str] | None = None,
    style: dict | None = None,
    width_px: int = 900,
    height_px: int = 520,
) -> bytes | None:
    """Renderiza una grafica del informe de IA a PNG usando matplotlib.

    Es un respaldo robusto e independiente del sistema operativo, con el mismo
    estilo institucional (Paleta Equi) que el modulo de Graficos. Soporta los
    tipos bar, histogram, pie y scatter. Ignora 'facet' (agrega sobre el) para
    mantener la robustez. Devuelve bytes PNG o None si falla.
    """
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        return None

    from io import BytesIO

    plt.rcParams["font.family"] = ["Geologica", "DejaVu Sans", "Arial", "sans-serif"]
    colors = palette or _FALLBACK_COLORS
    chart_style = dict(_EQUI_STYLE)
    if style:
        chart_style.update({key: style[key] for key in chart_style if key in style})
    text_color = chart_style["text_color"]
    chart_type = str(spec.get("chart_type") or "")
    orient = str(spec.get("orientation") or "v")
    x = spec.get("x")
    y = spec.get("y")
    color = spec.get("color")
    title = str(spec.get("title") or "")
    x_label = str(spec.get("x_label") or (x or ""))
    y_label = str(spec.get("y_label") or "")
    legend_title = str(spec.get("legend_title") or (color or ""))

    fig = None
    try:
        fig, ax = plt.subplots(
            figsize=(width_px / 110.0, height_px / 110.0),
            dpi=110,
            facecolor=chart_style["paper_bg"],
        )

        if chart_type == "bar":
            percent = bool(spec.get("percent", True))
            orientation = str(spec.get("orientation") or "v")
            stacked = str(spec.get("barmode")) == "stack"
            decimals = int(spec.get("label_decimals", 2))
            show_labels = bool(spec.get("show_labels", True))
            value_label = y_label or ("Porcentaje" if percent else "Frecuencia")

            cols = [x] + ([color] if color else [])
            data = df[cols].dropna().copy()
            for c in cols:
                data[c] = data[c].astype(str)
            total = max(len(data), 1)

            if color:
                grouped = data.groupby([x, color]).size().reset_index(name="f")
                grouped["v"] = grouped["f"] / total * 100 if percent else grouped["f"]
                pivot = grouped.pivot(index=x, columns=color, values="v").fillna(0)
                cats = [str(i) for i in pivot.index]
                series = list(pivot.columns)
                positions = np.arange(len(cats))
                if stacked:
                    base = np.zeros(len(cats))
                    for i, s in enumerate(series):
                        vals = pivot[s].to_numpy()
                        if orientation == "h":
                            ax.barh(positions, vals, left=base, label=str(s), color=colors[i % len(colors)])
                        else:
                            ax.bar(positions, vals, bottom=base, label=str(s), color=colors[i % len(colors)])
                        base += vals
                else:
                    n = max(len(series), 1)
                    bar_w = 0.8 / n
                    for i, s in enumerate(series):
                        vals = pivot[s].to_numpy()
                        offset = (i - (n - 1) / 2) * bar_w
                        if orientation == "h":
                            ax.barh(positions + offset, vals, height=bar_w, label=str(s), color=colors[i % len(colors)])
                        else:
                            ax.bar(positions + offset, vals, width=bar_w, label=str(s), color=colors[i % len(colors)])
                if orientation == "h":
                    ax.set_yticks(positions)
                    ax.set_yticklabels(cats)
                else:
                    ax.set_xticks(positions)
                    ax.set_xticklabels(cats, rotation=30, ha="right")
                ax.legend(title=legend_title, fontsize=8)
            else:
                grouped = data.groupby(x).size().reset_index(name="f")
                grouped["v"] = grouped["f"] / total * 100 if percent else grouped["f"]
                cats = [str(i) for i in grouped[x].tolist()]
                vals = grouped["v"].to_numpy()
                positions = np.arange(len(cats))
                suffix = "%" if percent else ""
                if orientation == "h":
                    ax.barh(positions, vals, color=colors[0])
                    ax.set_yticks(positions)
                    ax.set_yticklabels(cats)
                    if show_labels:
                        for p, v in zip(positions, vals):
                            ax.text(v, p, " " + _fmt_num(v, decimals) + suffix, va="center", fontsize=8)
                else:
                    ax.bar(positions, vals, color=colors[0])
                    ax.set_xticks(positions)
                    ax.set_xticklabels(cats, rotation=30, ha="right")
                    if show_labels:
                        for p, v in zip(positions, vals):
                            ax.text(p, v, _fmt_num(v, decimals) + suffix, ha="center", va="bottom", fontsize=8)

            if orientation == "h":
                ax.set_xlabel(value_label)
                ax.set_ylabel(x_label)
            else:
                ax.set_xlabel(x_label)
                ax.set_ylabel(value_label)

        elif chart_type == "histogram":
            bins = int(spec.get("bins", 30) or 30)
            if color and color in df.columns:
                groups = df[[x, color]].copy()
                groups[x] = _coerce_numeric(groups[x])
                groups = groups.dropna(subset=[x, color])
                cats = [str(c) for c in groups[color].astype(str).unique()]
                data_list = [groups[groups[color].astype(str) == c][x].to_numpy() for c in cats]
                ax.hist(data_list, bins=bins, stacked=True, label=cats,
                        color=[colors[i % len(colors)] for i in range(len(cats))])
                ax.legend(title=legend_title, fontsize=8)
            else:
                values = _coerce_numeric(df[x]).dropna().to_numpy()
                ax.hist(values, bins=bins, color=colors[0])
            ax.set_xlabel(x_label)
            ax.set_ylabel(y_label or "Frecuencia")

        elif chart_type == "pie":
            hole = float(spec.get("hole", 0.52) or 0)
            decimals = int(spec.get("label_decimals", 1))
            data = df[x].dropna().astype(str)
            counts = data.value_counts(sort=False)
            wedge_kw = {"width": 1 - hole} if hole and hole > 0 else {}
            ax.pie(
                counts.to_numpy(),
                labels=[str(i) for i in counts.index],
                autopct=lambda p: _fmt_num(p, decimals) + "%",
                colors=[colors[i % len(colors)] for i in range(len(counts))],
                wedgeprops=wedge_kw,
                textprops={"fontsize": 8},
            )
            ax.axis("equal")

        elif chart_type == "scatter":
            sub = pd.DataFrame({
                "x": _coerce_numeric(df[x]),
                "y": _coerce_numeric(df[y]),
            })
            if color and color in df.columns:
                sub["g"] = df[color].astype(str)
                sub = sub.dropna(subset=["x", "y"])
                for i, (group, gdata) in enumerate(sub.groupby("g")):
                    ax.scatter(gdata["x"], gdata["y"], s=18, alpha=0.7, label=str(group), color=colors[i % len(colors)])
                ax.legend(title=legend_title, fontsize=8)
            else:
                sub = sub.dropna(subset=["x", "y"])
                ax.scatter(sub["x"], sub["y"], s=18, alpha=0.7, color=colors[0])
            if bool(spec.get("show_trendline", False)) and len(sub) >= 2:
                slope, intercept = np.polyfit(sub["x"].to_numpy(), sub["y"].to_numpy(), 1)
                line_x = np.linspace(sub["x"].min(), sub["x"].max(), 100)
                ax.plot(line_x, slope * line_x + intercept, color="#F7966B", linewidth=2)
            ax.set_xlabel(x_label)
            ax.set_ylabel(y_label or str(y or ""))

        else:
            plt.close(fig)
            return None

        effective_type = "bar_h" if (chart_type == "bar" and orient == "h") else chart_type
        _style_ai_axes(fig, ax, chart_style, effective_type)
        if title:
            ax.set_title(title, fontsize=13, fontweight="bold", color=text_color, loc="center", pad=12)
        fig.tight_layout()
        buffer = BytesIO()
        fig.savefig(buffer, format="png", bbox_inches="tight", facecolor=fig.get_facecolor())
        plt.close(fig)
        buffer.seek(0)
        return buffer.getvalue()
    except Exception:
        try:
            if fig is not None:
                plt.close(fig)
        except Exception:
            pass
        return None

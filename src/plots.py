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
    show_trendline: bool,
    trendline_method: str,
    trendline_scope: str,
    trendline_color: str,
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
                    trace.update(line={"color": line_color, "width": 2.5})
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

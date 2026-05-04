from __future__ import annotations

from html import escape

import pandas as pd
import streamlit as st

from src.data_loader import get_excel_sheets, load_uploaded_file, normalize_columns
from src.descriptive_stats import (
    categorical_summary,
    continuous_summary,
    contingency_table,
    detect_variable_types,
)
from src.palettes import (
    get_available_palettes,
    get_default_style_for_palette,
    get_palette_colors,
)
from src.plots import bar_chart, histogram, scatter_plot, to_png_bytes
from src.utils import dataframe_to_csv_bytes, dataframe_to_excel_bytes, tables_to_excel_bytes


st.set_page_config(
    page_title="QuanTi Stats",
    layout="wide",
    initial_sidebar_state="expanded",
)


FONT_FAMILIES = {
    "Geologica": "Geologica, Arial, sans-serif",
    "Arial": "Arial, Helvetica, sans-serif",
    "Inter": "Inter, Arial, sans-serif",
    "Verdana": "Verdana, Arial, sans-serif",
    "Helvetica": "Helvetica, Arial, sans-serif",
    "Georgia": "Georgia, serif",
    "Courier New": "\"Courier New\", Courier, monospace",
    "Times New Roman": "\"Times New Roman\", Times, serif",
}


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Geologica:wght@400;500;600;700&display=swap');

        :root {
            --bg: #20201e;
            --panel: #2a2a27;
            --panel-soft: #30302c;
            --stroke: #484842;
            --text: #f3f0e8;
            --muted: #bbb6aa;
            --accent: #c9c2ff;
            --accent-2: #a8ead8;
            --accent-3: #7468e8;
        }

        .stApp {
            background: var(--bg);
            color: var(--text);
        }

        header[data-testid="stHeader"] {
            background: #ffffff;
            border-bottom: 1px solid rgba(0, 0, 0, 0.08);
        }

        [data-testid="stSidebar"] {
            background: #252522;
            border-right: 1px solid var(--stroke);
        }

        [data-testid="stSidebar"] * {
            color: var(--text);
        }

        [data-testid="stSidebar"] input,
        [data-testid="stSidebar"] textarea,
        [data-testid="stSidebar"] select,
        [data-testid="stSidebar"] [data-baseweb="select"] *,
        [data-testid="stSidebar"] [data-baseweb="popover"] *,
        [data-testid="stSidebar"] [data-baseweb="tag"] *,
        [data-testid="stSidebar"] [data-testid="stFileUploaderFileName"],
        [data-testid="stSidebar"] [data-testid="stFileUploaderFileSize"],
        [data-testid="stSidebar"] [data-testid="stFileUploaderFile"] *,
        [data-testid="stSidebar"] [data-testid="stUploadedFile"] *,
        [data-testid="stSidebar"] [data-testid="stFileUploader"] li *,
        [data-testid="stSidebar"] [data-testid="stFileUploader"] small {
            color: #24232b !important;
        }

        [data-testid="stSidebar"] [data-baseweb="select"] > div,
        [data-testid="stSidebar"] [data-baseweb="base-input"] > div,
        [data-testid="stSidebar"] [data-testid="stFileUploader"] section,
        [data-testid="stSidebar"] [data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"] {
            background: #f7f5ef !important;
            border-color: #f7f5ef !important;
        }

        [data-testid="stSidebar"] [data-testid="stFileUploaderFile"],
        [data-testid="stSidebar"] [data-testid="stUploadedFile"],
        [data-testid="stSidebar"] [data-testid="stFileUploader"] li {
            background: #ebeef2 !important;
            border-color: #ebeef2 !important;
        }

        [data-testid="stSidebar"] [data-testid="stFileUploader"] button {
            background: #ffffff !important;
            border: 1px solid #c9c6bd !important;
            color: #24232b !important;
            opacity: 1 !important;
        }

        [data-testid="stSidebar"] [data-testid="stFileUploader"] button *,
        [data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] button *,
        [data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] p,
        [data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] small,
        [data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] span,
        [data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] div {
            color: #24232b !important;
            opacity: 1 !important;
        }

        [data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] > div {
            color: #24232b !important;
        }

        [data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] svg,
        [data-testid="stSidebar"] [data-testid="stFileUploader"] button svg {
            color: #24232b !important;
            fill: currentColor !important;
            opacity: 1 !important;
            stroke: currentColor !important;
        }

        [data-testid="stSidebar"] input::placeholder,
        [data-testid="stSidebar"] textarea::placeholder,
        [data-testid="stSidebar"] [data-baseweb="select"] input::placeholder {
            color: #6f6a60 !important;
            opacity: 1 !important;
        }

        [data-testid="stSidebar"] svg {
            color: inherit;
            fill: currentColor;
        }

        [data-testid="stSidebar"] [data-baseweb="select"] svg,
        [data-testid="stSidebar"] [data-testid="stFileUploader"] svg {
            color: #3a3840 !important;
            fill: currentColor;
        }

        [data-testid="stSidebar"] [role="option"] *,
        [data-testid="stSidebar"] [data-baseweb="menu"] * {
            color: #24232b !important;
        }

        [data-testid="stSidebar"] [data-testid="stExpander"],
        [data-testid="stSidebar"] details,
        [data-testid="stSidebar"] details summary {
            background: #f7f5ef !important;
            border-color: #f7f5ef !important;
            color: #24232b !important;
        }

        [data-testid="stSidebar"] details summary *,
        [data-testid="stSidebar"] [data-testid="stExpander"] summary *,
        [data-testid="stSidebar"] [data-testid="stExpander"] [data-testid="stMarkdownContainer"] *,
        [data-testid="stSidebar"] [data-testid="stExpander"] p,
        [data-testid="stSidebar"] [data-testid="stExpander"] span {
            color: #24232b !important;
            opacity: 1 !important;
        }

        [data-testid="stSidebar"] details summary svg,
        [data-testid="stSidebar"] [data-testid="stExpander"] summary svg {
            color: #24232b !important;
            fill: currentColor !important;
            stroke: currentColor !important;
            opacity: 1 !important;
        }

        h1, h2, h3 {
            color: var(--text);
            letter-spacing: 0;
        }

        [data-testid="stMain"] [data-testid="stWidgetLabel"],
        [data-testid="stMain"] [data-testid="stWidgetLabel"] *,
        [data-testid="stMain"] [data-testid="stRadio"] label,
        [data-testid="stMain"] [data-testid="stRadio"] label *,
        [data-testid="stMain"] [data-testid="stCheckbox"] label,
        [data-testid="stMain"] [data-testid="stCheckbox"] label *,
        [data-testid="stMain"] [data-testid="stToggle"] label,
        [data-testid="stMain"] [data-testid="stToggle"] label *,
        [data-testid="stMain"] [data-testid="stSlider"] label,
        [data-testid="stMain"] [data-testid="stSlider"] label * {
            color: #f3f0e8 !important;
            opacity: 1 !important;
        }

        [data-testid="stMain"] [data-baseweb="radio"] div,
        [data-testid="stMain"] [data-baseweb="radio"] span,
        [data-testid="stMain"] [data-baseweb="checkbox"] div,
        [data-testid="stMain"] [data-baseweb="checkbox"] span {
            color: #f3f0e8 !important;
            opacity: 1 !important;
        }

        [data-testid="stMain"] input,
        [data-testid="stMain"] textarea,
        [data-testid="stMain"] [data-baseweb="select"] *,
        [data-testid="stMain"] [data-baseweb="base-input"] * {
            color: #24232b !important;
        }

        [data-testid="stMain"] [data-baseweb="select"] > div,
        [data-testid="stMain"] [data-baseweb="base-input"] > div {
            background: #f3f4f7 !important;
            border-color: #f3f4f7 !important;
        }

        [data-testid="stMain"] [data-baseweb="select"] svg {
            color: #24232b !important;
            fill: currentColor !important;
        }

        [data-testid="stMain"] [data-testid="stSegmentedControl"] button {
            background: #2f2f2b !important;
            border-color: #5a5a52 !important;
            color: #f3f0e8 !important;
        }

        [data-testid="stMain"] [data-testid="stSegmentedControl"] button *,
        [data-testid="stMain"] [data-testid="stSegmentedControl"] label,
        [data-testid="stMain"] [data-testid="stSegmentedControl"] label * {
            color: #f3f0e8 !important;
            opacity: 1 !important;
        }

        [data-testid="stMain"] [data-testid="stExpander"],
        [data-testid="stMain"] details,
        [data-testid="stMain"] details summary {
            background: #f7f5ef !important;
            border-color: #f7f5ef !important;
            color: #24232b !important;
        }

        [data-testid="stMain"] details summary *,
        [data-testid="stMain"] [data-testid="stExpander"] summary *,
        [data-testid="stMain"] [data-testid="stExpander"] [data-testid="stMarkdownContainer"] *,
        [data-testid="stMain"] [data-testid="stExpander"] p,
        [data-testid="stMain"] [data-testid="stExpander"] span {
            color: #24232b !important;
            opacity: 1 !important;
        }

        [data-testid="stMain"] details summary svg,
        [data-testid="stMain"] [data-testid="stExpander"] summary svg {
            color: #24232b !important;
            fill: currentColor !important;
            stroke: currentColor !important;
            opacity: 1 !important;
        }

        .block-container {
            padding-top: 4.75rem;
            max-width: 1420px;
        }

        .chart-sticky-scope + div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(2) {
            align-self: flex-start;
            position: sticky;
            top: 5.25rem;
            z-index: 5;
        }

        div[data-testid="stTabs"] button {
            background: #2d2d29;
            border: 1px solid var(--stroke);
            border-radius: 8px;
            color: var(--muted);
            min-height: 44px;
            padding: 0.35rem 1rem;
        }

        div[data-testid="stTabs"] button[aria-selected="true"] {
            background: #ebe8ff;
            color: #24232b;
            border-color: #ebe8ff;
            font-weight: 700;
        }

        .app-title {
            display: flex;
            align-items: center;
            gap: 0.72rem;
            margin-bottom: 1rem;
        }

        .logo-mark {
            width: 34px;
            height: 34px;
            border-radius: 8px;
            background: linear-gradient(145deg, #5b50d9, #2d276f);
            display: grid;
            place-items: center;
            font-weight: 800;
            color: white;
        }

        .title-copy strong {
            display: block;
            font-size: 1.05rem;
            line-height: 1.1;
        }

        .title-copy span {
            color: var(--muted);
            font-size: 0.78rem;
        }

        .side-heading {
            color: var(--muted);
            font-size: 0.76rem;
            font-weight: 800;
            letter-spacing: 0.04em;
            margin: 1.25rem 0 0.45rem;
            text-transform: uppercase;
        }

        .dataset-card,
        .metric-card,
        .panel,
        .note-card {
            background: var(--panel);
            border: 1px solid var(--stroke);
            border-radius: 8px;
            box-shadow: 0 10px 28px rgba(0, 0, 0, 0.14);
        }

        .dataset-card {
            border-style: dashed;
            padding: 1rem;
            text-align: center;
            margin-bottom: 0.8rem;
        }

        .dataset-card .file-name {
            font-weight: 800;
            color: var(--text);
            overflow-wrap: anywhere;
        }

        .dataset-card .file-meta {
            color: var(--muted);
            font-size: 0.86rem;
        }

        .metric-grid {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 0.85rem;
            margin: 0.35rem 0 1rem;
        }

        .metric-card {
            min-height: 112px;
            padding: 1rem;
        }

        .metric-card small {
            color: var(--muted);
            display: block;
            font-weight: 800;
            margin-bottom: 0.35rem;
        }

        .metric-card strong {
            color: var(--text);
            display: block;
            font-size: 2rem;
            line-height: 1;
        }

        .metric-card span {
            color: var(--muted);
            display: block;
            font-size: 0.85rem;
            margin-top: 0.35rem;
        }

        .panel {
            padding: 1rem;
            margin-top: 0.75rem;
        }

        .panel-title {
            color: var(--text);
            font-size: 1rem;
            font-weight: 850;
            margin-bottom: 0.15rem;
        }

        .panel-subtitle {
            color: var(--muted);
            font-size: 0.82rem;
            margin-bottom: 0.75rem;
        }

        .note-card {
            background: #f0edff;
            border-color: #f0edff;
            color: #27243d;
            font-size: 0.88rem;
            margin-top: 0.8rem;
            padding: 0.85rem 1rem;
        }

        .chip {
            align-items: center;
            background: #e8e4ff;
            border-radius: 7px;
            color: #2b2940;
            display: flex;
            font-size: 0.84rem;
            justify-content: space-between;
            margin: 0.34rem 0;
            min-height: 32px;
            padding: 0.34rem 0.55rem;
        }

        .chip.teal {
            background: #d5f4eb;
            color: #173d35;
        }

        .chip.dark {
            background: #30302c;
            border: 1px solid var(--stroke);
            color: var(--muted);
        }

        .chip code {
            background: rgba(255, 255, 255, 0.55);
            border-radius: 5px;
            color: inherit;
            font-size: 0.68rem;
            padding: 0.08rem 0.35rem;
        }

        .stDataFrame {
            border: 1px solid var(--stroke);
            border-radius: 8px;
            overflow: hidden;
        }

        div[data-testid="stDownloadButton"] button,
        div[data-testid="stButton"] button {
            border-radius: 8px;
            font-weight: 750;
        }

        @media (max-width: 1100px) {
            .metric-grid {
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }
        }

        @media (max-width: 760px) {
            .metric-grid {
                grid-template-columns: 1fr;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def init_state() -> None:
    defaults = {
        "df": None,
        "file_name": None,
        "continuous_vars": [],
        "categorical_vars": [],
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def chip_list(title: str, items: list[str], kind: str, badge: str) -> None:
    st.markdown(f'<div class="side-heading">{escape(title)}</div>', unsafe_allow_html=True)
    if not items:
        st.caption("Sin variables seleccionadas.")
        return
    html = "\n".join(
        f'<div class="chip {kind}"><span>{escape(item)}</span><code>{escape(badge)}</code></div>'
        for item in items[:12]
    )
    if len(items) > 12:
        html += f'<div class="chip dark"><span>+ {len(items) - 12} variables mas</span><code>...</code></div>'
    st.markdown(html, unsafe_allow_html=True)


def dataset_card(df: pd.DataFrame | None) -> None:
    if df is None:
        body = """
        <div class="dataset-card">
            <div class="file-name">Sin dataset cargado</div>
            <div class="file-meta">CSV, XLSX o XLS</div>
        </div>
        """
    else:
        file_name = escape(st.session_state.file_name or "Dataset cargado")
        body = f"""
        <div class="dataset-card">
            <div class="file-name">{file_name}</div>
            <div class="file-meta">n = {df.shape[0]:,} casos - {df.shape[1]:,} variables</div>
        </div>
        """
    st.markdown(body, unsafe_allow_html=True)


def load_controls() -> None:
    st.markdown(
        """
        <div class="app-title">
            <div class="logo-mark">QS</div>
            <div class="title-copy">
                <strong>QuanTi Stats</strong>
                <span>v1.0 - campo rapido</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.divider()
    st.markdown('<div class="side-heading">Dataset</div>', unsafe_allow_html=True)
    dataset_card(st.session_state.df)

    uploaded = st.file_uploader(
        "Cargar archivo",
        type=["csv", "xlsx", "xls"],
        accept_multiple_files=False,
        label_visibility="collapsed",
    )

    if not uploaded:
        return

    suffix = uploaded.name.rsplit(".", 1)[-1].lower()
    sheet_name = None
    csv_encoding = "utf-8"
    csv_separator = "Auto"

    with st.expander("Opciones de lectura", expanded=False):
        if suffix in {"xlsx", "xls"}:
            try:
                sheets = get_excel_sheets(uploaded)
            except Exception as exc:
                st.error(f"No fue posible leer las hojas del archivo Excel: {exc}")
                return
            sheet_name = st.selectbox("Hoja de Excel", sheets)
        else:
            csv_encoding = st.selectbox(
                "Codificacion",
                ["utf-8", "utf-8-sig", "latin-1", "cp1252"],
                index=0,
            )
            csv_separator = st.selectbox(
                "Separador",
                ["Auto", ",", ";", "\\t", "|"],
                index=0,
            )

    if st.button("Cargar dataset", type="primary", use_container_width=True):
        try:
            loaded = load_uploaded_file(
                uploaded,
                sheet_name=sheet_name,
                csv_encoding=csv_encoding,
                csv_separator=csv_separator,
            )
            loaded = normalize_columns(loaded)
            if loaded.empty:
                st.error("El archivo no contiene filas de datos.")
                return
            st.session_state.df = loaded
            st.session_state.file_name = uploaded.name
            detected = detect_variable_types(loaded)
            st.session_state.continuous_vars = detected["continuous"]
            st.session_state.categorical_vars = detected["categorical"]
            st.rerun()
        except Exception as exc:
            st.error(f"No fue posible cargar el archivo: {exc}")


def variable_controls(df: pd.DataFrame) -> tuple[list[str], list[str]]:
    all_columns = list(df.columns)

    st.markdown('<div class="side-heading">Clasificacion</div>', unsafe_allow_html=True)
    with st.expander("Ajustar tipos", expanded=False):
        continuous = st.multiselect(
            "Continuas",
            all_columns,
            default=[c for c in st.session_state.continuous_vars if c in all_columns],
        )
        categorical_options = [c for c in all_columns if c not in continuous]
        categorical = st.multiselect(
            "Categoricas",
            categorical_options,
            default=[c for c in st.session_state.categorical_vars if c in categorical_options],
        )

    st.session_state.continuous_vars = continuous
    st.session_state.categorical_vars = categorical

    return continuous, categorical


def metric_html(label: str, value: str, detail: str) -> str:
    return f"""
    <div class="metric-card">
        <small>{escape(label)}</small>
        <strong>{escape(value)}</strong>
        <span>{escape(detail)}</span>
    </div>
    """


def overview_metrics(df: pd.DataFrame, continuous_vars: list[str], categorical_vars: list[str]) -> None:
    missing = int(df.isna().sum().sum())
    complete_rows = int(df.dropna().shape[0])
    html = f"""
    <div class="metric-grid">
        {metric_html("N total", f"{df.shape[0]:,}", "casos validos en la base")}
        {metric_html("Variables", f"{df.shape[1]:,}", f"{len(continuous_vars)} cont - {len(categorical_vars)} cat")}
        {metric_html("Perdidos", f"{missing:,}", "celdas sin dato")}
        {metric_html("Filas completas", f"{complete_rows:,}", "sin valores perdidos")}
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def apply_trace_palette(fig, palette: list[str]) -> None:
    if not palette:
        return
    for index, trace in enumerate(fig.data):
        color = palette[index % len(palette)]
        trace_type = getattr(trace, "type", "")
        if trace_type in {"scatter", "scattergl"}:
            trace.update(marker={"color": color, "line": {"color": color}})
        elif trace_type in {"bar", "histogram"}:
            trace.update(marker={"color": color, "line": {"color": color, "width": 0.5}})
        elif hasattr(trace, "marker"):
            trace.update(marker={"color": color})


def sync_palette_style_defaults(selected_palette: str) -> None:
    new_defaults = get_default_style_for_palette(selected_palette)
    applied_palette = st.session_state.get("chart_palette_applied")

    for field, value in new_defaults.items():
        state_key = f"chart_{field}"
        if state_key not in st.session_state:
            st.session_state[state_key] = value

    if not applied_palette or applied_palette == selected_palette:
        st.session_state["chart_palette_applied"] = selected_palette
        return

    old_defaults = get_default_style_for_palette(applied_palette)
    for field, old_value in old_defaults.items():
        state_key = f"chart_{field}"
        if st.session_state.get(state_key) == old_value:
            st.session_state[state_key] = new_defaults[field]

    st.session_state["chart_palette_applied"] = selected_palette


def chart_style_controls() -> dict[str, object]:
    with st.expander("Estilo del grafico", expanded=True):
        available_palettes = get_available_palettes()
        palette_options = list(available_palettes.keys())
        if "chart_palette_name" not in st.session_state:
            st.session_state["chart_palette_name"] = palette_options[0]

        palette_name = st.selectbox(
            "Paleta de colores",
            palette_options,
            index=palette_options.index(st.session_state["chart_palette_name"]),
            key="chart_palette_name",
        )
        sync_palette_style_defaults(palette_name)
        col1, col2 = st.columns(2)
        with col1:
            paper_bg = st.color_picker("Fondo externo", key="chart_paper_bg")
            plot_bg = st.color_picker("Fondo del area", key="chart_plot_bg")
            text_color = st.color_picker("Color de letras", key="chart_text_color")
        with col2:
            grid_color = st.color_picker("Color de grilla", key="chart_grid_color")
            font_family = st.selectbox(
                "Fuente",
                list(FONT_FAMILIES.keys()),
            )
            font_size = st.slider("Tamano de fuente", 10, 28, 16)
        show_grid = st.toggle("Mostrar grilla", value=True)
    return {
        "palette_name": palette_name,
        "palette": get_palette_colors(palette_name),
        "legend_title": "",
        "show_title": True,
        "title_alignment": "Centro",
        "show_grid": show_grid,
        "paper_bg": paper_bg,
        "plot_bg": plot_bg,
        "text_color": text_color,
        "grid_color": grid_color,
        "font_family": font_family,
        "font_size": font_size,
    }


def style_figure(fig, style: dict[str, object]) -> None:
    palette = style["palette"]
    apply_trace_palette(fig, palette if isinstance(palette, list) else [])
    paper_bg = str(style["paper_bg"])
    plot_bg = str(style["plot_bg"])
    text_color = str(style["text_color"])
    grid_color = str(style["grid_color"])
    selected_font = str(style["font_family"])
    font_family = FONT_FAMILIES.get(selected_font, selected_font)
    font_size = int(style["font_size"])
    legend_title = str(style.get("legend_title", "")).strip()
    show_title = bool(style.get("show_title", True))
    show_grid = bool(style.get("show_grid", True))
    title_alignment = str(style.get("title_alignment", "Centro"))
    title_x = {"Izquierda": 0.0, "Centro": 0.5, "Derecha": 1.0}.get(title_alignment, 0.5)
    title_anchor = {"Izquierda": "left", "Centro": "center", "Derecha": "right"}.get(
        title_alignment,
        "center",
    )
    current_title = fig.layout.title.text if fig.layout.title and fig.layout.title.text else ""
    title_text = f"<b>{escape(current_title)}</b>" if show_title and current_title else ""
    fig.update_layout(
        template="plotly_dark",
        width=900,
        height=520,
        paper_bgcolor=paper_bg,
        plot_bgcolor=plot_bg,
        font={"color": text_color, "family": font_family, "size": font_size},
        title={
            "text": title_text,
            "x": title_x,
            "xanchor": title_anchor,
            "font": {"color": text_color, "family": font_family, "size": font_size + 4},
        },
        legend={
            "bgcolor": paper_bg,
            "bordercolor": paper_bg,
            "font": {"color": text_color, "family": font_family, "size": font_size},
            "title": {
                "font": {"color": text_color, "family": font_family, "size": font_size + 1}
            },
            "x": 1.02,
            "xanchor": "left",
            "y": 1.0,
            "yanchor": "top",
        },
        margin={"l": 48, "r": 170, "t": 56, "b": 48},
    )
    if legend_title:
        fig.update_layout(legend_title_text=legend_title)
    x_showgrid = False if not show_grid else (False if fig.layout.xaxis.showgrid is False else True)
    y_showgrid = False if not show_grid else (False if fig.layout.yaxis.showgrid is False else True)
    fig.update_xaxes(
        color=text_color,
        gridcolor=grid_color,
        linecolor=text_color,
        showgrid=x_showgrid,
        tickfont={"color": text_color, "family": font_family, "size": font_size},
        title_font={"color": text_color, "family": font_family, "size": font_size},
        zerolinecolor=grid_color,
    )
    fig.update_yaxes(
        color=text_color,
        gridcolor=grid_color,
        linecolor=text_color,
        showgrid=y_showgrid,
        tickfont={"color": text_color, "family": font_family, "size": font_size},
        title_font={"color": text_color, "family": font_family, "size": font_size},
        zerolinecolor=grid_color,
    )


def chart_title_controls(default_title: str, key_prefix: str) -> str:
    title = st.text_input("Titulo", default_title, key=f"{key_prefix}_title")
    show_title = st.toggle("Mostrar titulo", value=True, key=f"{key_prefix}_show_title")
    title_alignment = st.segmented_control(
        "Alineacion del titulo",
        ["Izquierda", "Centro", "Derecha"],
        default="Centro",
        key=f"{key_prefix}_title_alignment",
    )
    st.session_state[f"{key_prefix}_title_options"] = {
        "show_title": show_title,
        "title_alignment": title_alignment,
    }
    return title


def _parse_axis_limit(value: str) -> float | None:
    cleaned = value.strip().replace(",", ".")
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def axis_range_controls(
    x_label: str,
    y_label: str,
    *,
    key_prefix: str,
    x_numeric: bool,
    y_numeric: bool,
) -> dict[str, tuple[float | None, float | None] | None]:
    st.markdown("**Rango de ejes**")
    use_custom_ranges = st.toggle("Personalizar rango de ejes", value=False, key=f"{key_prefix}_use_axis_ranges")
    x_range: tuple[float | None, float | None] | None = None
    y_range: tuple[float | None, float | None] | None = None

    if use_custom_ranges:
        if x_numeric:
            st.caption(f"{x_label}: deja vacio un limite para mantenerlo automatico.")
            col_x_min, col_x_max = st.columns(2)
            with col_x_min:
                x_min_text = st.text_input("Min X", value="", key=f"{key_prefix}_x_min")
            with col_x_max:
                x_max_text = st.text_input("Max X", value="", key=f"{key_prefix}_x_max")
            x_range = (_parse_axis_limit(x_min_text), _parse_axis_limit(x_max_text))

        if y_numeric:
            st.caption(f"{y_label}: deja vacio un limite para mantenerlo automatico.")
            col_y_min, col_y_max = st.columns(2)
            with col_y_min:
                y_min_text = st.text_input("Min Y", value="", key=f"{key_prefix}_y_min")
            with col_y_max:
                y_max_text = st.text_input("Max Y", value="", key=f"{key_prefix}_y_max")
            y_range = (_parse_axis_limit(y_min_text), _parse_axis_limit(y_max_text))

    return {
        "x_range": x_range,
        "y_range": y_range,
    }


def apply_axis_ranges(fig, axis_ranges: dict[str, tuple[float | None, float | None] | None]) -> None:
    x_range = axis_ranges.get("x_range")
    y_range = axis_ranges.get("y_range")

    if x_range and any(limit is not None for limit in x_range):
        fig.update_xaxes(range=[x_range[0], x_range[1]])

    if y_range and any(limit is not None for limit in y_range):
        fig.update_yaxes(range=[y_range[0], y_range[1]])


def panel_start(title: str, subtitle: str = "") -> None:
    st.markdown(
        f"""
        <div class="panel">
            <div class="panel-title">{escape(title)}</div>
            <div class="panel-subtitle">{escape(subtitle)}</div>
        """,
        unsafe_allow_html=True,
    )


def panel_end() -> None:
    st.markdown("</div>", unsafe_allow_html=True)


def render_empty_state() -> None:
    st.markdown(
        """
        <div class="panel">
            <div class="panel-title">Carga una base para comenzar</div>
            <div class="panel-subtitle">
                Usa el panel izquierdo para subir un CSV, XLSX o XLS. Luego podras clasificar variables,
                clasificar variables y generar tablas o graficos desde los modulos horizontales.
            </div>
            <div class="note-card">
                El flujo queda organizado como un tablero: dataset y variables a la izquierda;
                analisis, tablas, graficos y exportacion a la derecha.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def continuous_tab(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    selected_columns = st.multiselect(
        "Variables continuas a mostrar",
        columns,
        default=columns,
        key="continuous_table_filter",
    )
    panel_start("Variables continuas", "Conteo, perdidos, tendencia central, dispersion y percentiles.")
    if not selected_columns:
        st.info("Selecciona al menos una variable continua para mostrar la tabla.")
        panel_end()
        return pd.DataFrame()

    table = continuous_summary(df, selected_columns)
    st.dataframe(table, use_container_width=True, height=430)
    if not table.empty:
        col_csv, col_xlsx = st.columns(2)
        with col_csv:
            st.download_button(
                "Descargar CSV",
                dataframe_to_csv_bytes(table),
                "descriptivas_continuas.csv",
                "text/csv",
                use_container_width=True,
            )
        with col_xlsx:
            st.download_button(
                "Descargar XLSX",
                dataframe_to_excel_bytes(table, "continuas"),
                "descriptivas_continuas.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
    panel_end()
    return table


def categorical_tab(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    selected_columns = st.multiselect(
        "Variables categoricas a mostrar",
        columns,
        default=columns,
        key="categorical_table_filter",
    )
    max_levels = st.slider("Maximo de categorias por variable", 5, 100, 30)
    panel_start("Variables categoricas", "Frecuencias absolutas, porcentajes y valores perdidos.")
    if not selected_columns:
        st.info("Selecciona al menos una variable categorica para mostrar la tabla.")
        panel_end()
        return pd.DataFrame()

    table = categorical_summary(df, selected_columns, max_levels=max_levels)
    st.dataframe(table, use_container_width=True, height=430)
    if not table.empty:
        col_csv, col_xlsx = st.columns(2)
        with col_csv:
            st.download_button(
                "Descargar CSV",
                dataframe_to_csv_bytes(table),
                "descriptivas_categoricas.csv",
                "text/csv",
                use_container_width=True,
            )
        with col_xlsx:
            st.download_button(
                "Descargar XLSX",
                dataframe_to_excel_bytes(table, "categoricas"),
                "descriptivas_categoricas.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
    panel_end()
    return table


def contingency_tab(df: pd.DataFrame, categorical_vars: list[str]) -> pd.DataFrame:
    if len(categorical_vars) < 2:
        st.info("Selecciona al menos dos variables categoricas.")
        return pd.DataFrame()

    controls, output = st.columns([0.34, 0.66], gap="large")
    with controls:
        st.markdown('<div class="side-heading">Configuracion</div>', unsafe_allow_html=True)
        row_var = st.selectbox("Filas", categorical_vars)
        col_var = st.selectbox("Columnas", [c for c in categorical_vars if c != row_var])
        mode = st.selectbox(
            "Mostrar",
            ["Frecuencia absoluta", "Porcentaje por fila", "Porcentaje por columna", "Porcentaje total"],
        )

    normalize_map = {
        "Frecuencia absoluta": None,
        "Porcentaje por fila": "index",
        "Porcentaje por columna": "columns",
        "Porcentaje total": "all",
    }
    table = contingency_table(df, row_var, col_var, normalize=normalize_map[mode])

    with output:
        panel_start(f"{row_var} x {col_var}", mode)
        st.dataframe(table, use_container_width=True, height=430)
        export_table = table.reset_index()
        col_csv, col_xlsx = st.columns(2)
        with col_csv:
            st.download_button(
                "Descargar CSV",
                dataframe_to_csv_bytes(export_table),
                "tabla_cruzada.csv",
                "text/csv",
                use_container_width=True,
            )
        with col_xlsx:
            st.download_button(
                "Descargar XLSX",
                dataframe_to_excel_bytes(export_table, "tabla_cruzada"),
                "tabla_cruzada.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
        panel_end()

    return table


def charts_tab(df: pd.DataFrame, continuous_vars: list[str], categorical_vars: list[str]) -> None:
    st.markdown('<div class="chart-sticky-scope"></div>', unsafe_allow_html=True)
    controls, output = st.columns([0.32, 0.68], gap="large")
    fig = None
    axis_ranges = {"x_range": None, "y_range": None}

    with controls:
        st.markdown('<div class="side-heading">Tipo de analisis</div>', unsafe_allow_html=True)
        chart_type = st.radio(
            "Tipo de grafico",
            ["Barras", "Histograma", "Dispersion"],
            horizontal=False,
            label_visibility="collapsed",
        )
        style_config = chart_style_controls()

        if chart_type == "Histograma":
            if not continuous_vars:
                st.info("No hay variables continuas seleccionadas.")
                return
            x = st.selectbox("Variable continua", continuous_vars)
            color = st.selectbox("Agrupacion/color", ["Ninguna"] + categorical_vars)
            bins = st.slider("Bins", 5, 100, 30)
            percent = st.toggle("Mostrar porcentajes", value=False)
            title = chart_title_controls(f"Histograma de {x}", "hist")
            style_config.update(st.session_state["hist_title_options"])
            x_label = st.text_input("Eje X", x)
            y_label = st.text_input("Eje Y", "Porcentaje" if percent else "Frecuencia")
            legend_title = st.text_input(
                "Titulo de la leyenda",
                "" if color == "Ninguna" else color,
                key="hist_legend_title",
            )
            style_config["legend_title"] = legend_title
            axis_ranges = axis_range_controls(
                x_label,
                y_label,
                key_prefix="hist",
                x_numeric=True,
                y_numeric=True,
            )
            fig = histogram(
                df,
                x=x,
                color=None if color == "Ninguna" else color,
                color_sequence=style_config["palette"],
                title=title,
                x_label=x_label,
                y_label=y_label,
                bins=bins,
                width=900,
                height=520,
                percent=percent,
            )

        elif chart_type == "Barras":
            if not categorical_vars:
                st.info("No hay variables categoricas seleccionadas.")
                return
            x = st.selectbox("Variable categorica", categorical_vars)
            color_options = [c for c in categorical_vars if c != x]
            color = st.selectbox("Variable de apilado/color", ["Ninguna"] + color_options)
            facet_options = [
                c
                for c in categorical_vars
                if c not in {x, None if color == "Ninguna" else color}
            ]
            facet = st.selectbox("Tercera variable / panel", ["Ninguna"] + facet_options)
            barmode = st.segmented_control(
                "Modo de barras",
                ["Apiladas", "Agrupadas"],
                default="Apiladas",
            )
            percent = st.toggle("Mostrar porcentajes", value=False)
            percent_denominator = "total"
            if percent:
                denominator_options = {"Total general": "total", f"Total por {x}": "x"}
                if color != "Ninguna":
                    denominator_options[f"Total por {color}"] = "color"
                if facet != "Ninguna":
                    denominator_options[f"Total por {facet}"] = "facet"
                denominator_label = st.selectbox(
                    "Calcular porcentaje sobre",
                    list(denominator_options.keys()),
                )
                percent_denominator = denominator_options[denominator_label]
            show_labels = st.toggle("Mostrar etiquetas en barras", value=True)
            label_decimals = 2
            if show_labels:
                label_decimals = st.number_input(
                    "Decimales de etiquetas",
                    min_value=0,
                    max_value=6,
                    value=2,
                    step=1,
                )
            orientation = st.segmented_control("Orientacion", ["Vertical", "Horizontal"], default="Vertical")
            title = chart_title_controls(f"Barras de {x}", "bar")
            style_config.update(st.session_state["bar_title_options"])
            x_label = st.text_input("Eje X", x)
            y_label = st.text_input("Eje Y", "Porcentaje" if percent else "Frecuencia")
            legend_title = st.text_input(
                "Titulo de la leyenda",
                "" if color == "Ninguna" else color,
                key="bar_legend_title",
            )
            style_config["legend_title"] = legend_title
            axis_ranges = axis_range_controls(
                x_label,
                y_label,
                key_prefix="bar",
                x_numeric=orientation == "Horizontal",
                y_numeric=orientation == "Vertical",
            )
            fig = bar_chart(
                df,
                x=x,
                color=None if color == "Ninguna" else color,
                facet=None if facet == "Ninguna" else facet,
                color_sequence=style_config["palette"],
                title=title,
                x_label=x_label,
                y_label=y_label,
                percent=percent,
                percent_denominator=percent_denominator,
                orientation="h" if orientation == "Horizontal" else "v",
                barmode="stack" if barmode == "Apiladas" else "group",
                show_labels=show_labels,
                label_decimals=int(label_decimals),
                width=900,
                height=520,
            )

        else:
            if len(continuous_vars) < 2:
                st.info("Selecciona al menos dos variables continuas.")
                return
            x = st.selectbox("Variable X", continuous_vars)
            y = st.selectbox("Variable Y", [c for c in continuous_vars if c != x])
            color = st.selectbox("Color", ["Ninguna"] + categorical_vars)
            title = chart_title_controls(f"{y} vs {x}", "scatter")
            style_config.update(st.session_state["scatter_title_options"])
            x_label = st.text_input("Eje X", x)
            y_label = st.text_input("Eje Y", y)
            legend_title = st.text_input(
                "Titulo de la leyenda",
                "" if color == "Ninguna" else color,
                key="scatter_legend_title",
            )
            style_config["legend_title"] = legend_title
            axis_ranges = axis_range_controls(
                x_label,
                y_label,
                key_prefix="scatter",
                x_numeric=True,
                y_numeric=True,
            )
            fig = scatter_plot(
                df,
                x=x,
                y=y,
                color=None if color == "Ninguna" else color,
                color_sequence=style_config["palette"],
                title=title,
                x_label=x_label,
                y_label=y_label,
                width=900,
                height=520,
            )

    if fig is None:
        return

    style_figure(fig, style_config)
    apply_axis_ranges(fig, axis_ranges)
    with output:
        panel_start("Vista del grafico", "Personalizable y listo para incluir en informes.")
        st.plotly_chart(fig, use_container_width=True)
        png = to_png_bytes(fig)
        if png:
            st.download_button("Descargar PNG", png, "grafico.png", "image/png")
        else:
            st.caption("La exportacion PNG requiere que kaleido funcione correctamente en el entorno.")
        st.markdown(
            """
            <div class="note-card">
                Tip: usa color o agrupacion para comparar segmentos. Para informes, exporta PNG o descarga
                la tabla base del modulo correspondiente.
            </div>
            """,
            unsafe_allow_html=True,
        )
        panel_end()


def export_tab(tables: dict[str, pd.DataFrame]) -> None:
    panel_start("Exportar resultados", "Descarga tablas descriptivas y salidas principales.")
    available = {name: table for name, table in tables.items() if not table.empty}
    if not available:
        st.info("Aun no hay tablas para exportar.")
    else:
        for name, table in available.items():
            st.markdown(f"**{name.replace('_', ' ').title()}**")
            col_csv, col_xlsx = st.columns(2)
            with col_csv:
                st.download_button(
                    f"{name} CSV",
                    dataframe_to_csv_bytes(table),
                    f"{name}.csv",
                    "text/csv",
                    use_container_width=True,
                    key=f"export_{name}_csv",
                )
            with col_xlsx:
                st.download_button(
                    f"{name} XLSX",
                    dataframe_to_excel_bytes(table, name),
                    f"{name}.xlsx",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    key=f"export_{name}_xlsx",
                )

        st.download_button(
            "Excel completo",
            tables_to_excel_bytes(available),
            "tablas_descriptivas.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
    panel_end()


def preview_tab(df: pd.DataFrame) -> None:
    panel_start("Vista previa del dataset", "Primeras filas y estructura general de la base.")
    st.dataframe(df.head(80), use_container_width=True, height=460)
    missing_by_column = (
        df.isna()
        .sum()
        .reset_index()
        .rename(columns={"index": "variable", 0: "valores_perdidos"})
        .sort_values("valores_perdidos", ascending=False)
    )
    with st.expander("Valores perdidos por variable"):
        st.dataframe(missing_by_column, use_container_width=True, height=300)
    panel_end()


def main() -> None:
    inject_styles()
    init_state()

    with st.sidebar:
        load_controls()
        df = st.session_state.df
        if df is not None:
            continuous_vars, categorical_vars = variable_controls(df)
        else:
            continuous_vars, categorical_vars = [], []

    st.markdown(
        """
        <div class="app-title">
            <div class="logo-mark">QS</div>
            <div class="title-copy">
                <strong>QuanTi Stats</strong>
                <span>Exploracion descriptiva modular</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    df = st.session_state.df
    if df is None:
        render_empty_state()
        return

    selected_continuous, selected_categorical = continuous_vars, categorical_vars
    overview_metrics(df, selected_continuous, selected_categorical)

    tables = {
        "continuas": continuous_summary(df, selected_continuous),
        "categoricas": categorical_summary(df, selected_categorical, max_levels=30),
    }

    tab_graphs, tab_cross, tab_cont, tab_cat, tab_export, tab_preview = st.tabs(
        ["Graficos", "Tablas cruzadas", "Continuas", "Categoricas", "Exportar", "Vista previa"]
    )

    with tab_graphs:
        charts_tab(df, selected_continuous, selected_categorical)
    with tab_cross:
        cross = contingency_tab(df, selected_categorical)
        if not cross.empty:
            tables["tabla_cruzada"] = cross.reset_index()
    with tab_cont:
        tables["continuas"] = continuous_tab(df, selected_continuous)
    with tab_cat:
        tables["categoricas"] = categorical_tab(df, selected_categorical)
    with tab_export:
        export_tab(tables)
    with tab_preview:
        preview_tab(df)


if __name__ == "__main__":
    main()

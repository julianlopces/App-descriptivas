from __future__ import annotations

import base64
from html import escape
from pathlib import Path

import pandas as pd
import streamlit as st

from src.crosstabs import (
    TABLE_TYPE_LABELS,
    build_crosstab_excel,
    compute_crosstab,
    format_crosstab_for_display,
)
from src.data_loader import get_excel_sheets, load_uploaded_file, normalize_columns
from src.descriptive_stats import (
    categorical_summary,
    continuous_summary,
    detect_variable_types,
)
from src.palettes import (
    get_available_palettes,
    get_default_style_for_palette,
    get_palette_colors,
)
from src.plots import bar_chart, histogram, scatter_plot, to_png_bytes
from src.theme import INSTITUTIONAL_COLORS, get_institutional_css
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

PROJECT_ROOT = Path(__file__).resolve().parent
LOGO_PATH = PROJECT_ROOT / "media" / "Equilibrium-Logo-Completo-Azul.png"


def get_logo_data_uri() -> str:
    if not LOGO_PATH.exists():
        return ""
    encoded = base64.b64encode(LOGO_PATH.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def inject_styles() -> None:
    st.markdown(
        get_institutional_css(),
        unsafe_allow_html=True,
    )


def render_app_header(subtitle: str) -> None:
    logo_data_uri = get_logo_data_uri()
    logo_html = (
        f'<img src="{logo_data_uri}" alt="Equilibrium logo">' if logo_data_uri else "QS"
    )
    st.markdown(
        f"""
        <div class="app-title">
            <div class="logo-mark">{logo_html}</div>
            <div class="title-copy">
                <strong>QuanTi Stats</strong>
                <span>{escape(subtitle)}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def format_table_value(value: object, max_decimals: int) -> object:
    if isinstance(value, bool) or value is None:
        return value
    if pd.isna(value):
        return ""
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        rounded = round(value, max_decimals)
        if float(rounded).is_integer():
            return str(int(rounded))
        formatted = f"{rounded:.{max_decimals}f}"
        return formatted.rstrip("0").rstrip(".")
    return value


def style_table(table: pd.DataFrame, max_decimals: int) -> pd.io.formats.style.Styler:
    colors = INSTITUTIONAL_COLORS
    formatter = {
        column: (lambda value, decimals=max_decimals: format_table_value(value, decimals))
        for column in table.columns
    }
    return table.style.format(formatter).set_table_styles(
        [
            {
                "selector": "thead th",
                "props": [
                    ("background-color", colors["primary"]),
                    ("color", colors["white"]),
                    ("border", f"1px solid {colors['night_blue']}"),
                    ("font-weight", "700"),
                ],
            },
            {
                "selector": "tbody td",
                "props": [
                    ("background-color", colors["white"]),
                    ("color", colors["text_strong"]),
                    ("border", f"1px solid {colors['night_blue']}"),
                ],
            },
            {
                "selector": "tbody th",
                "props": [
                    ("background-color", colors["panel_muted"]),
                    ("color", colors["text_strong"]),
                    ("border", f"1px solid {colors['night_blue']}"),
                    ("font-weight", "600"),
                ],
            },
            {
                "selector": "table",
                "props": [
                    ("border-collapse", "collapse"),
                    ("border", f"1px solid {colors['night_blue']}"),
                ],
            },
        ]
    )


def render_styled_table(table: pd.DataFrame, *, height: int, key_prefix: str) -> None:
    max_decimals = st.number_input(
        "Decimales máximos visibles",
        min_value=0,
        max_value=6,
        value=2,
        step=1,
        key=f"{key_prefix}_table_decimals",
    )
    st.dataframe(style_table(table, int(max_decimals)), use_container_width=True, height=height)


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
    render_app_header("v1.0 - campo rápido")
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
                "Codificación",
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

    st.markdown('<div class="side-heading">Clasificación</div>', unsafe_allow_html=True)
    with st.expander("Ajustar tipos", expanded=False):
        continuous = st.multiselect(
            "Continuas",
            all_columns,
            default=[c for c in st.session_state.continuous_vars if c in all_columns],
        )
        categorical_options = [c for c in all_columns if c not in continuous]
        categorical = st.multiselect(
            "Categóricas",
            categorical_options,
            default=[c for c in st.session_state.categorical_vars if c in categorical_options],
        )

    st.session_state.continuous_vars = continuous
    st.session_state.categorical_vars = categorical

    return continuous, categorical


def metric_html(label: str, value: str, detail: str) -> str:
    colors = INSTITUTIONAL_COLORS
    return f"""
    <div
        class="metric-card"
        style="
            min-height: 112px;
            padding: 1rem;
            border-radius: 8px;
            border: 1px solid {colors["primary"]};
            background: linear-gradient(180deg, {colors["primary"]}, {colors["secondary_blue"]});
            box-shadow: 0 12px 24px rgba(2, 15, 80, 0.18);
            color: {colors["white"]};
        "
    >
        <small style="display:block; color:{colors['white']}; font-weight:800; margin-bottom:0.35rem; opacity:0.96;">{escape(label)}</small>
        <strong style="display:block; color:{colors['white']}; font-size:2rem; line-height:1; font-weight:800;">{escape(value)}</strong>
        <span style="display:block; color:{colors['white']}; font-size:0.85rem; margin-top:0.35rem; font-weight:700; opacity:0.92;">{escape(detail)}</span>
    </div>
    """


def overview_metrics(df: pd.DataFrame, continuous_vars: list[str], categorical_vars: list[str]) -> None:
    missing = int(df.isna().sum().sum())
    complete_rows = int(df.dropna().shape[0])
    html = f"""
    <div
        class="metric-grid"
        style="
            display:grid;
            grid-template-columns:repeat(4, minmax(0, 1fr));
            gap:0.85rem;
            margin:0.35rem 0 1rem;
            align-items:stretch;
        "
    >
        {metric_html("N total", f"{df.shape[0]:,}", "casos válidos en la base")}
        {metric_html("Variables", f"{df.shape[1]:,}", f"{len(continuous_vars)} cont. - {len(categorical_vars)} cat.")}
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
    with st.expander("Estilo del gráfico", expanded=True):
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
            font_size = st.slider("Tamaño de fuente", 10, 28, 16)
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
    trace_names = [
        str(getattr(trace, "name", "") or "")
        for trace in fig.data
        if getattr(trace, "showlegend", True)
    ]
    legend_source = [legend_title] if legend_title else []
    if getattr(fig.layout.legend.title, "text", None):
        legend_source.append(str(fig.layout.legend.title.text))
    legend_source.extend(trace_names)
    longest_legend_text = max((len(text.strip()) for text in legend_source if text), default=0)
    legend_margin = max(170, min(320, int(longest_legend_text * (font_size * 0.78)) + 42))
    chart_width = 900 + max(0, legend_margin - 170)
    fig.update_layout(
        template="plotly_dark",
        width=chart_width,
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
        margin={"l": 48, "r": legend_margin, "t": 56, "b": 48},
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
    title = st.text_input(
        "Título",
        default_title,
        key=f"{key_prefix}_title",
        help="Texto principal que aparecerá en la parte superior del gráfico.",
    )
    show_title = st.toggle(
        "Mostrar título",
        value=True,
        key=f"{key_prefix}_show_title",
        help="Activa o desactiva la visibilidad del título en el gráfico.",
    )
    title_alignment = st.segmented_control(
        "Alineación del título",
        ["Izquierda", "Centro", "Derecha"],
        default="Centro",
        key=f"{key_prefix}_title_alignment",
        help="Define en qué parte superior del gráfico se ubicará el título.",
    )
    st.session_state[f"{key_prefix}_title_options"] = {
        "show_title": show_title,
        "title_alignment": title_alignment,
    }
    return title


def axis_range_controls(
    x_label: str,
    y_label: str,
    *,
    key_prefix: str,
    x_numeric: bool,
    y_numeric: bool,
) -> dict[str, tuple[float | None, float | None] | None]:
    st.markdown("**Rango de ejes**")
    use_custom_ranges = st.toggle(
        "Personalizar rango de ejes",
        value=False,
        key=f"{key_prefix}_use_axis_ranges",
        help="Permite fijar el mínimo y/o el máximo de los ejes. Si completas solo uno, el otro se calcula automáticamente.",
    )
    x_range: tuple[float | None, float | None] | None = None
    y_range: tuple[float | None, float | None] | None = None

    if use_custom_ranges:
        if x_numeric:
            st.caption(f"{x_label}: activa mínimo y/o máximo para fijar el rango.")
            col_x_min, col_x_max = st.columns(2)
            with col_x_min:
                use_x_min = st.checkbox("Usar Min X", key=f"{key_prefix}_use_x_min")
                x_min_value = st.number_input(
                    "Min X",
                    value=float(st.session_state.get(f"{key_prefix}_x_min_value", 0.0)),
                    step=1.0,
                    format="%.4f",
                    key=f"{key_prefix}_x_min_value",
                    disabled=not use_x_min,
                )
            with col_x_max:
                use_x_max = st.checkbox("Usar Max X", key=f"{key_prefix}_use_x_max")
                x_max_value = st.number_input(
                    "Max X",
                    value=float(st.session_state.get(f"{key_prefix}_x_max_value", 0.0)),
                    step=1.0,
                    format="%.4f",
                    key=f"{key_prefix}_x_max_value",
                    disabled=not use_x_max,
                )
            x_range = (
                float(x_min_value) if use_x_min else None,
                float(x_max_value) if use_x_max else None,
            )

        if y_numeric:
            st.caption(f"{y_label}: activa mínimo y/o máximo para fijar el rango.")
            col_y_min, col_y_max = st.columns(2)
            with col_y_min:
                use_y_min = st.checkbox("Usar Min Y", key=f"{key_prefix}_use_y_min")
                y_min_value = st.number_input(
                    "Min Y",
                    value=float(st.session_state.get(f"{key_prefix}_y_min_value", 0.0)),
                    step=1.0,
                    format="%.4f",
                    key=f"{key_prefix}_y_min_value",
                    disabled=not use_y_min,
                )
            with col_y_max:
                use_y_max = st.checkbox("Usar Max Y", key=f"{key_prefix}_use_y_max")
                y_max_value = st.number_input(
                    "Max Y",
                    value=float(st.session_state.get(f"{key_prefix}_y_max_value", 0.0)),
                    step=1.0,
                    format="%.4f",
                    key=f"{key_prefix}_y_max_value",
                    disabled=not use_y_max,
                )
            y_range = (
                float(y_min_value) if use_y_min else None,
                float(y_max_value) if use_y_max else None,
            )

    return {
        "x_range": x_range,
        "y_range": y_range,
    }


def apply_axis_ranges(fig, axis_ranges: dict[str, tuple[float | None, float | None] | None]) -> None:
    def complete_range(axis_name: str, requested_range: tuple[float | None, float | None]) -> tuple[float | None, float | None]:
        start, end = requested_range
        if start is not None and end is not None:
            return start, end
        try:
            full_fig = fig.full_figure_for_development(warn=False)
            full_axis = getattr(full_fig.layout, f"{axis_name}axis", None)
            computed_range = getattr(full_axis, "range", None) if full_axis else None
            if computed_range and len(computed_range) == 2:
                start = computed_range[0] if start is None else start
                end = computed_range[1] if end is None else end
        except Exception:
            pass
        return start, end

    x_range = axis_ranges.get("x_range")
    y_range = axis_ranges.get("y_range")

    if x_range and any(limit is not None for limit in x_range):
        x_min, x_max = x_range
        x_min, x_max = complete_range("x", (x_min, x_max))
        if x_min is not None or x_max is not None:
            fig.update_xaxes(range=[x_min, x_max], autorange=False)

    if y_range and any(limit is not None for limit in y_range):
        y_min, y_max = y_range
        y_min, y_max = complete_range("y", (y_min, y_max))
        if y_min is not None or y_max is not None:
            fig.update_yaxes(range=[y_min, y_max], autorange=False)


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
                Usa el panel izquierdo para subir un CSV, XLSX o XLS. Luego podrás clasificar variables
                y generar tablas o gráficos desde los módulos horizontales.
            </div>
            <div class="note-card">
                El flujo queda organizado como un tablero: dataset y variables a la izquierda;
                análisis, tablas, gráficos y exportación a la derecha.
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
    panel_start("Variables continuas", "Conteo, perdidos, tendencia central, dispersión y percentiles.")
    if not selected_columns:
        st.info("Selecciona al menos una variable continua para mostrar la tabla.")
        panel_end()
        return pd.DataFrame()

    table = continuous_summary(df, selected_columns)
    render_styled_table(table, height=430, key_prefix="continuous")
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
        "Variables categóricas a mostrar",
        columns,
        default=columns,
        key="categorical_table_filter",
    )
    max_levels = st.slider("Máximo de categorías por variable", 5, 100, 30)
    panel_start("Variables categóricas", "Frecuencias absolutas, porcentajes y valores perdidos.")
    if not selected_columns:
        st.info("Selecciona al menos una variable categórica para mostrar la tabla.")
        panel_end()
        return pd.DataFrame()

    table = categorical_summary(df, selected_columns, max_levels=max_levels)
    render_styled_table(table, height=430, key_prefix="categorical")
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
        st.info("Selecciona al menos dos variables categóricas.")
        return pd.DataFrame()

    controls, output = st.columns([0.34, 0.66], gap="large")
    with controls:
        st.markdown('<div class="side-heading">Configuración</div>', unsafe_allow_html=True)
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
        render_styled_table(table, height=430, key_prefix="cross")
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


def mass_crosstab_tab(df: pd.DataFrame, categorical_vars: list[str]) -> pd.DataFrame:
    panel_start(
        "Tablas cruzadas por desagregaciones",
        "Las variables principales se muestran como columnas y las variables de desagregación como filas. "
        "Por defecto se excluyen los valores perdidos.",
    )
    if len(categorical_vars) < 2:
        st.info("Selecciona al menos dos variables categóricas para generar tablas cruzadas.")
        panel_end()
        return pd.DataFrame()

    controls, output = st.columns([0.38, 0.62], gap="large")
    with controls:
        st.markdown('<div class="side-heading">Configuración</div>', unsafe_allow_html=True)
        main_vars = st.multiselect(
            "Variables principales",
            categorical_vars,
            key="cross_main_vars",
            help="Estas variables se usarán como columnas en todas las tablas del Excel.",
        )
        disaggregation_vars = st.multiselect(
            "Variables de desagregación sociodemográfica",
            categorical_vars,
            key="cross_disagg_vars",
            help="Estas variables se usarán como filas en todas las tablas del Excel.",
        )
        table_type_label = st.selectbox(
            "Tipo de tabla",
            list(TABLE_TYPE_LABELS.values()),
            key="cross_table_type",
            help="Este formato se aplicará a todas las tablas cruzadas generadas en el archivo.",
        )
        st.caption(
            "El Excel tendrá una hoja por variable principal y dentro de cada hoja aparecerán todas "
            "las desagregaciones seleccionadas."
        )

    reverse_type_labels = {label: key for key, label in TABLE_TYPE_LABELS.items()}
    table_type = reverse_type_labels[table_type_label]
    shared_vars = sorted(set(main_vars).intersection(disaggregation_vars))
    valid_pairs = [
        (main_var, disagg_var)
        for main_var in main_vars
        for disagg_var in disaggregation_vars
        if main_var != disagg_var
    ]

    with output:
        if not main_vars:
            st.warning("Selecciona al menos una variable principal.")
            panel_end()
            return pd.DataFrame()
        if not disaggregation_vars:
            st.warning("Selecciona al menos una variable de desagregación.")
            panel_end()
            return pd.DataFrame()
        if shared_vars:
            st.warning(
                "Las variables repetidas en ambos grupos se omitirán cuando coincidan: "
                + ", ".join(shared_vars)
            )
        if not valid_pairs:
            st.warning("No hay combinaciones válidas para generar tablas cruzadas.")
            panel_end()
            return pd.DataFrame()

        preview_main = ""
        preview_disagg = ""
        preview_table = pd.DataFrame()
        for candidate_main, candidate_disagg in valid_pairs:
            candidate_table = compute_crosstab(df, candidate_disagg, candidate_main, table_type)
            if not candidate_table.empty:
                preview_main = candidate_main
                preview_disagg = candidate_disagg
                preview_table = candidate_table
                break

        if preview_table.empty:
            st.info("No hay datos válidos para las combinaciones seleccionadas.")
            panel_end()
            return pd.DataFrame()

        panel_start(
            f"Vista previa: {preview_main} x {preview_disagg}",
            f"{table_type_label}. Se muestra la primera combinación; el Excel incluirá todas.",
        )
        render_styled_table(
            format_crosstab_for_display(preview_table, table_type),
            height=430,
            key_prefix="cross_preview",
        )
        excel_buffer = build_crosstab_excel(df, main_vars, disaggregation_vars, table_type)
        st.download_button(
            "Descargar Excel",
            excel_buffer.getvalue(),
            "tablas_cruzadas_desagregadas.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            key="cross_download_excel",
            help="Descarga un Excel con una hoja por variable principal y una tabla por cada desagregación.",
        )
        panel_end()

    panel_end()
    return preview_table.reset_index()


def charts_tab(df: pd.DataFrame, continuous_vars: list[str], categorical_vars: list[str]) -> None:
    controls, output = st.columns([0.32, 0.68], gap="large")
    fig = None
    axis_ranges = {"x_range": None, "y_range": None}

    with controls:
        control_panel = st.container(height=760, border=False)
    with output:
        preview_panel = st.container(height=760, border=False)

    with control_panel:
        st.markdown('<div class="side-heading">Tipo de análisis</div>', unsafe_allow_html=True)
        chart_type = st.radio(
            "Tipo de gráfico",
            ["Barras", "Histograma", "Gráfico de dispersión"],
            horizontal=False,
            label_visibility="collapsed",
        )
        style_config = chart_style_controls()

        if chart_type == "Histograma":
            if not continuous_vars:
                st.info("No hay variables continuas seleccionadas.")
                return
            x = st.selectbox("Variable continua", continuous_vars, help="Variable numérica que se distribuirá en el histograma.")
            color = st.selectbox("Agrupación/color", ["Ninguna"] + categorical_vars)
            bins = st.slider("Bins", 5, 100, 30, help="Cantidad de intervalos usados para agrupar los datos.")
            title = chart_title_controls(f"Histograma de {x}", "hist")
            style_config.update(st.session_state["hist_title_options"])
            x_label = st.text_input("Eje X", x, help="Texto visible del eje horizontal.")
            y_label = st.text_input("Eje Y", "Frecuencia", help="Texto visible del eje vertical.")
            legend_title = st.text_input(
                "Título de la leyenda",
                "" if color == "Ninguna" else color,
                key="hist_legend_title",
                help="Nombre que aparecerá sobre la leyenda del gráfico.",
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
                percent=False,
            )

        elif chart_type == "Barras":
            if not categorical_vars:
                st.info("No hay variables categóricas seleccionadas.")
                return
            x = st.selectbox("Variable de conteo/principal", categorical_vars, help="Variable cuyas categorías se verán en el eje principal.")
            color_options = [c for c in categorical_vars if c != x]
            color = st.selectbox("Variable para desagregar/color", ["Ninguna"] + color_options, help="Variable opcional para separar las barras por color.")
            facet_options = [
                c
                for c in categorical_vars
                if c not in {x, None if color == "Ninguna" else color}
            ]
            facet = st.selectbox("Tercera variable / panel", ["Ninguna"] + facet_options, help="Crea paneles adicionales para una tercera variable categórica.")
            barmode = st.segmented_control(
                "Modo de barras",
                ["Apiladas", "Agrupadas"],
                default="Apiladas",
                help="Define si las barras se muestran apiladas o una al lado de la otra.",
            )
            percent = st.toggle("Mostrar porcentajes", value=False, help="Si se activa, el eje Y se expresa en porcentaje en lugar de frecuencia.")
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
                    help="Elige sobre qué total se calcularán los porcentajes mostrados en las barras.",
                )
                percent_denominator = denominator_options[denominator_label]
            show_labels = st.toggle("Mostrar etiquetas en barras", value=True, help="Muestra el valor o porcentaje directamente sobre cada barra.")
            label_decimals = 2
            if show_labels:
                label_decimals = st.number_input(
                    "Decimales de etiquetas",
                    min_value=0,
                    max_value=6,
                    value=2,
                    step=1,
                    help="Cantidad máxima de decimales mostrados en las etiquetas.",
                )
            orientation = st.segmented_control(
                "Orientación",
                ["Vertical", "Horizontal"],
                default="Vertical",
                help="Define si las barras se muestran de abajo hacia arriba o de izquierda a derecha.",
            )
            title = chart_title_controls(f"Barras de {x}", "bar")
            style_config.update(st.session_state["bar_title_options"])
            x_label = st.text_input("Eje X", x, help="Texto visible del eje horizontal.")
            y_label = st.text_input("Eje Y", "Porcentaje" if percent else "Frecuencia", help="Texto visible del eje vertical.")
            legend_title = st.text_input(
                "Título de la leyenda",
                "" if color == "Ninguna" else color,
                key="bar_legend_title",
                help="Nombre que aparecerá sobre la leyenda del gráfico.",
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
            x = st.selectbox("Variable X", continuous_vars, help="Variable numérica que se mostrará en el eje horizontal.")
            y = st.selectbox("Variable Y", [c for c in continuous_vars if c != x], help="Variable numérica que se mostrará en el eje vertical.")
            color = st.selectbox("Color", ["Ninguna"] + categorical_vars, help="Variable opcional para diferenciar puntos por grupo.")
            show_trendline = st.toggle(
                "Mostrar l?nea de ajuste",
                value=False,
                help="Agrega una l?nea de ajuste para resumir la relaci?n entre X e Y.",
            )
            trendline_method = "OLS"
            trendline_scope = "overall"
            trendline_color = "#F7966B"
            if show_trendline:
                trendline_method = st.selectbox(
                    "M?todo de ajuste",
                    ["OLS"],
                    index=0,
                    help="M?todo estad?stico usado para calcular la l?nea de ajuste.",
                )
                if color != "Ninguna":
                    trendline_scope_label = st.selectbox(
                        "C?lculo de la l?nea de ajuste",
                        ["General", "Por subgrupos"],
                        index=0,
                        help="Elige si la l?nea de ajuste se calcula para todos los puntos o por cada grupo de color.",
                    )
                    trendline_scope = "overall" if trendline_scope_label == "General" else "trace"
                if color == "Ninguna" or trendline_scope == "overall":
                    trendline_color = st.color_picker(
                        "Color de la l?nea de ajuste",
                        value="#F7966B",
                        help="Color aplicado a la l?nea de ajuste general.",
                    )
                else:
                    st.caption("Las l?neas de ajuste por subgrupos usar?n autom?ticamente el mismo color que sus puntos.")
            title = chart_title_controls(f"{y} vs {x}", "scatter")
            style_config.update(st.session_state["scatter_title_options"])
            x_label = st.text_input("Eje X", x, help="Texto visible del eje horizontal.")
            y_label = st.text_input("Eje Y", y, help="Texto visible del eje vertical.")
            legend_title = st.text_input(
                "Título de la leyenda",
                "" if color == "Ninguna" else color,
                key="scatter_legend_title",
                help="Nombre que aparecerá sobre la leyenda del gráfico.",
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
                show_trendline=show_trendline,
                trendline_method=trendline_method,
                trendline_scope=trendline_scope,
                trendline_color=trendline_color,
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
    with preview_panel:
        panel_start("Vista del gráfico", "Personalizable y listo para incluir en informes.")
        st.plotly_chart(fig, use_container_width=True)
        png = to_png_bytes(fig)
        if png:
            st.download_button("Descargar PNG", png, "grafico.png", "image/png")
        else:
            st.caption("La exportación PNG requiere que kaleido funcione correctamente en el entorno.")
        st.markdown(
            """
            <div class="note-card">
                Tip: usa color o agrupación para comparar segmentos. Para informes, exporta PNG o descarga
                la tabla base del módulo correspondiente.
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
    render_styled_table(df.head(80), height=460, key_prefix="preview")
    missing_by_column = (
        df.isna()
        .sum()
        .reset_index()
        .rename(columns={"index": "variable", 0: "valores_perdidos"})
        .sort_values("valores_perdidos", ascending=False)
    )
    with st.expander("Valores perdidos por variable"):
        render_styled_table(missing_by_column, height=300, key_prefix="missing")
    panel_end()


def instructions_tab() -> None:
    panel_start(
        "Instrucciones de uso",
        "Gu\u00eda r\u00e1pida de lo que puedes hacer en cada m\u00f3dulo de la app.",
    )
    st.markdown(
        """
        <div
            style="
                background:#F4D2A4;
                border:1px solid #F4B21B;
                border-radius:8px;
                color:#000031;
                font-size:0.88rem;
                margin-top:0.8rem;
                padding:0.85rem 1rem;
            "
        >
            Sugerencia de flujo: carga la base en el panel izquierdo, revisa la clasificaci&oacute;n de variables y
            luego entra al m&oacute;dulo que necesites para explorar, tabular o exportar resultados.
        </div>
        <div
            style="
                display:grid;
                grid-template-columns:repeat(auto-fit, minmax(220px, 1fr));
                gap:0.9rem;
                margin-top:0.9rem;
            "
        >
            <div style="background:linear-gradient(180deg, #FFFFFF 0%, #F7FAF2 100%); border:1px solid #B6C4E5; border-radius:8px; padding:0.95rem 1rem; box-shadow:0 10px 20px rgba(2, 15, 80, 0.05);">
                <h4>Carga y clasificaci&oacute;n</h4>
                <p>Desde el panel izquierdo subes la base y confirmas qu&eacute; variables son continuas o categ&oacute;ricas.</p>
                <ul>
                    <li>Carga archivos CSV, XLSX o XLS.</li>
                    <li>Elige hoja, codificaci&oacute;n o separador si hace falta.</li>
                    <li>Ajusta manualmente la clasificaci&oacute;n de variables.</li>
                </ul>
            </div>
            <div style="background:linear-gradient(180deg, #FFFFFF 0%, #F7FAF2 100%); border:1px solid #B6C4E5; border-radius:8px; padding:0.95rem 1rem; box-shadow:0 10px 20px rgba(2, 15, 80, 0.05);">
                <h4>Vista previa</h4>
                <p>Sirve para revisar r&aacute;pidamente las primeras filas del dataset antes de seguir con el an&aacute;lisis.</p>
                <ul>
                    <li>Inspecciona las primeras filas de la base cargada.</li>
                    <li>Revisa valores perdidos por variable.</li>
                    <li>Confirma nombres de columnas y estructura general del archivo.</li>
                </ul>
            </div>
            <div style="background:linear-gradient(180deg, #FFFFFF 0%, #F7FAF2 100%); border:1px solid #B6C4E5; border-radius:8px; padding:0.95rem 1rem; box-shadow:0 10px 20px rgba(2, 15, 80, 0.05);">
                <h4>Gr&aacute;ficos</h4>
                <p>Construye visualizaciones personalizadas para an&aacute;lisis e informes.</p>
                <ul>
                    <li>Genera barras, histogramas o gr&aacute;ficos de dispersi&oacute;n.</li>
                    <li>Personaliza t&iacute;tulos, ejes, colores, leyenda y rangos.</li>
                    <li>Exporta el gr&aacute;fico como PNG cuando est&eacute; disponible.</li>
                </ul>
            </div>
            <div style="background:linear-gradient(180deg, #FFFFFF 0%, #F7FAF2 100%); border:1px solid #B6C4E5; border-radius:8px; padding:0.95rem 1rem; box-shadow:0 10px 20px rgba(2, 15, 80, 0.05);">
                <h4>Tablas cruzadas</h4>
                <p>Produce tablas masivas entre variables principales y desagregaciones sociodemogr&aacute;ficas.</p>
                <ul>
                    <li>Selecciona varias variables principales.</li>
                    <li>Selecciona varias variables de desagregaci&oacute;n.</li>
                    <li>Descarga un Excel con una hoja por variable principal.</li>
                </ul>
            </div>
            <div style="background:linear-gradient(180deg, #FFFFFF 0%, #F7FAF2 100%); border:1px solid #B6C4E5; border-radius:8px; padding:0.95rem 1rem; box-shadow:0 10px 20px rgba(2, 15, 80, 0.05);">
                <h4>Continuas</h4>
                <p>Resume variables num&eacute;ricas con estad&iacute;sticos descriptivos listos para reporte.</p>
                <ul>
                    <li>Media, mediana, desviaci&oacute;n est&aacute;ndar y percentiles.</li>
                    <li>Conteo de v&aacute;lidos y perdidos.</li>
                    <li>Descarga la tabla en CSV o XLSX.</li>
                </ul>
            </div>
            <div style="background:linear-gradient(180deg, #FFFFFF 0%, #F7FAF2 100%); border:1px solid #B6C4E5; border-radius:8px; padding:0.95rem 1rem; box-shadow:0 10px 20px rgba(2, 15, 80, 0.05);">
                <h4>Categ&oacute;ricas</h4>
                <p>Revisa frecuencias, porcentajes y valores perdidos por categor&iacute;a.</p>
                <ul>
                    <li>Filtra qu&eacute; variables mostrar.</li>
                    <li>Controla el m&aacute;ximo de categor&iacute;as visibles.</li>
                    <li>Descarga la tabla en CSV o XLSX.</li>
                </ul>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
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

    render_app_header("Exploración descriptiva modular")

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

    tab_instructions, tab_preview, tab_graphs, tab_cross, tab_cont, tab_cat = st.tabs(
        ["Instrucciones", "Vista previa", "Gráficos", "Tablas cruzadas", "Continuas", "Categóricas"]
    )

    with tab_instructions:
        instructions_tab()
    with tab_preview:
        preview_tab(df)
    with tab_graphs:
        charts_tab(df, selected_continuous, selected_categorical)
    with tab_cross:
        cross = mass_crosstab_tab(df, selected_categorical)
        if not cross.empty:
            tables["tabla_cruzada"] = cross
    with tab_cont:
        tables["continuas"] = continuous_tab(df, selected_continuous)
    with tab_cat:
        tables["categoricas"] = categorical_tab(df, selected_categorical)


if __name__ == "__main__":
    main()
